"""
scheduler.py

Runs the detection pipeline (feature engineering -> scoring -> persistence
-> alerting) on a fixed interval, simulating a production monitoring loop
where LogSense continuously watches incoming logs rather than being run
by hand.

Started from main.py on app startup and stopped on shutdown. Uses
APScheduler's BackgroundScheduler so it runs inside the same process as the
FastAPI app - no separate worker/container is required for this project's
scope (see docs/architecture.md for the tradeoffs of that choice).
"""

import glob
import os
import sys

from apscheduler.schedulers.background import BackgroundScheduler

try:
    from app.core.config import settings
    from app.db.database import SessionLocal
    from app.services import alert_service, anomaly_detection
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from app.core.config import settings
    from app.db.database import SessionLocal
    from app.services import alert_service, anomaly_detection


# In this simplified setup, "new incoming logs" means whatever's currently in
# data/raw/. A real deployment would instead point ingestion_service.py at a
# live source (CloudWatch, Elasticsearch, a message queue) and only pass this
# job the slice of logs newer than the last run; see docs/architecture.md.
RAW_LOGS_GLOB = os.getenv("RAW_LOGS_GLOB", settings.raw_logs_glob)

_scheduler: BackgroundScheduler = None


def run_detection_cycle():
    """
    One full cycle: detect anomalies over the current raw logs, then send
    alerts for anything that newly crosses the alert threshold. Wrapped in
    try/except because APScheduler silently swallows exceptions in
    background jobs otherwise, which would make failures invisible.
    """
    db = SessionLocal()
    try:
        if not glob.glob(RAW_LOGS_GLOB):
            print(f"[scheduler] No raw log files matching {RAW_LOGS_GLOB} - skipping this cycle.")
            return

        summary = anomaly_detection.run_detection(db, raw_logs_path=RAW_LOGS_GLOB)
        print(f"[scheduler] Detection cycle complete: {summary}")

        alert_summary = alert_service.dispatch_pending_alerts(db)
        print(f"[scheduler] Alert dispatch complete: {alert_summary}")

    except FileNotFoundError as exc:
        # No trained model yet - expected on a fresh install before the
        # first ml/train.py run. Not treated as an error.
        print(f"[scheduler] Skipping cycle - {exc}")
    except Exception as exc:  # noqa: BLE001 - a bad cycle must never kill the scheduler thread
        print(f"[scheduler] Detection cycle failed: {exc}")
    finally:
        db.close()


def start_scheduler(interval_minutes: int = None) -> BackgroundScheduler:
    """Start the background scheduler. Called once from main.py's startup event."""
    global _scheduler

    interval_minutes = interval_minutes or settings.scheduler_interval_minutes

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_detection_cycle,
        "interval",
        minutes=interval_minutes,
        id="detection_cycle",
        next_run_time=None,  # first run waits one full interval; call run_detection_cycle() directly for an immediate run
    )
    _scheduler.start()
    print(f"[scheduler] Started - running detection every {interval_minutes} minute(s).")
    return _scheduler


def stop_scheduler():
    """Stop the background scheduler. Called from main.py's shutdown event."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        print("[scheduler] Stopped.")