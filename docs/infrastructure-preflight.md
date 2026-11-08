# ORBIT Batch 3 — Infrastructure Automation

## Five capabilities

1. Terraform formatting, initialization, and validation.
2. Existing repository secret scanning.
3. AWS identity and IAM permission simulation.
4. Infracost monthly cost estimation and budget enforcement.
5. GitHub Actions automated validation.

## Offline CI checks

    python tools/deployment_preflight.py --ci

## Full local preflight

    python tools/deployment_preflight.py

## AWS account restriction

Set the approved 12-digit AWS account:

    export ORBIT_ALLOWED_AWS_ACCOUNT="YOUR_REAL_12_DIGIT_ACCOUNT_ID"

Root credentials are always rejected.

For IAM identities that cannot be automatically resolved, configure:

    export ORBIT_IAM_POLICY_SOURCE_ARN="YOUR_IAM_ROLE_OR_USER_ARN"

## Monthly budget

Install and configure Infracost, then set:

    export ORBIT_MAX_MONTHLY_COST_USD="25"

If a budget is configured but Infracost is unavailable or cannot produce
an estimate, preflight fails.

## Optional Terraform plan

    python tools/deployment_preflight.py --plan

This may contact AWS and read infrastructure state.
It does not apply changes.

## Safety boundary

ORBIT does not run terraform apply.
CI does not receive AWS credentials.
Permission simulation is a policy check, not a guarantee that deployment
will succeed.
