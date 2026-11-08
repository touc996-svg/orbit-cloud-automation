# ORBIT Batch 4 — Advanced Infrastructure Operations

## 1. Separate environments

Environment configurations are maintained independently:

- `infra/environments/development.tfvars`
- `infra/environments/staging.tfvars`
- `infra/environments/production.tfvars`

They are derived from the existing `terraform.tfvars.example`.
The `environment` value is different in each file.

Review the values before using them. This project does not automatically
create three isolated AWS accounts or VPCs. Account and network isolation
must be established through the AWS account and IAM design.

## 2. Remote Terraform state

The separate `infra/state-backend` Terraform root describes:

- S3 state storage
- S3 versioning
- Server-side encryption
- Public access blocking
- Bucket ownership controls
- HTTPS-only bucket policy
- DynamoDB state locking
- Prevent-destroy safeguards

It is a bootstrap configuration only. It has not been applied.

The main infrastructure configuration is not switched to remote state
automatically. `tools/infra_ops.py` creates a temporary working copy and
adds the S3 backend there, without modifying the tracked root configuration.

Configure these environment variables only after the backend exists:

- `ORBIT_TF_STATE_BUCKET`
- `ORBIT_TF_STATE_REGION`
- `ORBIT_TF_STATE_LOCK_TABLE`
- `ORBIT_ALLOWED_AWS_ACCOUNT`

The tool uses separate state keys for each environment.

## 3. Plan and drift operations

After the remote backend has been created and configured:

    python tools/infra_ops.py plan --environment development

    python tools/infra_ops.py plan --environment staging

    python tools/infra_ops.py plan --environment production

Drift check:

    python tools/infra_ops.py drift --environment development

A drift check requires an initialized remote state containing managed
resources. It exits with code 2 when drift is detected. This is intentional
so CI can alert on differences.

A drift check uses Terraform refresh-only planning. It does not reconcile
or apply changes.

## 4. State backup and verification

Create a protected state backup:

    python tools/infra_ops.py backup-state --environment development

Verify a backup:

    python tools/infra_ops.py verify-backup backups/NAME.tfstate

Backups are written with restrictive file permissions and are excluded
from Git. Terraform state may contain passwords, tokens, and other secrets.
Store a separate protected copy outside the workstation.

## 5. Recovery procedure

1. Stop infrastructure operations for the affected environment.
2. Identify the correct state backup and verify its JSON structure.
3. Pull and preserve a second copy of the current remote state.
4. Confirm the backup's environment, lineage and serial with the team.
5. Review Terraform's state recovery guidance and use `terraform state push`
   only with an authorized operator and a reviewed recovery plan.
6. Run a refresh-only plan and inspect the result before considering any
   infrastructure change.

State recovery is deliberately not automated by this project.

## 6. GitHub approval gates and OIDC

Create GitHub Environments named:

- `development`
- `staging`
- `production`

In repository Settings > Environments, configure required reviewers
for staging and production. Consider restricting deployment branches
to `main`.

Configure these environment-level variables:

- `ORBIT_AWS_ROLE_ARN`
- `ORBIT_AWS_REGION`
- `ORBIT_ALLOWED_AWS_ACCOUNT`
- `ORBIT_TF_STATE_BUCKET`
- `ORBIT_TF_STATE_REGION`
- `ORBIT_TF_STATE_LOCK_TABLE`

The AWS role must trust the GitHub Actions OIDC provider and restrict
the subject to this repository and the relevant GitHub environment.
Grant only the read and state access required for planning and drift
checks. Do not use root credentials or long-lived access keys.

The operations workflow runs plan or drift operations only.
It contains no apply or destroy operation.

## 7. Automation

The GitHub operations workflow supports manual environment selection.
It also schedules a weekly development drift check once the required
AWS role and backend settings are configured.

The schedule does not automatically deploy or repair infrastructure.
