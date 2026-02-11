from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4

CAMPAIGNS = {}
METRICS = {}
LEADS = {}
LEAD_ACTIVITIES = {}
AUDIENCES = {}
SEQUENCES = {}
LANDING_PAGES = {}
CALENDAR = {}
COMPETITORS = {}
COMPETITOR_SNAPSHOTS = {}
AB_TESTS = {}

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def uid() -> str:
    return str(uuid4())
