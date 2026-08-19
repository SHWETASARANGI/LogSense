"""
logs.py

    GET /logs - filterable, paginated raw log browsing, for the frontend
    Log Explorer page. Reads from the `logs` table (db/models.py:LogRecord),
    which is populated by services/ingestion_service.py.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.db import models as db_models
from app.schemas.log import LogOut

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/", response_model=List[LogOut])
def list_logs(
    service_name: Optional[str] = None,
    log_level: Optional[str] = Query(None, description="DEBUG | INFO | WARN | ERROR"),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(deps.get_db),
):
    query = db.query(db_models.LogRecord)

    if service_name:
        query = query.filter(db_models.LogRecord.service_name == service_name)
    if log_level:
        query = query.filter(db_models.LogRecord.log_level == log_level)
    if start:
        query = query.filter(db_models.LogRecord.timestamp >= start)
    if end:
        query = query.filter(db_models.LogRecord.timestamp <= end)

    query = query.order_by(db_models.LogRecord.timestamp.desc())
    return query.offset(offset).limit(limit).all()