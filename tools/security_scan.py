#!/usr/bin/env python3
"""Small dependency-free repository scanner for common accidentally committed secrets."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {".git", ".terraform", ".venv", "venv", "__pycache__", ".pytest_cache"}
IGNORED_NAMES = {".env.example", "terraform.tfvars.example"}
FORBIDDEN_SUFFIXES = (".tfstate", ".tfplan", ".pem", ".key")
PATTERNS = {
    "AWS access key ID": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "AWS temporary access key ID": re.compile(r"\bASIA[0-9A-Z]{16}\b"),
    "private key material": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "hard-coded AWS secret assignment": re.compile(
        r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{30,}"
    ),
}


def scan(root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        if path.name in IGNORED_NAMES:
            continue
        if path.name.endswith(FORBIDDEN_SUFFIXES):
            findings.append(f"Terraform state/plan or private-key artifact present: {relative}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append(f"Possible {label} in {relative}")
    return findings


def main() -> int:
    findings = scan()
    if findings:
        print("[FAIL] Potential secret or sensitive artifact detected:")
        for finding in findings:
            print(f" - {finding}")
        return 1
    print("[OK] No common committed-secret patterns or Terraform state/plan artifacts found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
