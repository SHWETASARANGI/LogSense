"""
dashboard.py

    GET /dashboard - aggregate summary for the frontend Dashboard page:
    total anomalies, active anomalies, error rate, log volume, severity
    breakdown, and current model info, all over a configurable lookback window.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api import deps
from app.db import models as db_models
from app.schemas.dashboard import DashboardSummary
from app.services import model_registry

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_model=DashboardSummary)
def get_dashboard_summary(
    lookback_hours: int = Query(24, gt=0, description="How far back to aggregate."),
    db: Session = Depends(deps.get_db),
):
    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    base_query = db.query(db_models.AnomalyRecord).filter(
        db_models.AnomalyRecord.window_start >= since
    )

    total_anomalies = base_query.count()
    active_anomalies = base_query.filter(db_models.AnomalyRecord.status == "new").count()

    avg_score = base_query.with_entities(
        func.avg(db_models.AnomalyRecord.anomaly_score)
    ).scalar() or 0.0

    avg_error_rate = base_query.with_entities(
        func.avg(db_models.AnomalyRecord.error_rate)
    ).scalar() or 0.0

    total_log_volume = base_query.with_entities(
        func.sum(db_models.AnomalyRecord.log_count)
    ).scalar() or 0

    severity_breakdown = dict(
        db.query(db_models.AnomalyRecord.severity, func.count())
        .filter(db_models.AnomalyRecord.window_start >= since)
        .group_by(db_models.AnomalyRecord.severity)
        .all()
    )

    active_model = model_registry.get_active_model_record(db)

    return DashboardSummary(
        lookback_hours=lookback_hours,
        total_anomalies=total_anomalies,
        active_anomalies=active_anomalies,
        avg_anomaly_score=round(avg_score, 3),
        avg_error_rate=round(avg_error_rate, 3),
        total_log_volume=int(total_log_volume),
        severity_breakdown=severity_breakdown,
        model_version=active_model.version if active_model else None,
        model_trained_at=active_model.trained_at if active_model else None,
    )