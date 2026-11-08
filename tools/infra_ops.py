#!/usr/bin/env python3
"""ORBIT Batch 4: environment planning, drift detection and state backup."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"
BACKUPS = ROOT / "backups"

ENVIRONMENTS = ("development", "staging", "production")


def execute(command: list[str], cwd: Path | None = None) -> int:
    print(f"\n$ {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd or ROOT,
            check=False,
        )
        return result.returncode
    except FileNotFoundError:
        print(f"ERROR: Executable not found: {command[0]}")
        return 127


def valid_environment(environment: str) -> bool:
    return environment in ENVIRONMENTS


def is_root_arn(arn: str) -> bool:
    return bool(re.search(r":root$", arn or ""))


def check_aws_identity() -> bool:
    if not shutil.which("aws"):
        print("ERROR: AWS CLI is required.")
        return False

    result = subprocess.run(
        ["aws", "sts", "get-caller-identity", "--output", "json"],
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        print("ERROR: AWS identity verification failed.")
        print(result.stderr)
        return False

    try:
        identity = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("ERROR: Invalid AWS identity response.")
        return False

    arn = identity.get("Arn", "")
    account = identity.get("Account", "")

    print(f"AWS identity: {arn}")

    if is_root_arn(arn):
        print("BLOCKED: AWS root credentials are prohibited.")
        return False

    if not re.fullmatch(r"\d{12}", account):
        print("ERROR: Invalid AWS account ID.")
        return False

    expected = os.getenv("ORBIT_ALLOWED_AWS_ACCOUNT", "")

    if not re.fullmatch(r"\d{12}", expected):
        print(
            "ERROR: Set ORBIT_ALLOWED_AWS_ACCOUNT to the approved "
            "12-digit AWS account ID."
        )
        return False

    if account != expected:
        print("BLOCKED: AWS account does not match the approved account.")
        return False

    print("PASS: Non-root AWS identity and account restriction.")
    return True


def backend_settings(environment: str) -> dict[str, str] | None:
    bucket = os.getenv("ORBIT_TF_STATE_BUCKET", "")
    region = os.getenv("ORBIT_TF_STATE_REGION", "")
    table = os.getenv("ORBIT_TF_STATE_LOCK_TABLE", "")

    if not all((bucket, region, table)):
        print(
            "ERROR: Configure ORBIT_TF_STATE_BUCKET, "
            "ORBIT_TF_STATE_REGION and ORBIT_TF_STATE_LOCK_TABLE."
        )
        return None

    if "<" in bucket or "REPLACE" in bucket.upper():
        print("ERROR: Replace the Terraform state bucket placeholder.")
        return None

    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
        print("ERROR: Invalid S3 state bucket name.")
        return None

    if not re.fullmatch(r"[A-Za-z0-9._-]+", table):
        print("ERROR: Invalid DynamoDB locking table name.")
        return None

    if not re.fullmatch(r"[a-z0-9-]+", region):
        print("ERROR: Invalid AWS region.")
        return None

    return {
        "bucket": bucket,
        "region": region,
        "dynamodb_table": table,
        "key": f"orbit/{environment}/terraform.tfstate",
        "encrypt": "true",
    }


def copy_infrastructure(destination: Path) -> bool:
    try:
        shutil.copytree(
            INFRA,
            destination,
            ignore=shutil.ignore_patterns(
                ".terraform",
                "*.tfstate",
                "*.tfstate.*",
                "*.tfplan",
                "backups",
            ),
        )
    except OSError as error:
        print(f"ERROR: Cannot prepare isolated Terraform directory: {error}")
        return False

    versions = destination / "versions.tf"

    if not versions.is_file():
        print("ERROR: infra/versions.tf is missing.")
        return False

    content = versions.read_text(encoding="utf-8")

    if 'backend "s3"' not in content:
        updated, count = re.subn(
            r"(?m)^terraform\s*\{",
            'terraform {\n  backend "s3" {}\n',
            content,
            count=1,
        )

        if count != 1:
            print("ERROR: Could not prepare temporary S3 backend.")
            return False

        versions.write_text(updated, encoding="utf-8")

    return True


def remote_operation(environment: str, operation: str) -> int:
    if not valid_environment(environment):
        print("ERROR: Invalid environment.")
        return 1

    variable_file = INFRA / "environments" / f"{environment}.tfvars"

    if not variable_file.is_file():
        print(f"ERROR: Missing environment variables: {variable_file}")
        return 1

    settings = backend_settings(environment)

    if settings is None or not check_aws_identity():
        return 1

    with tempfile.TemporaryDirectory(prefix="orbit-terraform-") as directory:
        work = Path(directory) / "infra"

        if not copy_infrastructure(work):
            return 1

        copied_vars = work / "environments" / f"{environment}.tfvars"
        if not copied_vars.is_file():
            print("ERROR: Environment variables were not copied.")
            return 1

        backend_args = [
            "terraform",
            f"-chdir={work}",
            "init",
            "-reconfigure",
            "-input=false",
            "-no-color",
        ]

        for key, value in settings.items():
            backend_args.append(f"-backend-config={key}={value}")

        if execute(backend_args) != 0:
            print("ERROR: Remote Terraform backend initialization failed.")
            return 1

        if operation == "drift":
            state_result = subprocess.run(
                ["terraform", f"-chdir={work}", "state", "list"],
                text=True,
                capture_output=True,
                check=False,
            )

            if state_result.returncode != 0 or not state_result.stdout.strip():
                print(
                    "BLOCKED: No managed resources found in remote state. "
                    "Refusing to report a false clean drift result."
                )
                return 1

        if operation == "backup-state":
            return backup_remote_state(work, environment)

        command = [
            "terraform",
            f"-chdir={work}",
            "plan",
            "-input=false",
            "-no-color",
            "-lock-timeout=60s",
            f"-var-file=environments/{environment}.tfvars",
        ]

        if operation == "drift":
            command.extend(["-refresh-only", "-detailed-exitcode"])

        result = execute(command)

        if operation == "drift":
            if result == 0:
                print(f"NO DRIFT DETECTED: {environment}")
                return 0
            if result == 2:
                print(f"DRIFT DETECTED: {environment}. Review the plan.")
                return 2

        if result == 0:
            print(f"PASS: {operation} completed for {environment}.")
            print("No infrastructure changes were applied.")
        else:
            print(f"FAIL: {operation} failed for {environment}.")

        return result


def backup_remote_state(work: Path, environment: str) -> int:
    command = ["terraform", f"-chdir={work}", "state", "pull"]

    print("\nCreating protected state backup...")

    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        print("ERROR: Terraform state backup failed.")
        print(result.stderr)
        return 1

    try:
        state = json.loads(result.stdout)
        if not isinstance(state, dict) or "version" not in state:
            raise ValueError("Unrecognized Terraform state format")
    except (json.JSONDecodeError, ValueError):
        print("ERROR: Terraform returned invalid state JSON.")
        return 1

    BACKUPS.mkdir(mode=0o700, parents=True, exist_ok=True)
    BACKUPS.chmod(0o700)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = BACKUPS / f"orbit-{environment}-{timestamp}.tfstate"

    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(state, output)
            output.write("\n")
        path.chmod(0o600)
    except OSError as error:
        print(f"ERROR: Could not securely save state backup: {error}")
        return 1

    print(f"PASS: State backup saved to {path}")
    print("File permissions: 600. Keep this sensitive file out of Git.")
    return 0


def verify_backup(path: Path) -> int:
    if not path.is_file():
        print(f"ERROR: Backup file not found: {path}")
        return 1

    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        required = {"version", "serial", "lineage", "resources"}

        if not isinstance(state, dict) or not required.issubset(state):
            raise ValueError("Required Terraform state fields are missing")

        if not isinstance(state["resources"], list):
            raise ValueError("Terraform state resources must be a list")

    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"FAIL: Backup verification failed: {error}")
        return 1

    print("PASS: Terraform state JSON structure verified.")
    print(f"State serial: {state['serial']}")
    print(f"Resource entries: {len(state['resources'])}")
    print("Do not expose or commit this backup; it may contain secrets.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ORBIT environment and Terraform state operations"
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)

    for name in ("plan", "drift", "backup-state"):
        command = subparsers.add_parser(name)
        command.add_argument(
            "--environment",
            required=True,
            choices=ENVIRONMENTS,
        )

    verify = subparsers.add_parser("verify-backup")
    verify.add_argument("file", type=Path)

    args = parser.parse_args()

    if args.operation == "verify-backup":
        return verify_backup(args.file)

    return remote_operation(args.environment, args.operation)


if __name__ == "__main__":
    sys.exit(main())
