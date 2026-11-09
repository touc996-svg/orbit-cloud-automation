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

---

## Engineering Portfolio

This repository is part of a four-project engineering portfolio spanning data engineering, machine learning operations, cloud infrastructure automation, and applied AI engineering.

| Project | Engineering Focus | Technology |
|---|---|---|
| [ATLAS](https://github.com/touc996-svg/atlas) | Event-driven data engineering and lakehouse analytics | Python, Kafka, PostgreSQL, Spark, Parquet, dbt, FastAPI |
| [APEX MLOps](https://github.com/touc996-svg/apex-mlops) | Reproducible ML lifecycle, model governance and monitoring | Python, scikit-learn, MLflow, FastAPI, Docker |
| [ORBIT](https://github.com/touc996-svg/orbit-cloud-automation) | AWS infrastructure automation and security validation | Terraform, AWS, Python, GitHub Actions |
| [NEXUS AI](https://github.com/touc996-svg/nexus-ai) | Multi-agent AI, RAG architecture and intelligent orchestration | FastAPI, Qwen3, Ollama, Qdrant, Nomic Embeddings, SQL |

### Portfolio Verification Highlights

- **ATLAS:** Verified local end-to-end pipeline execution, 3/3 dbt models and 9/9 dbt data-quality tests.
- **APEX MLOps 0.3.0:** Model registry, artifact integrity, controlled retraining, protected inference API and drift monitoring.
- **ORBIT:** Terraform validation, security scanning, infrastructure preflight and CI. This is an infrastructure baseline; no live AWS deployment is claimed.
- **NEXUS AI 0.7.0:** 70 passing local tests, 12/12 reported live integration checks, successful Qwen3 inference, 768-dimensional Nomic embeddings, and successful GitHub CI for commit `5c6a949`. RAG endpoints passed HTTP smoke tests; retrieval quality remains a separate validation item.

Each project has its own architecture, setup instructions, tests and documented limitations. The repositories can be reviewed and run independently.
