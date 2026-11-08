import unittest

from tools.infra_ops import (
    ENVIRONMENTS,
    backend_settings,
    is_root_arn,
    valid_environment,
)
from unittest.mock import patch


class InfraOperationsTests(unittest.TestCase):

    def test_supported_environments(self):
        for name in ("development", "staging", "production"):
            self.assertTrue(valid_environment(name))

    def test_invalid_environment(self):
        self.assertFalse(valid_environment("sandbox"))

    def test_root_identity_is_blocked(self):
        self.assertTrue(
            is_root_arn("arn:aws:iam::123456789012:root")
        )

    def test_iam_role_is_not_root(self):
        self.assertFalse(
            is_root_arn("arn:aws:iam::123456789012:role/OrbitRole")
        )

    def test_backend_key_is_environment_specific(self):
        with patch.dict(
            "os.environ",
            {
                "ORBIT_TF_STATE_BUCKET": "orbit-state-example-bucket",
                "ORBIT_TF_STATE_REGION": "us-east-1",
                "ORBIT_TF_STATE_LOCK_TABLE": "orbit-terraform-locks",
            },
        ):
            settings = backend_settings("production")

        self.assertIsNotNone(settings)
        self.assertEqual(
            settings["key"],
            "orbit/production/terraform.tfstate",
        )

    def test_backend_rejects_placeholder_bucket(self):
        with patch.dict(
            "os.environ",
            {
                "ORBIT_TF_STATE_BUCKET": "REPLACE_ME",
                "ORBIT_TF_STATE_REGION": "us-east-1",
                "ORBIT_TF_STATE_LOCK_TABLE": "orbit-terraform-locks",
            },
        ):
            self.assertIsNone(backend_settings("development"))

    def test_environment_names_are_unique(self):
        self.assertEqual(len(ENVIRONMENTS), len(set(ENVIRONMENTS)))


if __name__ == "__main__":
    unittest.main()
