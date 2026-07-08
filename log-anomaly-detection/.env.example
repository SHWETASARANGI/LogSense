"""
simulate_logs.py

Generates realistic, structured application/infrastructure logs for LogSense,
conforming to the raw log schema defined in docs/ml_design.md.

Simulates multiple services with "normal" baseline behavior, then injects
labeled anomaly windows (error spikes, latency degradation, traffic surges,
traffic drops / outages) so that downstream anomaly detection models can be
evaluated against known ground truth.

Outputs:
    data/raw/logs_<run_id>.jsonl              - raw log lines (JSON Lines)
    data/samples/injected_anomalies_<run_id>.json - ground-truth anomaly windows

Usage:
    python scripts/simulate_logs.py --duration-minutes 180 --num-anomalies 6
    python scripts/simulate_logs.py --duration-minutes 60 --seed 42 --output-dir data
"""

import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Service configuration: defines "normal" baseline behavior per service.
# These numbers are illustrative, not derived from any real system.
# ---------------------------------------------------------------------------
SERVICES = {
    "auth-service": {
        "hosts": ["host-01", "host-02"],
        "base_logs_per_sec": 4.0,
        "error_rate": 0.01,
        "warn_rate": 0.04,
        "latency_mean_ms": 80,
        "latency_std_ms": 25,
        "has_http": True,
    },
    "payment-service": {
        "hosts": ["host-03", "host-04", "host-05"],
        "base_logs_per_sec": 6.0,
        "error_rate": 0.02,
        "warn_rate": 0.05,
        "latency_mean_ms": 220,
        "latency_std_ms": 60,
        "has_http": True,
    },
    "api-gateway": {
        "hosts": ["host-06", "host-07"],
        "base_logs_per_sec": 10.0,
        "error_rate": 0.015,
        "warn_rate": 0.03,
        "latency_mean_ms": 50,
        "latency_std_ms": 15,
        "has_http": True,
    },
    "notification-service": {
        "hosts": ["host-08"],
        "base_logs_per_sec": 2.0,
        "error_rate": 0.03,
        "warn_rate": 0.06,
        "latency_mean_ms": 150,
        "latency_std_ms": 40,
        "has_http": False,
    },
}

ERROR_TYPES = [
    "TimeoutError",
    "DBConnectionError",
    "NullReferenceException",
    "RateLimitExceeded",
    "UpstreamServiceError",
    "ValidationError",
]

INFO_MESSAGES = [
    "Request processed successfully",
    "Cache hit for key",
    "Scheduled job completed",
    "Health check OK",
    "User session refreshed",
]

WARN_MESSAGES = [
    "Retrying request after transient failure",
    "Connection pool nearing capacity",
    "Slow query detected",
    "Deprecated API endpoint called",
]

ANOMALY_TYPES = ["ERROR_SPIKE", "LATENCY_SPIKE", "TRAFFIC_SURGE", "TRAFFIC_DROP"]


def sample_status_code(is_error: bool, is_warn: bool) -> int:
    """Sample an HTTP-like status code consistent with the log's severity."""
    if is_error:
        return random.choice([500, 502, 503, 504])
    if is_warn:
        return random.choice([408, 429])
    return random.choices([200, 201, 204, 404], weights=[80, 10, 5, 5])[0]


def sample_latency(mean_ms: float, std_ms: float, multiplier: float = 1.0) -> float:
    """Sample a latency value, clipped to be non-negative."""
    value = random.gauss(mean_ms * multiplier, std_ms * multiplier)
    return round(max(value, 1.0), 2)


def make_log_entry(service_name: str, cfg: dict, timestamp: datetime,
                    error_rate_override: float = None,
                    latency_multiplier: float = 1.0) -> dict:
    """Construct a single structured log entry for a given service."""
    error_rate = cfg["error_rate"] if error_rate_override is None else error_rate_override
    roll = random.random()

    if roll < error_rate:
        level = "ERROR"
    elif roll < error_rate + cfg["warn_rate"]:
        level = "WARN"
    else:
        level = "INFO" if random.random() > 0.3 else "DEBUG"

    is_error = level == "ERROR"
    is_warn = level == "WARN"

    entry = {
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "service_name": service_name,
        "host_id": random.choice(cfg["hosts"]),
        "log_level": level,
        "status_code": sample_status_code(is_error, is_warn) if cfg["has_http"] else None,
        "latency_ms": sample_latency(cfg["latency_mean_ms"], cfg["latency_std_ms"],
                                      latency_multiplier) if cfg["has_http"] else None,
        "message": (
            random.choice(WARN_MESSAGES) if is_warn else
            random.choice(INFO_MESSAGES) if not is_error else
            "Unhandled exception during request processing"
        ),
        "error_type": random.choice(ERROR_TYPES) if is_error else None,
        "trace_id": uuid.uuid4().hex[:16],
    }
    return entry


def schedule_anomalies(start_time: datetime, duration_minutes: int,
                        num_anomalies: int, min_len_min: int = 2,
                        max_len_min: int = 6) -> list:
    """
    Randomly schedule non-overlapping anomaly windows across the simulation
    period. Each window is assigned a type and a target service.
    """
    anomalies = []
    attempts = 0
    max_attempts = num_anomalies * 20

    while len(anomalies) < num_anomalies and attempts < max_attempts:
        attempts += 1
        offset_min = random.randint(5, max(6, duration_minutes - max_len_min - 5))
        length_min = random.randint(min_len_min, max_len_min)
        window_start = start_time + timedelta(minutes=offset_min)
        window_end = window_start + timedelta(minutes=length_min)

        # avoid overlapping anomaly windows for clean ground truth
        overlaps = any(
            window_start < a["window_end"] and window_end > a["window_start"]
            for a in anomalies
        )
        if overlaps:
            continue

        anomalies.append({
            "anomaly_type": random.choice(ANOMALY_TYPES),
            "service_name": random.choice(list(SERVICES.keys())),
            "window_start": window_start,
            "window_end": window_end,
        })

    anomalies.sort(key=lambda a: a["window_start"])
    return anomalies


