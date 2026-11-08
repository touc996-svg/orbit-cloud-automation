# ORBIT Security and Observability (Batch 2)

## Repository security scan

Run `python3 tools/orbit.py security-scan` before committing. The scanner checks for common AWS access-key IDs, private-key headers, hard-coded AWS secret assignments, and Terraform state/plan/key artifacts. It is a guardrail, not a complete secrets-management solution; review changes and use GitHub secret scanning where available.

## VPC Flow Logs

VPC Flow Logs can be enabled by setting `enable_vpc_flow_logs = true` in the local `infra/terraform.tfvars`. The default is `false`. When enabled, Terraform creates a CloudWatch log group with a configurable retention period and a narrowly scoped IAM role for the VPC Flow Logs service.

CloudWatch Logs ingestion and storage may incur charges. Review current regional pricing and the Terraform plan before enabling. The feature is optional and no AWS resource is created by this batch script.

## Safe workflow

1. Run unit tests and `security-scan`.
2. Run `terraform fmt -check -recursive` and `terraform validate`.
3. Generate a plan only after AWS authentication is configured.
4. Review every planned resource and estimated cost before any manual apply.
