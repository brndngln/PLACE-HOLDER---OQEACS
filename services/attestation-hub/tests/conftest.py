import os
import sys
from pathlib import Path

os.environ.setdefault("DATA_PATH", "/tmp/attestation-hub-test-store.json")
os.environ.setdefault("ATTESTATION_HMAC_KEY", "unit-test-key")

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
