#!/usr/bin/env python
"""Raspberry Pi performance benchmark for the configured profiles.

Runs ``avfm run`` in passive mode (so no servo movement is required) and reads
the resulting ``run.json``. Hardware results are intentionally not fabricated:
this script only reports what actually ran.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        default="rpi",
        choices=["rpi", "rpi_low_power", "rpi_passive", "rpi_tracking_only"],
    )
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--json", default=None)
    args = parser.parse_args()

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    output = Path("var") / "bench" / f"{args.profile}-{stamp}"
    command = [
        sys.executable,
        "-m",
        "avfm",
        "run",
        "--source",
        "picamera",
        "--servo",
        "none",
        "--config",
        f"configs/{args.profile}.toml",
        "--no-show",
        "--duration",
        str(args.duration),
        "--record-dir",
        str(output),
        "--json",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    run_json = output / "run.json"
    report = {}
    if run_json.exists():
        report = json.loads(run_json.read_text(encoding="utf-8")).get("report", {})
    payload = {
        "kind": "rpi_bench",
        "created_at": datetime.now(UTC).isoformat(),
        "profile": args.profile,
        "duration_s": args.duration,
        "returncode": result.returncode,
        "report": report,
        "stderr_tail": result.stderr.strip()[-4000:],
    }
    if args.json:
        target = Path(args.json)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if result.returncode == 0 else result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
