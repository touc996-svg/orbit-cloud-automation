#!/usr/bin/env python3
"""Safe local automation entry point for the ORBIT Terraform project."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
INFRA_DIR = ROOT / "infra"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ORBIT infrastructure automation (no apply command is provided)."
    )
    parser.add_argument(
        "command",
        choices=("doctor", "validate", "plan", "security-scan"),
        help="doctor checks tools/credentials; validate checks Terraform; plan previews changes.",
    )
    return parser


def run_command(command: Sequence[str], *, cwd: Path | None = None) -> int:
    print("$ " + " ".join(command), flush=True)
    try:
        completed = subprocess.run(list(command), cwd=cwd, check=False)
    except FileNotFoundError:
        print(f"Required executable not found: {command[0]}", file=sys.stderr)
        return 127
    return completed.returncode


def doctor() -> int:
    missing: list[str] = []
    for executable in ("terraform", "aws", "git"):
        resolved = shutil.which(executable)
        if resolved:
            print(f"[OK] {executable}: {resolved}")
        else:
            print(f"[MISSING] {executable}")
            missing.append(executable)

    if "terraform" in missing:
        print("Install Terraform before running validate or plan.", file=sys.stderr)
        return 1

    if "aws" not in missing:
        print("Checking AWS caller identity (read-only)...")
        code = run_command(["aws", "sts", "get-caller-identity", "--output", "json"])
        if code != 0:
            print("[WARN] AWS CLI is present, but caller identity could not be confirmed.")
        else:
            print("[OK] AWS caller identity is available.")
    else:
        print("[WARN] AWS CLI is not installed; local Python tests can still run.")
    return 0


def validate() -> int:
    steps = [
        (["terraform", "fmt", "-check", "-recursive"], ROOT),
        (["terraform", "init", "-backend=false", "-input=false"], INFRA_DIR),
        (["terraform", "validate"], INFRA_DIR),
    ]
    for command, cwd in steps:
        code = run_command(command, cwd=cwd)
        if code != 0:
            return code
    return 0


def plan() -> int:
    print("This command only creates a Terraform plan; it does not apply infrastructure.")
    return run_command(
        ["terraform", "plan", "-input=false", "-out=orbit.tfplan"], cwd=INFRA_DIR
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        return doctor()
    if args.command == "validate":
        return validate()
    if args.command == "plan":
        return plan()
    if args.command == "security-scan":
        return run_command([sys.executable, str(ROOT / "tools" / "security_scan.py")], cwd=ROOT)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
