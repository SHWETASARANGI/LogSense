"""
config.py

Centralized configuration for LogSense. Values are read from environment
variables (see .env.example at the repo root) with sensible local defaults,
so the app runs out-of-the-box in development without any setup.
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    # --- Database ---
    # SQLite by default for local development; swap for a Postgres URL
    # (e.g. postgresql://user:pass@localhost:5432/logsense) in production
    # without touching any application code.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./logsense.db")

    # --- Model ---
    # Directory containing the currently active model.pkl + metadata.json.
    # services/model_registry.py reads from here.
    model_dir: str = os.getenv("MODEL_DIR", "../models/isolation_forest")

    # --- Feature engineering ---
    feature_window_seconds: int = int(os.getenv("FEATURE_WINDOW_SECONDS", "60"))

    # --- Anomaly detection thresholds ---
    # Windows scoring >= this are persisted to the anomalies table at all.
    # Keeps the DB from filling up with every near-zero "normal" window.
    anomaly_store_threshold: float = float(os.getenv("ANOMALY_STORE_THRESHOLD", "0.5"))

    # Windows scoring >= this trigger an alert (services/alert_service.py).
    anomaly_alert_threshold: float = float(os.getenv("ANOMALY_ALERT_THRESHOLD", "0.75"))


settings = Settings()