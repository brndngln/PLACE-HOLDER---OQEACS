import os
import sys
from pathlib import Path

os.environ.setdefault("DATA_PATH", "/tmp/policy-engine-test-store.json")
os.environ.setdefault("POLICIES_DIR", "/tmp/policy-engine-test-policies")
os.environ.setdefault("OPA_SYNC_ENABLED", "false")

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