def active_anomaly_for(service_name: str, timestamp: datetime, anomalies: list):
    """Return the anomaly dict active for this service/timestamp, if any."""
    for a in anomalies:
        if a["service_name"] == service_name and a["window_start"] <= timestamp < a["window_end"]:
            return a
    return None


def apply_anomaly_effects(cfg: dict, anomaly: dict):
    """
    Given the base service config and an active anomaly, return
    (error_rate_override, latency_multiplier, rate_multiplier) to apply
    for this tick's log generation.
    """
    error_rate_override = None
    latency_multiplier = 1.0
    rate_multiplier = 1.0

    if anomaly is None:
        return error_rate_override, latency_multiplier, rate_multiplier

    if anomaly["anomaly_type"] == "ERROR_SPIKE":
        error_rate_override = min(cfg["error_rate"] * 12, 0.6)
    elif anomaly["anomaly_type"] == "LATENCY_SPIKE":
        latency_multiplier = random.uniform(4.0, 8.0)
    elif anomaly["anomaly_type"] == "TRAFFIC_SURGE":
        rate_multiplier = random.uniform(4.0, 6.0)
    elif anomaly["anomaly_type"] == "TRAFFIC_DROP":
        rate_multiplier = random.uniform(0.0, 0.1)

    return error_rate_override, latency_multiplier, rate_multiplier


def generate_logs(start_time: datetime, duration_minutes: int, anomalies: list) -> list:
    """
    Simulate one log tick per second for each service, sampling a Poisson
    number of log lines per tick based on the (possibly anomaly-adjusted)
    rate, and return the full flat list of generated log entries.
    """
    logs = []
    total_seconds = duration_minutes * 60

    for sec in range(total_seconds):
        timestamp = start_time + timedelta(seconds=sec)

        for service_name, cfg in SERVICES.items():
            anomaly = active_anomaly_for(service_name, timestamp, anomalies)
            error_rate_override, latency_multiplier, rate_multiplier = apply_anomaly_effects(cfg, anomaly)

            effective_rate = cfg["base_logs_per_sec"] * rate_multiplier
            num_logs_this_tick = poisson_sample(effective_rate)

            for _ in range(num_logs_this_tick):
                logs.append(make_log_entry(
                    service_name, cfg, timestamp,
                    error_rate_override=error_rate_override,
                    latency_multiplier=latency_multiplier,
                ))

    logs.sort(key=lambda x: x["timestamp"])
    return logs


def poisson_sample(lam: float) -> int:
    """Simple Poisson sampler using only the standard library (Knuth's algorithm)."""
    if lam <= 0:
        return 0
    l = pow(2.718281828, -lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p <= l:
            return k - 1


def write_jsonl(logs: list, path: str):
    with open(path, "w") as f:
        for entry in logs:
            f.write(json.dumps(entry) + "\n")


def write_anomalies(anomalies: list, path: str):
    serializable = [
        {
            "anomaly_type": a["anomaly_type"],
            "service_name": a["service_name"],
            "window_start": a["window_start"].isoformat().replace("+00:00", "Z"),
            "window_end": a["window_end"].isoformat().replace("+00:00", "Z"),
        }
        for a in anomalies
    ]
    with open(path, "w") as f:
        json.dump(serializable, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Simulate LogSense application logs.")
    parser.add_argument("--duration-minutes", type=int, default=60,
                         help="How many minutes of logs to simulate.")
    parser.add_argument("--num-anomalies", type=int, default=4,
                         help="Number of labeled anomaly windows to inject.")
    parser.add_argument("--output-dir", type=str, default="data",
                         help="Root data directory (expects raw/ and samples/ subfolders).")
    parser.add_argument("--seed", type=int, default=None,
                         help="Random seed for reproducibility.")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    start_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=args.duration_minutes)

    print(f"[simulate_logs] Scheduling {args.num_anomalies} anomaly windows...")
    anomalies = schedule_anomalies(start_time, args.duration_minutes, args.num_anomalies)
    for a in anomalies:
        print(f"  - {a['anomaly_type']:<15} on {a['service_name']:<20} "
              f"{a['window_start'].strftime('%H:%M:%S')} -> {a['window_end'].strftime('%H:%M:%S')}")

    print(f"[simulate_logs] Generating {args.duration_minutes} minutes of logs "
          f"across {len(SERVICES)} services...")
    logs = generate_logs(start_time, args.duration_minutes, anomalies)
    print(f"[simulate_logs] Generated {len(logs)} log entries.")

    raw_dir = os.path.join(args.output_dir, "raw")
    samples_dir = os.path.join(args.output_dir, "samples")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(samples_dir, exist_ok=True)

    logs_path = os.path.join(raw_dir, f"logs_{run_id}.jsonl")
    anomalies_path = os.path.join(samples_dir, f"injected_anomalies_{run_id}.json")

    write_jsonl(logs, logs_path)
    write_anomalies(anomalies, anomalies_path)

    print(f"[simulate_logs] Wrote raw logs to:        {logs_path}")
    print(f"[simulate_logs] Wrote ground-truth labels to: {anomalies_path}")


if __name__ == "__main__":
    main()