#!/usr/bin/env python3
"""ORBIT Batch 3: Infrastructure deployment safety checks."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"

REQUIRED_ACTIONS = [
    "ec2:DescribeVpcs",
    "ec2:DescribeSubnets",
    "ec2:DescribeRouteTables",
    "ec2:DescribeSecurityGroups",
    "ec2:DescribeAvailabilityZones",
    "ec2:CreateVpc",
    "ec2:CreateSubnet",
    "ec2:CreateFlowLogs",
    "logs:DescribeLogGroups",
    "logs:CreateLogGroup",
    "iam:GetRole",
    "iam:CreateRole",
    "iam:PutRolePolicy",
    "iam:PassRole",
]


def run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    print(f"\n$ {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.stdout:
            print(result.stdout)
        return result
    except FileNotFoundError:
        print(f"ERROR: Required executable not found: {command[0]}")
        return subprocess.CompletedProcess(command, 127, "")


def is_root_arn(arn: str) -> bool:
    return bool(re.search(r":root$", arn or ""))


def valid_account(account: str) -> bool:
    return bool(re.fullmatch(r"\d{12}", account or ""))


def iam_policy_source_arn(arn: str) -> str | None:
    """Resolve IAM policy source ARN from an IAM or assumed-role ARN."""
    if ":iam::" in arn:
        return arn

    match = re.match(
        r"arn:(aws|aws-us-gov|aws-cn):sts::(\d+):assumed-role/(.+)/[^/]+$",
        arn,
    )
    if match:
        partition, account, role = match.groups()
        return f"arn:{partition}:iam::{account}:role/{role}"

    return None


def terraform_checks() -> bool:
    if not (INFRA / "main.tf").is_file():
        print("FAIL: infra/main.tf is missing.")
        return False

    commands = [
        ["terraform", "-chdir=infra", "fmt", "-check", "-recursive"],
        [
            "terraform", "-chdir=infra", "init",
            "-backend=false", "-input=false", "-no-color",
        ],
        ["terraform", "-chdir=infra", "validate", "-no-color"],
    ]

    for command in commands:
        if run(command).returncode != 0:
            print("FAIL: Terraform validation.")
            return False

    print("PASS: Terraform format, initialization, and validation.")
    return True


def repository_security_check() -> bool:
    scanner = ROOT / "tools" / "security_scan.py"

    if not scanner.is_file():
        print("FAIL: Existing ORBIT security scanner is missing.")
        return False

    result = run([sys.executable, str(scanner)])

    if result.returncode == 0:
        print("PASS: Repository security scanner.")
        return True

    print("FAIL: Repository security scanner.")
    return False


def aws_identity_check() -> bool:
    if not shutil.which("aws"):
        print("FAIL: AWS CLI is not installed.")
        return False

    result = run([
        "aws", "sts", "get-caller-identity", "--output", "json"
    ])

    if result.returncode != 0:
        print("FAIL: Unable to verify AWS identity.")
        return False

    try:
        identity = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        print("FAIL: Invalid AWS identity response.")
        return False

    arn = identity.get("Arn", "")
    account = identity.get("Account", "")

    print(f"AWS account: {account}")
    print(f"AWS identity: {arn}")

    if is_root_arn(arn):
        print("BLOCKED: AWS root credentials are prohibited.")
        return False

    if not valid_account(account):
        print("FAIL: AWS returned an invalid account ID.")
        return False

    expected = os.getenv("ORBIT_ALLOWED_AWS_ACCOUNT")

    if expected:
        if not valid_account(expected):
            print("FAIL: ORBIT_ALLOWED_AWS_ACCOUNT must contain 12 digits.")
            return False

        if account != expected:
            print("BLOCKED: AWS account does not match the approved account.")
            return False

    source_arn = os.getenv("ORBIT_IAM_POLICY_SOURCE_ARN")
    if not source_arn:
        source_arn = iam_policy_source_arn(arn)

    if not source_arn:
        print(
            "FAIL: Cannot resolve IAM policy source ARN. "
            "Set ORBIT_IAM_POLICY_SOURCE_ARN to the actual IAM role or user ARN."
        )
        return False

    simulation = run([
        "aws", "iam", "simulate-principal-policy",
        "--policy-source-arn", source_arn,
        "--action-names", *REQUIRED_ACTIONS,
        "--output", "json",
    ])

    if simulation.returncode != 0:
        print("FAIL: IAM permission simulation failed.")
        return False

    try:
        evaluations = json.loads(simulation.stdout).get(
            "EvaluationResults", []
        )
    except (json.JSONDecodeError, TypeError):
        print("FAIL: Invalid IAM simulation response.")
        return False

    if not evaluations:
        print("FAIL: IAM simulation returned no permission results.")
        return False

    denied = [
        item.get("EvalActionName", "unknown")
        for item in evaluations
        if item.get("EvalDecision") != "allowed"
    ]

    if denied:
        print("BLOCKED: Required permissions are missing or denied:")
        for action in denied:
            print(f"  - {action}")
        return False

    print("PASS: AWS identity and IAM permission simulation.")
    return True


def cost_check() -> bool:
    budget = os.getenv("ORBIT_MAX_MONTHLY_COST_USD")
    infracost = shutil.which("infracost")

    if budget:
        try:
            maximum = float(budget)
            if maximum <= 0:
                raise ValueError
        except ValueError:
            print("FAIL: Monthly cost limit must be a positive number.")
            return False
    else:
        maximum = None

    if not infracost:
        if maximum is not None:
            print("FAIL: Infracost is required when a budget limit is configured.")
            return False

        print("SKIP: Infracost not installed; cost estimation unavailable.")
        return True

    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "cost-estimate.json"

        result = run([
            infracost, "breakdown",
            "--path", str(INFRA),
            "--format", "json",
            "--out-file", str(output),
        ])

        if result.returncode != 0:
            print("FAIL: Infracost could not generate an estimate.")
            return False

        try:
            data = json.loads(output.read_text(encoding="utf-8"))
            estimated = float(data["totalMonthlyCost"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            print("FAIL: Unable to read monthly cost estimate.")
            return False

    print(f"Estimated monthly infrastructure cost: ${estimated:.2f}")

    if maximum is not None:
        print(f"Configured monthly budget: ${maximum:.2f}")

        if estimated > maximum:
            print("BLOCKED: Estimated cost exceeds the monthly budget.")
            return False

    print("PASS: Cost safeguard.")
    return True


def terraform_plan() -> bool:
    result = run([
        "terraform", "-chdir=infra", "plan",
        "-input=false", "-no-color", "-lock=false",
        "-out=/tmp/orbit-batch3.tfplan",
    ])

    if result.returncode != 0:
        print("FAIL: Terraform plan.")
        return False

    print("PASS: Terraform plan generated. Nothing was applied.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ORBIT infrastructure deployment preflight"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Run offline CI checks without AWS credentials.",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Generate a Terraform plan after successful preflight.",
    )
    args = parser.parse_args()

    if args.ci and args.plan:
        parser.error("--plan cannot be combined with --ci")

    print("\n" + "=" * 55)
    print("ORBIT BATCH 3 — DEPLOYMENT PREFLIGHT")
    print("=" * 55)

    checks = [
        ("Terraform validation", terraform_checks()),
        ("Repository security", repository_security_check()),
    ]

    if args.ci:
        print("\nCI MODE: AWS and live cost checks are skipped.")
    else:
        checks.append(("AWS identity and permissions", aws_identity_check()))
        checks.append(("Cost estimation and budget", cost_check()))

    passed = all(status for _, status in checks)

    if args.plan:
        if passed:
            checks.append(("Terraform plan", terraform_plan()))
        else:
            print("\nBLOCKED: Plan skipped because a preflight check failed.")

    print("\n" + "=" * 55)
    print("ORBIT PREFLIGHT SUMMARY")
    print("=" * 55)

    for name, status in checks:
        print(f"{'PASS' if status else 'FAIL'}: {name}")

    success = all(status for _, status in checks)

    print("\nRESULT:", "READY FOR REVIEW" if success else "BLOCKED")
    print("No terraform apply or AWS resource creation was performed.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
