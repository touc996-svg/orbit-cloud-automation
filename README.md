# ORBIT — Cloud Automation & Infrastructure Engineering

ORBIT is a portfolio-grade, Terraform-first AWS infrastructure baseline with Python command-line automation and GitHub Actions validation. The first release focuses on repeatable networking, secure object storage, infrastructure validation, and safe change review.

## What this project provisions

- A dedicated VPC with DNS support.
- Two public subnets across available Availability Zones, with an Internet Gateway route.
- Two private subnets with no direct internet route and no NAT Gateway.
- An S3 Gateway VPC endpoint associated with the private route table.
- A private S3 artifacts bucket with versioning, bucket-owner-enforced object ownership, default encryption, public-access blocking, and a policy denying non-TLS requests.
- Optional VPC Flow Logs to CloudWatch Logs, disabled by default to avoid ongoing ingestion charges.
- A dependency-free repository security scanner for common accidentally committed AWS credentials, private-key markers, and Terraform state/plan artifacts.

The private subnets intentionally have no NAT Gateway. This avoids an always-on NAT cost in the starter environment. Add controlled egress only when a workload requires it and the cost is understood.

## Architecture

```text
AWS account / selected region
└── ORBIT VPC (10.0.0.0/16)
    ├── Public subnet A ──┐
    ├── Public subnet B ──┴── Internet Gateway
    ├── Private subnet A ─┐
    ├── Private subnet B ─┴── S3 Gateway VPC Endpoint
    └── Private S3 artifacts bucket
        ├── Versioning enabled
        ├── SSE-S3 default encryption
        ├── Public access blocked
        └── HTTPS-only bucket policy

Developer workstation / GitHub Actions
└── Python CLI → Terraform fmt / init / validate / plan
```

## Safety and cost controls

1. The bootstrap script does not create AWS resources.
2. `orbit doctor`, `orbit validate`, and `orbit plan` do not apply infrastructure.
3. There is no `terraform apply` command in the Python CLI or CI workflow.
4. VPC Flow Logs are disabled by default; enable them only after reviewing CloudWatch ingestion and retention costs.
4. Terraform creates resources only when an operator deliberately runs `terraform apply` from `infra/` after reviewing a plan.
5. NAT Gateways, EC2 instances, load balancers, and paid third-party services are not included in this baseline.
6. AWS usage may still incur charges after resources are applied (for example, S3 storage and requests, public IPv4 addresses, and data transfer). Review current AWS pricing before deployment.

## Prerequisites

- Python 3.10+
- Terraform 1.6+
- AWS CLI v2
- AWS credentials configured locally for the target account and region
- Git

No third-party Python packages are required for the starter CLI or its unit tests.

## Quick start

```bash
cd ~/Projects/orbit-cloud-automation
python3 tools/orbit.py doctor
python3 -m unittest discover -s tests -v
python3 tools/orbit.py validate
python3 tools/orbit.py plan
python3 tools/orbit.py security-scan
```

`validate` runs formatting, initializes providers without configuring a remote backend, and validates the Terraform configuration. The first `init` downloads provider plugins and may create `.terraform.lock.hcl`.

`plan` produces `infra/orbit.tfplan` and a readable plan output. It does not create or modify AWS infrastructure.

## Terraform variables

Copy `infra/terraform.tfvars.example` to `infra/terraform.tfvars` and edit the project name or region when needed. The example file is safe to commit; the real `terraform.tfvars` is ignored by Git.

## CI

GitHub Actions checks Python unit tests and Terraform formatting, initialization, and validation on pushes and pull requests. It does not authenticate to AWS, generate a deployment plan, or apply infrastructure.

## Repository layout

```text
infra/                 Terraform root module and reusable modules
  modules/network/     VPC, subnets, route tables, S3 gateway endpoint
  modules/storage/     Secure S3 artifacts bucket
 tools/orbit.py        Python automation CLI
tests/                 Standard-library unit tests
 docs/                 Architecture and operational runbook
.github/workflows/     CI validation
```

## Current scope and limitations

This is an infrastructure foundation, not a deployed production environment. The first batch does not create compute workloads, centralized account-wide CloudTrail, an organization-wide landing zone, or a remote Terraform state backend. Those can be added as separate, reviewed changes. No live AWS deployment is claimed by the local tests.
