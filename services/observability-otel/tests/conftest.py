import os
import sys
from pathlib import Path

os.environ.setdefault("DATA_PATH", "/tmp/observability-otel-test-state.json")
os.environ.setdefault("OTEL_COLLECTOR_URL", "http://localhost:13133")

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
