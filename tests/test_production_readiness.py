import json
import tempfile
import unittest

from pathlib import Path

from tools.production_readiness import (
    ci_preflight,
    validate_state_document,
    verify_state_backup,
)


class ProductionReadinessTests(unittest.TestCase):

    def setUp(self):
        self.valid_state = {
            "version": 4,
            "serial": 3,
            "lineage": "orbit-test-lineage",
            "resources": [],
        }

    def test_valid_state_document(self):
        valid, _ = validate_state_document(self.valid_state)
        self.assertTrue(valid)

    def test_state_missing_lineage_is_rejected(self):
        state = dict(self.valid_state)
        del state["lineage"]

        valid, _ = validate_state_document(state)
        self.assertFalse(valid)

    def test_invalid_serial_is_rejected(self):
        state = dict(self.valid_state)
        state["serial"] = "invalid"

        valid, _ = validate_state_document(state)
        self.assertFalse(valid)

    def test_resources_must_be_a_list(self):
        state = dict(self.valid_state)
        state["resources"] = {}

        valid, _ = validate_state_document(state)
        self.assertFalse(valid)

    def test_valid_protected_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.tfstate"
            path.write_text(json.dumps(self.valid_state), encoding="utf-8")
            path.chmod(0o600)

            self.assertTrue(verify_state_backup(path))

    def test_world_readable_backup_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.tfstate"
            path.write_text(json.dumps(self.valid_state), encoding="utf-8")
            path.chmod(0o644)

            self.assertFalse(verify_state_backup(path))

    def test_missing_backup_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.tfstate"
            self.assertFalse(verify_state_backup(path))

    def test_repository_preflight(self):
        self.assertTrue(ci_preflight())


if __name__ == "__main__":
    unittest.main()
