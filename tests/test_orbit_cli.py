from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "orbit.py"
SPEC = importlib.util.spec_from_file_location("orbit_cli", MODULE_PATH)
assert SPEC and SPEC.loader
orbit = importlib.util.module_from_spec(SPEC)
sys.modules["orbit_cli"] = orbit
SPEC.loader.exec_module(orbit)


class OrbitCliTests(unittest.TestCase):
    def test_parser_accepts_only_safe_commands(self) -> None:
        self.assertEqual(orbit.build_parser().parse_args(["doctor"]).command, "doctor")
        self.assertEqual(orbit.build_parser().parse_args(["validate"]).command, "validate")
        self.assertEqual(orbit.build_parser().parse_args(["plan"]).command, "plan")

    def test_apply_is_not_an_available_command(self) -> None:
        with self.assertRaises(SystemExit):
            orbit.build_parser().parse_args(["apply"])

    @patch("orbit_cli.subprocess.run")
    def test_run_command_returns_process_code(self, mocked_run) -> None:
        mocked_run.return_value.returncode = 17
        result = orbit.run_command(["terraform", "validate"])
        self.assertEqual(result, 17)
        mocked_run.assert_called_once()

    @patch("orbit_cli.subprocess.run", side_effect=FileNotFoundError)
    def test_missing_executable_returns_127(self, mocked_run) -> None:
        self.assertEqual(orbit.run_command(["missing-tool"]), 127)


if __name__ == "__main__":
    unittest.main()
