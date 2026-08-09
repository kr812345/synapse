#!/usr/bin/env python3
"""
Synapse AI OS — E2E Test Runner Harness CLI Script.

Executes test suite by tier selection (1, 2, 3, 4, or all), tracks execution time,
invokes pytest with tier marker expressions, and writes JSON summary reports.
"""

import sys
import os
import argparse
import subprocess
import json
import time
from datetime import datetime, timezone


def parse_args():
    parser = argparse.ArgumentParser(
        description="Synapse AI OS E2E Test Runner Harness",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--tier", "-t",
        choices=["1", "2", "3", "4", "5", "all"],
        default="all",
        help="Target test tier to execute (1: Feature Coverage, 2: Boundary/Corner, 3: Integrations, 4: Workflows, 5: Adversarial, all: Full Suite)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output mode for pytest"
    )
    parser.add_argument(
        "--report-file", "-r",
        default="tests/e2e_report.json",
        help="Path to save JSON summary report"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    pytest_bin = os.path.join(workspace_dir, ".venv", "bin", "pytest")

    if not os.path.isfile(pytest_bin):
        print(f"Error: pytest binary not found at {pytest_bin}")
        sys.exit(1)

    tier_marker_map = {
        "1": "tier1",
        "2": "tier2",
        "3": "tier3",
        "4": "tier4",
        "5": "tier5",
        "all": "tier1 or tier2 or tier3 or tier4 or tier5 or e2e"
    }

    marker_expr = tier_marker_map[args.tier]

    print("=" * 80)
    print("                 SYNAPSE AI OS — E2E TEST RUNNER HARNESS                 ")
    print("=" * 80)
    print(f" Target Tier       : Tier {args.tier.upper()}")
    print(f" Marker Expression : '{marker_expr}'")
    print(f" Workspace Dir     : {workspace_dir}")
    print("=" * 80 + "\n")

    cmd = [pytest_bin]
    if args.tier != "all":
        cmd.extend(["-m", marker_expr])
    if args.verbose:
        cmd.append("-v")

    start_time = time.time()
    result = subprocess.run(cmd, cwd=workspace_dir)
    elapsed_seconds = round(time.time() - start_time, 3)

    status = "passed" if result.returncode == 0 else "failed"

    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tier_selected": args.tier,
        "marker_expression": marker_expr,
        "status": status,
        "exit_code": result.returncode,
        "execution_time_seconds": elapsed_seconds,
    }

    report_path = os.path.join(workspace_dir, args.report_file)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print("\n" + "-" * 80)
    print(f" Execution Summary:")
    print(f"   Status:        {status.upper()}")
    print(f"   Exit Code:     {result.returncode}")
    print(f"   Duration:      {elapsed_seconds}s")
    print(f"   Report Saved:  {report_path}")
    print("-" * 80 + "\n")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
