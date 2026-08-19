"""
alert_service.py

Watches for newly detected anomalies that cross the alert threshold and
dispatches notifications. In this simplified setup, "dispatching" always
logs to stdout/monitoring/logs (so behavior is visible without any external
service configured) and additionally sends an email if SMTP settings are
present in the environment - this mirrors how a real observability stack
separates "detect" from "notify" so alert channels can be swapped freely
without touching detection logic.

Typical call pattern (see core/scheduler.py):
    summary = anomaly_detection.run_detection(db, ...)
    alert_service.dispatch_pending_alerts(db)
"""

import os
import smtplib
import sys
from email.message import EmailMessage
from typing import List

from sqlalchemy.orm import Session

try:
    from app.core.config import settings
    from app.db import models as db_models
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from app.core.config import settings
    from app.db import models as db_models


# Only these severities are worth interrupting someone for. "medium" and
# "low" anomalies are still visible in the dashboard/API, just not alerted.
ALERTABLE_SEVERITIES = {"high", "critical"}


def get_pending_alerts(db: Session, min_score: float = None) -> List[db_models.AnomalyRecord]:
    """
    Fetch anomalies that cross the alert threshold and haven't been alerted
    on yet. This is what dispatch_pending_alerts acts on, but exposed
    separately so routes/tests can inspect what *would* alert without
    actually sending anything.
    """
    min_score = min_score if min_score is not None else settings.anomaly_alert_threshold

    return (
        db.query(db_models.AnomalyRecord)
        .filter(
            db_models.AnomalyRecord.anomaly_score >= min_score,
            db_models.AnomalyRecord.alert_sent.is_(False),
            db_models.AnomalyRecord.severity.in_(ALERTABLE_SEVERITIES),
        )
        .order_by(db_models.AnomalyRecord.anomaly_score.desc())
        .all()
    )


def format_alert_message(anomaly: db_models.AnomalyRecord) -> str:
    return (
        f"[{anomaly.severity.upper()}] Anomaly detected on '{anomaly.service_name}' "
        f"at {anomaly.window_start.isoformat()} - "
        f"score={anomaly.anomaly_score:.2f}, error_rate={anomaly.error_rate:.1%}, "
        f"log_volume_delta={anomaly.log_volume_delta:+.1f}%"
    )


def send_console_alert(anomaly: db_models.AnomalyRecord) -> None:
    """Always-available alert channel: structured log line. Wired to
    monitoring/logs in a real deployment via the logging config in
    core/logging.py."""
    print(f"[ALERT] {format_alert_message(anomaly)}")


def send_email_alert(anomaly: db_models.AnomalyRecord) -> bool:
    """
    Optional email channel. Only attempts to send if SMTP_HOST/SMTP_FROM/
    ALERT_EMAIL_TO are configured in the environment; otherwise a no-op.
    Returns True if an email was actually sent.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_from = os.getenv("SMTP_FROM")
    alert_to = os.getenv("ALERT_EMAIL_TO")

    if not (smtp_host and smtp_from and alert_to):
        return False

    msg = EmailMessage()
    msg["Subject"] = f"LogSense alert: {anomaly.severity.upper()} anomaly on {anomaly.service_name}"
    msg["From"] = smtp_from
    msg["To"] = alert_to
    msg.set_content(format_alert_message(anomaly))

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)

    return True


def dispatch_pending_alerts(db: Session) -> dict:
    """
    Find and send alerts for every anomaly that qualifies, marking each as
    alert_sent so it's never re-alerted. Returns a summary for logging.
    """
    pending = get_pending_alerts(db)

    email_sent_count = 0
    for anomaly in pending:
        send_console_alert(anomaly)
        try:
            if send_email_alert(anomaly):
                email_sent_count += 1
        except Exception as exc:  # noqa: BLE001 - alert delivery must never crash detection
            print(f"[alert_service] Email alert failed for anomaly {anomaly.id}: {exc}")

        anomaly.alert_sent = True

    db.commit()

    return {
        "alerts_dispatched": len(pending),
        "emails_sent": email_sent_count,
    }