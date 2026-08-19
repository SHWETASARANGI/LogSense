"""
model.py

Pydantic schemas for GET /model/status and POST /model/retrain - powers the
frontend's Model Monitoring page and the manual/triggered retraining flow.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelStatus(BaseModel):
    version: str
    model_type: str
    contamination: float
    n_estimators: Optional[int] = None
    trained_at: datetime
    training_data_path: Optional[str] = None
    is_active: bool
    anomalies_detected: int  # count of anomalies attributed to this model version


class RetrainRequest(BaseModel):
    features_path: Optional[str] = Field(
        default=None,
        description="Path to a feature parquet file. Defaults to data/processed/features.parquet.",
    )
    contamination: float = Field(default=0.05, gt=0.0, lt=0.5)
    n_estimators: int = Field(default=200, gt=0)


class RetrainResponse(BaseModel):
    version: str
    trained_at: datetime
    rows_used: int
    contamination: float
    n_estimators: int