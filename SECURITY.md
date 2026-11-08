# Security Policy

- Never commit AWS access keys, secret keys, session tokens, private keys, `.env` files, Terraform state, or saved plan files.
- Prefer short-lived AWS credentials and IAM roles over long-lived access keys.
- Review every Terraform plan before applying it.
- Keep private subnet workloads private; this baseline deliberately adds no NAT Gateway or inbound workload security groups.
- Report suspected vulnerabilities privately to the repository maintainer rather than publishing credentials or exploit details in an issue.
