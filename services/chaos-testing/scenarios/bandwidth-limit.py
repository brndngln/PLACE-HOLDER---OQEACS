from __future__ import annotations

import argparse
from common import add_toxic, remove_toxic, timed_probe, write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--report-dir", required=True)
    args = parser.parse_args()

    add_toxic("minio-proxy", "bw100kb", "bandwidth", {"rate": 100})
    backup_probe = timed_probe("http://omni-backup-orchestrator:8187/health")
    remove_toxic("minio-proxy", "bw100kb")

    report = {
        "scenario": "bandwidth-limit",
        "target": args.target,
        "probe": backup_probe,
        "transfer_rate_kbps": 100,
    }
    write_report(args.report_dir, "bandwidth-limit-report.json", report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
