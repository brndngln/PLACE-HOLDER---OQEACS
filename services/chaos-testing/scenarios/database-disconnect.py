from __future__ import annotations

import argparse
import time
from common import add_toxic, remove_toxic, timed_probe, write_report, post_mm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--report-dir", required=True)
    args = parser.parse_args()

    add_toxic("postgres-proxy", "dbdown", "timeout", {"timeout": 1})
    start = time.time()
    failed = timed_probe("http://omni-orchestrator:9500/health")
    detection = int(time.time() - start)
    post_mm("[chaos] database-disconnect simulated")
    remove_toxic("postgres-proxy", "dbdown")
    recovered = timed_probe("http://omni-orchestrator:9500/health")

    report = {
        "scenario": "database-disconnect",
        "target": args.target,
        "failure_detection_seconds": detection,
        "failure_probe": failed,
        "recovered_probe": recovered,
        "error_response_quality": "structured" if not failed.get("ok", True) else "unknown",
    }
    write_report(args.report_dir, "database-disconnect-report.json", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
