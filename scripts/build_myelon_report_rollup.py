#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from myelon_report_common import write_rollup_reports


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build top-level rollup reports from retained vllm.rs benchmark report.json files"
    )
    parser.add_argument(
        "--campaign-root",
        type=Path,
        required=True,
        help="Root directory containing retained benchmark campaign subdirectories",
    )
    args = parser.parse_args()

    outputs = write_rollup_reports(args.campaign_root.resolve())
    print(json.dumps(outputs, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
