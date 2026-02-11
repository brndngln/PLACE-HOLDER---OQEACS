"""
Omni Quantum Elite — Event Processor
Consumes platform events from Redis Streams and routes
notifications to Mattermost and Omi.
"""

import json
import logging
import os
import time

import httpx
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://omni-redis:6379/11")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://omni-orchestrator:9500")
MATTERMOST_WEBHOOK = os.getenv("MATTERMOST_WEBHOOK", "")
OMI_WEBHOOK = os.getenv("OMI_WEBHOOK", "")

STREAM_KEY = "omni:events"
GROUP_NAME = "event-processor"
CONSUMER_NAME = "processor-1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("omni-event-processor")


def send_mattermost(message: str):
    if not MATTERMOST_WEBHOOK:
        return
    try:
        httpx.post(MATTERMOST_WEBHOOK, json={"text": message}, timeout=5)
    except Exception as e:
        logger.error(f"Mattermost notification failed: {e}")


def send_omi(message: str, severity: str = "info"):
    if not OMI_WEBHOOK:
        return
    try:
        httpx.post(OMI_WEBHOOK, json={"message": message, "severity": severity}, timeout=5)
    except Exception as e:
        logger.error(f"Omi notification failed: {e}")


def process_event(event_data: dict):
    """Process a single platform event."""
    event_type = event_data.get("type", "unknown")
    service = event_data.get("service", "unknown")
    timestamp = event_data.get("timestamp", "")

    if event_type == "status_change":
        from_status = event_data.get("from", "?")
        to_status = event_data.get("to", "?")
        tier = event_data.get("tier", "standard")

        emoji_map = {"healthy": "🟢", "degraded": "🟡", "down": "🔴"}
        emoji = emoji_map.get(to_status, "⚪")

        msg = f"{emoji} **{service}** changed from {from_status} → **{to_status}**"

        if to_status == "down" and tier == "critical":
            send_mattermost(f"🚨 **CRITICAL ALERT** {msg}")
            send_omi(f"Critical alert: {service} is down", severity="critical")
        elif to_status == "down":
            send_mattermost(f"⚠️ {msg}")
            send_omi(f"Warning: {service} is down", severity="warning")
        elif to_status == "healthy" and from_status == "down":
            send_mattermost(f"✅ **RECOVERED** {msg}")
            send_omi(f"{service} has recovered", severity="info")

    elif event_type == "backup_completed":
        send_mattermost(f"💾 Backup completed for **{service}**")

    elif event_type == "deploy_completed":
        send_mattermost(f"🚀 Deployment completed for **{service}**")

    elif event_type == "secret_rotated":
        send_mattermost(f"🔐 Secret rotated for **{service}**")

    logger.info(f"Processed event: {event_type} for {service}")


def main():
    logger.info("📡 Omni Event Processor starting...")

    # Connect to Redis
    r = None
    while not r:
        try:
            r = redis.from_url(REDIS_URL)
            r.ping()
            logger.info("✅ Connected to Redis")
        except Exception as e:
            logger.warning(f"Redis not ready: {e}, retrying in 5s...")
            time.sleep(5)
            r = None

    # Create consumer group (idempotent)
    try:
        r.xgroup_create(STREAM_KEY, GROUP_NAME, id="0", mkstream=True)
        logger.info(f"Created consumer group '{GROUP_NAME}'")
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info(f"Consumer group '{GROUP_NAME}' already exists")
        else:
            raise

    logger.info("Listening for events...")

    while True:
        try:
            # Read from stream with 5s timeout
            entries = r.xreadgroup(
                GROUP_NAME, CONSUMER_NAME,
                {STREAM_KEY: ">"},
                count=10, block=5000,
            )

            if not entries:
                continue

            for stream, messages in entries:
                for msg_id, data in messages:
                    try:
                        # Decode event
                        event = {}
                        for k, v in data.items():
                            key = k.decode() if isinstance(k, bytes) else k
                            val = v.decode() if isinstance(v, bytes) else v
                            try:
                                val = json.loads(val)
                            except (json.JSONDecodeError, TypeError):
                                pass
                            event[key] = val

                        process_event(event)

                        # Acknowledge
                        r.xack(STREAM_KEY, GROUP_NAME, msg_id)
                    except Exception as e:
                        logger.error(f"Failed to process message {msg_id}: {e}")

        except redis.ConnectionError:
            logger.error("Lost Redis connection, reconnecting in 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Event loop error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
