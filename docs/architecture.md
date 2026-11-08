# ORBIT Architecture Notes

## Network boundaries

The VPC is split across two Availability Zones. Public subnets have a default route to an Internet Gateway. Private subnets have no default internet route. An S3 Gateway VPC endpoint is associated with the private route table so private workloads can reach S3 without a NAT Gateway.

## Storage controls

The artifacts bucket has versioning, default SSE-S3 encryption, public access blocks, bucket-owner-enforced ownership, and a bucket policy that denies requests without TLS. The policy does not grant access; workload IAM permissions must be designed separately.

## Automation flow

1. `doctor` checks local tools and makes a read-only AWS STS identity request when the AWS CLI is installed.
2. `validate` formats, initializes providers with backend configuration disabled, and validates HCL.
3. `plan` displays proposed infrastructure changes and saves a local plan file.
4. Applying infrastructure is intentionally an explicit operator action outside the automation CLI and CI workflow.

## Deliberate trade-offs

- No NAT Gateway: reduces idle recurring cost, but private workloads do not have general internet egress.
- No compute: keeps the first batch focused on infrastructure fundamentals.
- Local Terraform state: appropriate only for an individual learning environment; move to a protected remote backend with locking before team use.
- No IAM deploy role yet: identity federation is a separate batch because an existing AWS account may already have an IAM OIDC provider.
