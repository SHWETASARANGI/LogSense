"""
feature_engineering.py

Transforms raw, per-line log data into the fixed-window, per-service feature
table defined in docs/ml_design.md (section 3). This is the single source of
truth for turning logs into the numeric feature vectors that ML models
(ml/isolation_forest.py, ml/autoencoder.py) consume.

Design decisions implemented here (see docs/ml_design.md for full rationale):
    - One row = one (service_name, window_start) pair.
    - Empty windows are zero-filled, not dropped, so rate features and
      log_volume_delta stay well-defined across time gaps.
    - Rate-based features default to 0.0 when log_count == 0 (avoid div/0).
    - log_volume_delta is % change in log_count vs. the previous window for
      the same service; the first window per service gets 0.0 (no prior data).

Usage (standalone):
    python -m app.services.feature_engineering \
        --input data/raw/logs_20260708_173332.jsonl \
        --output data/processed/features.parquet \
        --window-seconds 60
"""

import argparse
import glob
import json
import os
import sys

import pandas as pd

# Allow running this file standalone (python services/feature_engineering.py)
# as well as as a package module (python -m app.services.feature_engineering).
try:
    from app.utils.time_windows import floor_to_window, full_window_range, window_end
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from app.utils.time_windows import floor_to_window, full_window_range, window_end


# Output column order matches the schema in docs/ml_design.md section 3.
FEATURE_COLUMNS = [
    "window_start",
    "window_end",
    "service_name",
    "log_count",
    "error_count",
    "warn_count",
    "error_rate",
    "warn_rate",
    "avg_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "status_5xx_rate",
    "status_4xx_rate",
    "unique_error_types",
    "unique_hosts",
    "log_volume_delta",
]


