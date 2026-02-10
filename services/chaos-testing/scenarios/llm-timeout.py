from __future__ import annotations

import argparse
import time
from common import add_toxic, remove_toxic, timed_probe, write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--report-dir", required=True)
    args = parser.parse_args()

    add_toxic("ollama-proxy", "timeout10", "timeout", {"timeout": 10})
    t0 = time.time()
    result = timed_probe("http://omni-token-infinity:9600/health")
    failover_detection = int((time.time() - t0) * 1000)
    remove_toxic("ollama-proxy", "timeout10")

    report = {
        "scenario": "llm-timeout",
        "target": args.target,
        "probe": result,
        "failover_detection_ms": failover_detection,
        "langfuse_failover_expected": True,
    }
    write_report(args.report_dir, "llm-timeout-report.json", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
