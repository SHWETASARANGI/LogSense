"""
anomaly_detection.py

The core detection pipeline: raw logs -> features -> model score -> persisted
anomaly records. This is the function core/scheduler.py calls on a timer to
simulate a production monitoring loop, and it's also callable directly (e.g.
from a route or a one-off script) for on-demand detection runs.

Pipeline:
    1. Load raw logs (from a file, or accept an already-loaded DataFrame)
    2. Compute windowed features (services/feature_engineering.py)
    3. Score each window with the active model (services/model_registry.py)
    4. Persist windows scoring >= ANOMALY_STORE_THRESHOLD to the anomalies
       table, upserting on (service_name, window_start) so re-running
       detection over overlapping data doesn't create duplicates.
"""

import os
import sys
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

try:
    from app.core.config import settings
    from app.db import models as db_models
    from app.services import feature_engineering
    from app.services import model_registry
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from app.core.config import settings
    from app.db import models as db_models
    from app.services import feature_engineering
    from app.services import model_registry


# Severity bands over the normalized [0, 1] anomaly_score. Tunable, and
# intentionally centralized here so the API and dashboard always agree on
# what "high" vs "critical" means.
SEVERITY_BANDS = [
    (0.9, "critical"),
    (0.75, "high"),
    (0.6, "medium"),
    (0.0, "low"),
]


def severity_for_score(score: float) -> str:
    """Map a normalized anomaly_score to a severity label."""
    for lower_bound, label in SEVERITY_BANDS:
        if score >= lower_bound:
            return label
    return "low"


def run_detection(
    db: Session,
    raw_logs_path: str = None,
    logs_df: pd.DataFrame = None,
    window_seconds: int = None,
    store_threshold: float = None,
) -> dict:
    """
    Run the full detection pipeline and persist resulting anomalies.

    Either `raw_logs_path` (a .jsonl file or glob) or an already-loaded
    `logs_df` must be provided. Returns a summary dict for logging/API
    responses.
    """
    if logs_df is None:
        if raw_logs_path is None:
            raise ValueError("Must provide either raw_logs_path or logs_df.")
        logs_df = feature_engineering.load_raw_logs(raw_logs_path)

    window_seconds = window_seconds or settings.feature_window_seconds
    store_threshold = store_threshold if store_threshold is not None else settings.anomaly_store_threshold

    features = feature_engineering.compute_features(logs_df, window_seconds=window_seconds)

    model = model_registry.get_active_model()
    active_metadata = model_registry.get_active_metadata()
    model_version = active_metadata["version"]

    features["anomaly_score"] = model.score(features)

    anomalous = features[features["anomaly_score"] >= store_threshold].copy()

    upserted = 0
    for _, row in anomalous.iterrows():
        severity = severity_for_score(row["anomaly_score"])

        existing = db.query(db_models.AnomalyRecord).filter_by(
            service_name=row["service_name"],
            window_start=row["window_start"].to_pydatetime(),
        ).first()

        if existing:
            existing.anomaly_score = float(row["anomaly_score"])
            existing.severity = severity
            existing.log_count = int(row["log_count"])
            existing.error_rate = float(row["error_rate"])
            existing.avg_latency_ms = float(row["avg_latency_ms"])
            existing.p95_latency_ms = float(row["p95_latency_ms"])
            existing.log_volume_delta = float(row["log_volume_delta"])
            existing.model_version = model_version
        else:
            record = db_models.AnomalyRecord(
                window_start=row["window_start"].to_pydatetime(),
                window_end=row["window_end"].to_pydatetime(),
                service_name=row["service_name"],
                anomaly_score=float(row["anomaly_score"]),
                severity=severity,
                log_count=int(row["log_count"]),
                error_rate=float(row["error_rate"]),
                avg_latency_ms=float(row["avg_latency_ms"]),
                p95_latency_ms=float(row["p95_latency_ms"]),
                log_volume_delta=float(row["log_volume_delta"]),
                model_version=model_version,
                status="new",
            )
            db.add(record)

        upserted += 1

    db.commit()

    summary = {
        "windows_evaluated": len(features),
        "anomalies_detected": len(anomalous),
        "anomalies_upserted": upserted,
        "model_version": model_version,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }
    return summary