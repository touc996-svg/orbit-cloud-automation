import unittest

from tools.deployment_preflight import (
    iam_policy_source_arn,
    is_root_arn,
    valid_account,
)


class DeploymentPreflightTests(unittest.TestCase):

    def test_root_is_detected(self):
        self.assertTrue(
            is_root_arn("arn:aws:iam::123456789012:root")
        )

    def test_iam_user_is_not_root(self):
        self.assertFalse(
            is_root_arn("arn:aws:iam::123456789012:user/orbit")
        )

    def test_empty_arn_is_not_root(self):
        self.assertFalse(is_root_arn(""))

    def test_valid_account(self):
        self.assertTrue(valid_account("123456789012"))

    def test_invalid_account(self):
        self.assertFalse(valid_account("YOUR_12_DIGIT_ACCOUNT_ID"))
        self.assertFalse(valid_account("12345"))

    def test_iam_role_arn_is_preserved(self):
        arn = "arn:aws:iam::123456789012:role/OrbitDeploy"
        self.assertEqual(iam_policy_source_arn(arn), arn)

    def test_assumed_role_is_converted(self):
        arn = (
            "arn:aws:sts::123456789012:"
            "assumed-role/OrbitDeploy/session"
        )
        expected = "arn:aws:iam::123456789012:role/OrbitDeploy"
        self.assertEqual(iam_policy_source_arn(arn), expected)

    def test_unsupported_arn_returns_none(self):
        self.assertIsNone(iam_policy_source_arn("invalid-arn"))


if __name__ == "__main__":
    unittest.main()
