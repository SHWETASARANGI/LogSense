"""
models.py

SQLAlchemy ORM models for LogSense's three persisted entities:
    - LogRecord       - structured log lines (mirrors docs/ml_design.md section 2)
    - AnomalyRecord    - detected anomalies (mirrors docs/ml_design.md section 3 + score)
    - ModelMetadataRecord - training run history, for the Model Monitoring page

Note: raw logs also live on disk (data/raw/*.jsonl) and the feature table
lives in data/processed/features.parquet - those remain the source of truth
for training. LogRecord in the DB exists to serve the Log Explorer page
(filter by service/time/level) without re-parsing files on every request.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, UniqueConstraint
from sqlalchemy.sql import func

from app.db.database import Base


class LogRecord(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    service_name = Column(String, nullable=False, index=True)
    host_id = Column(String, nullable=False)
    log_level = Column(String, nullable=False, index=True)
    status_code = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    message = Column(String, nullable=False)
    error_type = Column(String, nullable=True)
    trace_id = Column(String, nullable=False)


class AnomalyRecord(Base):
    __tablename__ = "anomalies"
    __table_args__ = (
        # One anomaly record per (service, window) - re-running detection on
        # the same window updates the existing row instead of duplicating it.
        UniqueConstraint("service_name", "window_start", name="uq_service_window"),
    )

    id = Column(Integer, primary_key=True, index=True)
    window_start = Column(DateTime(timezone=True), nullable=False, index=True)
    window_end = Column(DateTime(timezone=True), nullable=False)
    service_name = Column(String, nullable=False, index=True)

    anomaly_score = Column(Float, nullable=False)
    severity = Column(String, nullable=False, index=True)  # low | medium | high | critical

    # Snapshot of the feature values that produced this score, so the
    # Anomaly Explorer / AnomalyDetail page can show "why" without
    # re-querying the feature table.
    log_count = Column(Integer, nullable=False)
    error_rate = Column(Float, nullable=False)
    avg_latency_ms = Column(Float, nullable=False)
    p95_latency_ms = Column(Float, nullable=False)
    log_volume_delta = Column(Float, nullable=False)

    model_version = Column(String, nullable=False)

    # Alert/triage lifecycle - new -> acknowledged -> resolved.
    status = Column(String, nullable=False, default="new", index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ModelMetadataRecord(Base):
    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, nullable=False, unique=True, index=True)
    model_type = Column(String, nullable=False)
    contamination = Column(Float, nullable=False)
    n_estimators = Column(Integer, nullable=True)
    trained_at = Column(DateTime(timezone=True), nullable=False)
    training_data_path = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())