"""
anomalies.py

Endpoints for browsing and triaging detected anomalies. Powers the frontend
AnomalyList / AnomalyDetail components.

    GET   /anomalies          - filterable, paginated list
    GET   /anomalies/{id}     - single anomaly detail
    PATCH /anomalies/{id}     - update triage status (new -> acknowledged -> resolved)
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.db import models as db_models
from app.schemas.anomaly import AnomalyOut, AnomalyStatusUpdate

router = APIRouter(prefix="/anomalies", tags=["anomalies"])

VALID_STATUSES = {"new", "acknowledged", "resolved"}


@router.get("/", response_model=List[AnomalyOut])
def list_anomalies(
    service_name: Optional[str] = None,
    severity: Optional[str] = Query(None, description="low | medium | high | critical"),
    status: Optional[str] = Query(None, description="new | acknowledged | resolved"),
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(deps.get_db),
):
    """List anomalies, most recent first, with optional filters."""
    query = db.query(db_models.AnomalyRecord)

    if service_name:
        query = query.filter(db_models.AnomalyRecord.service_name == service_name)
    if severity:
        query = query.filter(db_models.AnomalyRecord.severity == severity)
    if status:
        query = query.filter(db_models.AnomalyRecord.status == status)

    query = query.order_by(db_models.AnomalyRecord.window_start.desc())
    return query.offset(offset).limit(limit).all()


@router.get("/{anomaly_id}", response_model=AnomalyOut)
def get_anomaly(anomaly_id: int, db: Session = Depends(deps.get_db)):
    """Fetch a single anomaly by id, for the AnomalyDetail page."""
    anomaly = db.get(db_models.AnomalyRecord, anomaly_id)
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    return anomaly


@router.patch("/{anomaly_id}", response_model=AnomalyOut)
def update_anomaly_status(
    anomaly_id: int,
    payload: AnomalyStatusUpdate,
    db: Session = Depends(deps.get_db),
):
    """Update the triage status of an anomaly (acknowledge / resolve)."""
    if payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {sorted(VALID_STATUSES)}",
        )

    anomaly = db.get(db_models.AnomalyRecord, anomaly_id)
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    anomaly.status = payload.status
    db.commit()
    db.refresh(anomaly)
    return anomaly