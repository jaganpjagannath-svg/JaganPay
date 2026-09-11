import json
import logging
import threading
from datetime import datetime
import requests
from flask import current_app

logger = logging.getLogger("jaganpay.webhook")


def _dispatch_async(url: str, payload: dict):
    """Background worker to dispatch webhook without blocking main request."""
    try:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "JaganPay-EventDispatcher/1.0",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=3.0)
        logger.info(f"Dispatched webhook to {url} - Status {resp.status_code}")
    except requests.exceptions.RequestException as e:
        logger.debug(f"Optional n8n webhook unreachable ({url}): {e}. Continuing normally.")
    except Exception as e:
        logger.warning(f"Unexpected webhook error: {e}")


def dispatch_event(event_type: str, payload: dict):
    """
    Central event dispatcher for n8n automation workflows.
    Runs asynchronously in a daemon thread so user payment/login flow is never slowed down.
    """
    try:
        app = current_app._get_current_object()
        webhooks = app.config.get("N8N_WEBHOOKS", {})
        url = webhooks.get(event_type)

        if not url:
            return

        envelope = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "simulation": True,
            "data": payload,
        }

        # Spawn non-blocking thread
        thread = threading.Thread(target=_dispatch_async, args=(url, envelope), daemon=True)
        thread.start()
    except Exception as e:
        logger.warning(f"Failed to initiate event dispatch {event_type}: {e}")