def load_raw_logs(input_path: str) -> pd.DataFrame:
    """
    Load one or more raw JSONL log files into a DataFrame.

    `input_path` may be a single file or a glob pattern (e.g. 'data/raw/*.jsonl')
    so multiple simulate_logs.py runs can be combined into one training set.
    """
    paths = sorted(glob.glob(input_path)) if any(ch in input_path for ch in "*?[") else [input_path]
    if not paths:
        raise FileNotFoundError(f"No files matched: {input_path}")

    records = []
    for path in paths:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

    if not records:
        raise ValueError(f"No log records found in: {input_path}")

    df = pd.DataFrame.from_records(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def _aggregate_raw_windows(df: pd.DataFrame, window_seconds: int) -> pd.DataFrame:
    """
    Group raw logs by (service_name, window_start) and compute per-window
    aggregates. Windows with zero logs are NOT present yet at this stage —
    that gap-filling happens in _reindex_full_grid.
    """
    df = df.copy()
    df["window_start"] = floor_to_window(df["timestamp"], window_seconds)
    df["is_error"] = df["log_level"] == "ERROR"
    df["is_warn"] = df["log_level"] == "WARN"
    df["is_5xx"] = df["status_code"].between(500, 599, inclusive="both")
    df["is_4xx"] = df["status_code"].between(400, 499, inclusive="both")

    grouped = df.groupby(["service_name", "window_start"])

    agg = grouped.agg(
        log_count=("timestamp", "count"),
        error_count=("is_error", "sum"),
        warn_count=("is_warn", "sum"),
        avg_latency_ms=("latency_ms", "mean"),
        p95_latency_ms=("latency_ms", lambda s: s.quantile(0.95)),
        p99_latency_ms=("latency_ms", lambda s: s.quantile(0.99)),
        status_5xx_count=("is_5xx", "sum"),
        status_4xx_count=("is_4xx", "sum"),
        unique_error_types=("error_type", lambda s: s.dropna().nunique()),
        unique_hosts=("host_id", "nunique"),
    ).reset_index()

    return agg


def _reindex_full_grid(agg: pd.DataFrame, df: pd.DataFrame, window_seconds: int) -> pd.DataFrame:
    """
    Ensure every (service_name, window_start) combination across the full
    observed time range is present, zero-filling windows with no logs.
    This is the implementation of the "empty window" decision in
    docs/ml_design.md section 4.3.
    """
    all_services = sorted(df["service_name"].unique())
    full_windows = full_window_range(df["timestamp"].min(), df["timestamp"].max(), window_seconds)

    full_index = pd.MultiIndex.from_product(
        [all_services, full_windows], names=["service_name", "window_start"]
    )
    full_grid = pd.DataFrame(index=full_index).reset_index()

    merged = full_grid.merge(agg, on=["service_name", "window_start"], how="left")

    zero_fill_cols = [
        "log_count", "error_count", "warn_count",
        "status_5xx_count", "status_4xx_count",
        "unique_error_types", "unique_hosts",
    ]
    merged[zero_fill_cols] = merged[zero_fill_cols].fillna(0)
    # Latency features have no meaningful value in a window with zero traffic;
    # 0.0 is used (rather than NaN) so the feature matrix stays fully numeric
    # for models like Isolation Forest that don't natively handle NaN.
    merged[["avg_latency_ms", "p95_latency_ms", "p99_latency_ms"]] = merged[
        ["avg_latency_ms", "p95_latency_ms", "p99_latency_ms"]
    ].fillna(0.0)

    return merged


def _compute_derived_features(merged: pd.DataFrame, window_seconds: int) -> pd.DataFrame:
    """Compute rate-based features and the cross-window log_volume_delta."""
    merged = merged.sort_values(["service_name", "window_start"]).reset_index(drop=True)

    # Rate features: 0.0 when log_count == 0 to avoid division by zero.
    safe_log_count = merged["log_count"].replace(0, pd.NA)
    merged["error_rate"] = (merged["error_count"] / safe_log_count).fillna(0.0)
    merged["warn_rate"] = (merged["warn_count"] / safe_log_count).fillna(0.0)
    merged["status_5xx_rate"] = (merged["status_5xx_count"] / safe_log_count).fillna(0.0)
    merged["status_4xx_rate"] = (merged["status_4xx_count"] / safe_log_count).fillna(0.0)

    # log_volume_delta: % change in log_count vs. the previous window for the
    # SAME service. First window per service has no prior point -> 0.0.
    merged["prev_log_count"] = merged.groupby("service_name")["log_count"].shift(1)
    prev_safe = merged["prev_log_count"].replace(0, pd.NA)
    merged["log_volume_delta"] = (
        (merged["log_count"] - merged["prev_log_count"]) / prev_safe * 100
    ).fillna(0.0)

    merged["window_end"] = window_end(merged["window_start"], window_seconds)

    return merged


def compute_features(df: pd.DataFrame, window_seconds: int = 60) -> pd.DataFrame:
    """
    Full pipeline: raw log DataFrame -> windowed feature DataFrame.
    This is the main entry point used both by this script's CLI and by
    services/anomaly_detection.py at inference time.
    """
    agg = _aggregate_raw_windows(df, window_seconds)
    merged = _reindex_full_grid(agg, df, window_seconds)
    features = _compute_derived_features(merged, window_seconds)

    features = features[FEATURE_COLUMNS].sort_values(["service_name", "window_start"]).reset_index(drop=True)
    return features


def save_features(features: pd.DataFrame, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    features.to_parquet(output_path, index=False)


def main():
    parser = argparse.ArgumentParser(description="Aggregate raw logs into windowed features.")
    parser.add_argument("--input", type=str, required=True,
                         help="Path to a raw log .jsonl file, or a glob pattern (e.g. 'data/raw/*.jsonl').")
    parser.add_argument("--output", type=str, default="data/processed/features.parquet",
                         help="Output path for the feature table (parquet).")
    parser.add_argument("--window-seconds", type=int, default=60,
                         help="Fixed window size in seconds.")
    args = parser.parse_args()

    print(f"[feature_engineering] Loading raw logs from: {args.input}")
    df = load_raw_logs(args.input)
    print(f"[feature_engineering] Loaded {len(df)} raw log lines "
          f"across {df['service_name'].nunique()} services.")

    print(f"[feature_engineering] Aggregating into {args.window_seconds}s windows...")
    features = compute_features(df, window_seconds=args.window_seconds)
    print(f"[feature_engineering] Produced {len(features)} feature rows.")

    save_features(features, args.output)
    print(f"[feature_engineering] Wrote feature table to: {args.output}")


if __name__ == "__main__":
    main()