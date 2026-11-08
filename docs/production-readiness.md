# ORBIT Batch 5 — Production Readiness and Security Hardening

## Scope

This is a separate Terraform stack under `infra/production-readiness`.
It does not replace or modify the existing network, storage, observability,
state-backend or infrastructure operations stacks.

## 1. GitHub Actions OIDC

The stack creates a read-only Terraform plan role for each GitHub Environment:

- development
- staging
- production

Each role trust policy is restricted to:
- The configured GitHub repository
- The exact GitHub Environment subject
- The `sts.amazonaws.com` OIDC audience

The stack expects an existing AWS IAM OIDC provider for
`token.actions.githubusercontent.com`. It does not create a duplicate
provider automatically.

The roles can discover infrastructure and access the configured Terraform
state and lock table. They do not receive EC2, IAM, S3 or other infrastructure
provisioning permissions.

After provisioning by an authorized operator, configure each GitHub
Environment variable:

`ORBIT_AWS_ROLE_ARN`

Use the matching role ARN from the Terraform outputs.

## 2. Incident monitoring

The incident SNS topic receives alerts for:

- Root-account management API activity recorded by CloudTrail
- Failed AWS console logins
- AWS Health events
- AWS Budgets notifications

The email subscription must be confirmed by the recipient.

These alerts depend on CloudTrail management events and AWS service event
delivery being enabled and available in the account.

## 3. Cost monitoring

The stack creates:

- A monthly AWS Budget
- Actual cost notifications at 80% and 100%
- A forecasted cost notification at 100%
- A CloudWatch `AWS/Billing` EstimatedCharges alarm

The CloudWatch billing alarm is created in `us-east-1` because AWS billing
metrics are published there. Enable billing alerts in AWS Billing
preferences for the account.

Cost notifications are alerts, not hard spending caps. They do not
automatically stop AWS resources.

## 4. Disaster recovery and backup

AWS Backup creates a vault and a plan with:
- Daily backups, 35-day default retention
- Weekly backups, 90-day default retention

Resources must carry this tag to be selected:

`ORBITBackup = daily`

The backup selection is tag-based. Confirm that the resources you intend to
protect support AWS Backup and have the required tags.

For stronger encryption controls, configure a customer-managed KMS key
using `backup_kms_key_arn`.

Vault lock is not enabled in this stack. Configure immutable retention
separately after security and recovery requirements are reviewed.

## 5. Incident response runbooks

### Root account activity
1. Verify the CloudTrail event and source IP.
2. Identify the API action and affected resource.
3. Confirm whether the activity was authorized.
4. Escalate unexpected root activity immediately.
5. Review credentials, root MFA and account access.
6. Preserve logs and document the incident.

### Failed console login
1. Review CloudTrail sign-in events.
2. Correlate IP address, time and principal.
3. Check for repeated failures or suspicious geographic changes.
4. Follow the account's access-response policy.
5. Preserve evidence before changing credentials.

### AWS Health event
1. Review the affected service and region.
2. Identify impacted ORBIT resources.
3. Follow the AWS Health remediation guidance.
4. Record recovery actions and customer impact.

### Billing alert
1. Review AWS Cost Explorer by service and region.
2. Compare usage with the previous period.
3. Identify unexpected or idle resources.
4. Confirm the change is legitimate before removing resources.

### Backup recovery
1. Identify the affected resource and recovery point.
2. Confirm the backup is recent and belongs to the correct environment.
3. Restore to an isolated target where possible.
4. Validate data integrity and application health.
5. Obtain approval before replacing production resources.
6. Document recovery time and recovery point achieved.

## 6. State backup verification

Verify a protected Terraform state backup locally:

    python tools/production_readiness.py verify-backup backups/NAME.tfstate

The verifier checks required state structure and file permissions.
State files may contain secrets. Never commit backups or print their contents.

## 7. Configuration

Copy the example file:

    cp infra/production-readiness/terraform.tfvars.example \
       infra/production-readiness/terraform.tfvars

Replace all placeholders with verified values. The real values file is
excluded from Git.

Prerequisites include:
- An existing GitHub Actions OIDC provider in AWS
- An existing remote state bucket and DynamoDB lock table
- A verified AWS account and authorized non-root operator
- Confirmed incident alert email
- GitHub Environments and required reviewers

## Safety boundary

The Batch 5 GitHub Actions workflow performs tests, Terraform initialization
without a backend, formatting and validation only.

It does not receive AWS credentials, create resources, run Terraform plan,
run Terraform apply, or destroy infrastructure.

The Terraform configuration describes resources but does not provision them
unless an authorized operator separately executes an approved deployment.
