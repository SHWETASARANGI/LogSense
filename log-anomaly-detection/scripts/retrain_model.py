"""
retrain_model.py

Standalone retraining job - the thing you'd point a cron job, a CI pipeline,
or an orchestrator (Airflow, Prefect, a k8s CronJob) at, so the model
retrains on a schedule without needing the API to be running.

Optionally regenerates the feature table from the latest raw logs before
retraining, so this can be the single entry point for "pick up whatever's
new in data/raw/, refresh features, retrain, promote" - the same three
pipeline stages the FastAPI scheduler runs, but callable independently of
the web process.

Usage:
    # Retrain on the existing feature table:
    python scripts/retrain_model.py

    # Rebuild features from raw logs first, then retrain:
    python scripts/retrain_model.py --rebuild-features --raw-logs "data/raw/*.jsonl"
"""

import argparse
import os
import sys

# Allow running this script directly (python scripts/retrain_model.py) by
# putting backend/ on the path, since app.* modules live there.
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.db.database import SessionLocal, init_db  # noqa: E402
from app.ml.train import train_and_save  # noqa: E402
from app.services import feature_engineering, model_registry  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Retrain the LogSense anomaly detection model.")
    parser.add_argument("--features", type=str, default="data/processed/features.parquet",
                         help="Path to the feature table to train on (or to write to, if rebuilding).")
    parser.add_argument("--rebuild-features", action="store_true",
                         help="Regenerate the feature table from raw logs before training.")
    parser.add_argument("--raw-logs", type=str, default="data/raw/*.jsonl",
                         help="Glob of raw log files to use when --rebuild-features is set.")
    parser.add_argument("--window-seconds", type=int, default=60)
    parser.add_argument("--output-dir", type=str, default="models/isolation_forest")
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--contamination", type=float, default=0.05)
    args = parser.parse_args()

    if args.rebuild_features:
        print(f"[retrain_model] Rebuilding features from: {args.raw_logs}")
        raw_df = feature_engineering.load_raw_logs(args.raw_logs)
        features = feature_engineering.compute_features(raw_df, window_seconds=args.window_seconds)
        feature_engineering.save_features(features, args.features)
        print(f"[retrain_model] Wrote {len(features)} feature rows to {args.features}")

    metadata = train_and_save(
        features_path=args.features,
        output_dir=args.output_dir,
        n_estimators=args.n_estimators,
        contamination=args.contamination,
    )

    # Promote the new model to active in the DB, same as the API route does,
    # so a cron-triggered retrain is indistinguishable from a manual one.
    init_db()
    db = SessionLocal()
    try:
        model_registry.sync_model_metadata(db, model_dir=args.output_dir)
    finally:
        db.close()

    print(f"[retrain_model] Retraining complete. New active version: {metadata['version']}")


if __name__ == "__main__":
    main()