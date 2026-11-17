import json
import logging
from pathlib import Path

from flask import current_app

from app.db import get_db


def configure_audit_logger(app):
    path = Path(app.config["AUDIT_LOG_PATH"])
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("sigoc.audit")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)


def audit(operation, result, correlation_id, user=None, campaign=None, record_key=None, details=None):
    safe_details = details or {}
    db = get_db()
    db.execute(
        """INSERT INTO audit_events
           (correlation_id, user_id, username, operation, campaign, record_key, result, details)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            correlation_id, user.get("id") if user else None, user.get("username") if user else None,
            operation, campaign, record_key, result, json.dumps(safe_details, ensure_ascii=False),
        ),
    )
    db.commit()
    logging.getLogger("sigoc.audit").info(json.dumps({
        "correlation_id": correlation_id, "username": user.get("username") if user else None,
        "operation": operation, "campaign": campaign, "record_key": record_key,
        "result": result, "details": safe_details,
    }, ensure_ascii=False))

