"""
isolation_forest.py

A thin, self-contained wrapper around sklearn's IsolationForest that:
    - builds a consistent design matrix from the feature table produced by
      services/feature_engineering.py (numeric features + one-hot encoded
      service_name, per docs/ml_design.md section 4.2 and section 5),
    - converts sklearn's raw anomaly score into a normalized [0, 1]
      "anomaly_score" (higher = more anomalous), which is what the API/
      dashboard will actually display,
    - handles save/load with metadata, so training-time feature order and
      service categories are guaranteed to match serving-time (avoids
      train/serve skew).

This class is used by both ml/train.py (training) and
services/anomaly_detection.py (inference) - never duplicate this logic
elsewhere.
"""

import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# Numeric feature columns consumed by the model, per docs/ml_design.md section 5.
# Deliberately excludes identifier/time columns (window_start, window_end,
# service_name) which are retained alongside predictions but not fed raw
# into the model.

NUMERIC_FEATURE_COLUMNS = [
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

MODEL_FILENAME = "model.pkl"
METADATA_FILENAME = "metadata.json"


class IsolationForestModel:
    """
    Wrapper around sklearn.ensemble.IsolationForest with a fixed feature
    contract, service_name encoding, and normalized scoring.
    """

    def __init__(self, n_estimators: int = 200, contamination: float = 0.05,
                 random_state: int = 42, service_categories: list = None):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state

        # Fixed at fit time; ensures serving-time one-hot columns match
        # training-time columns even if a service is missing at inference.
        self.service_categories = service_categories or []

        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
        )

        # Populated after fit(); used to min-max normalize raw scores into [0, 1].
        self._raw_score_min = None
        self._raw_score_max = None
        self._is_fitted = False

    # ------------------------------------------------------------------
    # Design matrix construction
    # ------------------------------------------------------------------
    def _build_design_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Construct the numeric design matrix: numeric feature columns +
        one-hot encoded service_name, using the FIXED service_categories
        recorded at fit time (so column set/order never drifts at inference).
        """
        missing = [c for c in NUMERIC_FEATURE_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Input dataframe is missing required feature columns: {missing}")

        numeric = df[NUMERIC_FEATURE_COLUMNS].copy()

        for category in self.service_categories:
            numeric[f"service_{category}"] = (df["service_name"] == category).astype(int)

        return numeric

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def fit(self, df: pd.DataFrame):
        """
        Fit the model on a feature table (as produced by
        services/feature_engineering.py). Records the service categories
        seen at training time and the raw score range used for normalization.
        """
        self.service_categories = sorted(df["service_name"].unique().tolist())
        X = self._build_design_matrix(df)

        self.model.fit(X)

        # decision_function: higher = more normal, lower = more anomalous.
        # We flip sign so higher = more anomalous, then record min/max on the
        # training set to normalize into a stable [0, 1] "anomaly_score".
        raw_scores = -self.model.decision_function(X)
        self._raw_score_min = float(raw_scores.min())
        self._raw_score_max = float(raw_scores.max())
        self._is_fitted = True
        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def score(self, df: pd.DataFrame) -> np.ndarray:
        """
        Return a normalized anomaly_score in [0, 1] for each row (higher =
        more anomalous). Scores are clipped to [0, 1]; inference-time scores
        can fall slightly outside the training-time min/max range, so
        clipping keeps the output well-defined for the API/dashboard.
        """
        if not self._is_fitted:
            raise RuntimeError("Model must be fit (or loaded) before scoring.")

        X = self._build_design_matrix(df)
        raw_scores = -self.model.decision_function(X)

        score_range = self._raw_score_max - self._raw_score_min
        if score_range == 0:
            # Degenerate case (e.g. training set was perfectly uniform).
            normalized = np.zeros_like(raw_scores)
        else:
            normalized = (raw_scores - self._raw_score_min) / score_range

        return np.clip(normalized, 0.0, 1.0)

    def predict(self, df: pd.DataFrame, threshold: float = 0.6) -> np.ndarray:
        """Return a boolean array: True where anomaly_score >= threshold."""
        return self.score(df) >= threshold

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, output_dir: str, training_data_path: str = None,
              window_start: str = None, window_end: str = None):
        """
        Save the fitted model and its metadata. Metadata follows the contract
        in docs/ml_design.md section 5, plus fields needed by the Model
        Monitoring dashboard page (training date, current model status).
        """
        if not self._is_fitted:
            raise RuntimeError("Cannot save an unfitted model.")

        os.makedirs(output_dir, exist_ok=True)
        joblib.dump(self.model, os.path.join(output_dir, MODEL_FILENAME))

        metadata = {
            "model_type": "IsolationForest",
            "feature_list": NUMERIC_FEATURE_COLUMNS,
            "service_categories": self.service_categories,
            "n_estimators": self.n_estimators,
            "contamination": self.contamination,
            "random_state": self.random_state,
            "raw_score_min": self._raw_score_min,
            "raw_score_max": self._raw_score_max,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "training_data_path": training_data_path,
            "training_window_start": window_start,
            "training_window_end": window_end,
            "version": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        }
        with open(os.path.join(output_dir, METADATA_FILENAME), "w") as f:
            json.dump(metadata, f, indent=2)

        return metadata

    @classmethod
    def load(cls, model_dir: str) -> "IsolationForestModel":
        """Reconstruct a fitted IsolationForestModel from a saved directory."""
        metadata_path = os.path.join(model_dir, METADATA_FILENAME)
        model_path = os.path.join(model_dir, MODEL_FILENAME)

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        instance = cls(
            n_estimators=metadata["n_estimators"],
            contamination=metadata["contamination"],
            random_state=metadata["random_state"],
            service_categories=metadata["service_categories"],
        )
        instance.model = joblib.load(model_path)
        instance._raw_score_min = metadata["raw_score_min"]
        instance._raw_score_max = metadata["raw_score_max"]
        instance._is_fitted = True

        return instance