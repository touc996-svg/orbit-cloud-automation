#!/usr/bin/env python3
"""ORBIT Batch 5: production readiness and state backup verification."""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

ENVIRONMENTS = ("development", "staging", "production")

REQUIRED_FILES = (
    "infra/production-readiness/versions.tf",
    "infra/production-readiness/provider.tf",
    "infra/production-readiness/variables.tf",
    "infra/production-readiness/main.tf",
    "infra/production-readiness/outputs.tf",
    ".github/workflows/orbit-batch5-ci.yml",
    "docs/production-readiness.md",
)


def validate_state_document(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "State document must be a JSON object."

    required = {"version", "serial", "lineage", "resources"}

    missing = required - data.keys()
    if missing:
        return False, f"Missing state fields: {', '.join(sorted(missing))}"

    if not isinstance(data["version"], int) or data["version"] < 1:
        return False, "Invalid Terraform state version."

    if not isinstance(data["serial"], int) or data["serial"] < 0:
        return False, "Invalid Terraform state serial."

    if not isinstance(data["lineage"], str) or not data["lineage"].strip():
        return False, "Invalid Terraform state lineage."

    if not isinstance(data["resources"], list):
        return False, "Terraform state resources must be a list."

    return True, "Terraform state structure is valid."


def verify_state_backup(path: Path) -> bool:
    if not path.is_file():
        print(f"FAIL: Backup file does not exist: {path}")
        return False

    try:
        mode = stat.S_IMODE(path.stat().st_mode)

        if mode & 0o077:
            print(
                "FAIL: Backup permissions are too open. "
                "Use chmod 600 on this sensitive file."
            )
            return False

        data = json.loads(path.read_text(encoding="utf-8"))

    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL: Cannot safely read state backup: {error}")
        return False

    valid, message = validate_state_document(data)
    print(("PASS: " if valid else "FAIL: ") + message)

    if valid:
        print(f"State serial: {data['serial']}")
        print(f"Resource entries: {len(data['resources'])}")
        print("Sensitive state content was not printed.")

    return valid


def ci_preflight(root: Path = ROOT) -> bool:
    failures = []

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            failures.append(f"Missing required file: {relative}")

    for environment in ENVIRONMENTS:
        path = root / "infra" / "environments" / f"{environment}.tfvars"

        if not path.is_file():
            failures.append(f"Missing environment configuration: {path}")
            continue

        content = path.read_text(encoding="utf-8")
        match = re.search(
            r'(?m)^\s*environment\s*=\s*"([^"]+)"\s*$',
            content,
        )

        if not match or match.group(1) != environment:
            failures.append(
                f"Environment value does not match filename: {path}"
            )

    root_versions = root / "infra" / "versions.tf"

    if root_versions.exists():
        content = root_versions.read_text(encoding="utf-8")
        if re.search(r'backend\s+"s3"', content):
            failures.append(
                "Main Terraform backend was changed unexpectedly."
            )

    ignore_file = root / ".gitignore"
    ignore_content = (
        ignore_file.read_text(encoding="utf-8")
        if ignore_file.exists()
        else ""
    )

    for pattern in ("*.tfstate", "*.tfstate.*", "*.tfplan", "/backups/"):
        if pattern not in ignore_content.splitlines():
            failures.append(f"Missing .gitignore protection: {pattern}")

    workflow_dir = root / ".github" / "workflows"

    if workflow_dir.exists():
        for path in workflow_dir.glob("*.y*ml"):
            content = path.read_text(encoding="utf-8")
            if re.search(r"terraform\s+apply", content, re.IGNORECASE):
                failures.append(
                    f"Unsafe Terraform apply command found in {path.name}"
                )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return False

    print("PASS: Production-readiness stack files.")
    print("PASS: Development, staging and production configurations.")
    print("PASS: Existing Terraform backend remains unchanged.")
    print("PASS: State and plan files are protected by .gitignore.")
    print("PASS: GitHub workflows contain no Terraform apply command.")
    print("PASS: ORBIT Batch 5 CI preflight.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ORBIT production readiness checks"
    )

    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ci", help="Run offline production readiness checks")

    backup = commands.add_parser(
        "verify-backup",
        help="Validate a protected local Terraform state backup",
    )
    backup.add_argument("path", type=Path)

    args = parser.parse_args()

    if args.command == "ci":
        return 0 if ci_preflight() else 1

    if args.command == "verify-backup":
        return 0 if verify_state_backup(args.path) else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
