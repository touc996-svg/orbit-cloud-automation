from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "security_scan.py"
SPEC = importlib.util.spec_from_file_location("orbit_security_scan", MODULE_PATH)
assert SPEC and SPEC.loader
scanner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scanner)


class SecurityScanTests(unittest.TestCase):
    def test_detects_aws_access_key_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample_key = "AKIA" + "1234567890ABCDEF"
            (root / "sample.py").write_text(f'key = "{sample_key}"', encoding="utf-8")
            self.assertTrue(any("AWS access key ID" in item for item in scanner.scan(root)))

    def test_detects_temporary_aws_access_key_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample_key = "ASIA" + "1234567890ABCDEF"
            (root / "sample.py").write_text(
                f'key = "{sample_key}"', encoding="utf-8"
            )
            self.assertTrue(
                any("AWS temporary access key ID" in item
                    for item in scanner.scan(root))
            )

    def test_ignores_example_environment_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env.example").write_text("AWS_SECRET_ACCESS_KEY=replace-me", encoding="utf-8")
            self.assertEqual(scanner.scan(root), [])

    def test_detects_terraform_state_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "terraform.tfstate").write_text("{}", encoding="utf-8")
            self.assertTrue(any("Terraform state/plan" in item for item in scanner.scan(root)))

    def test_clean_repository_returns_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("print('safe')", encoding="utf-8")
            self.assertEqual(scanner.scan(root), [])


if __name__ == "__main__":
    unittest.main()
