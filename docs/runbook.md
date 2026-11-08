# ORBIT Local Runbook

## 1. Check local tooling

```bash
python3 tools/orbit.py doctor
```

## 2. Run the Python test suite

```bash
./scripts/test.sh
```

## 3. Validate Terraform

```bash
python3 tools/orbit.py validate
```

## 4. Review a plan

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars
python3 tools/orbit.py plan
```

Review every proposed create, update, and destroy action. The generated plan file can contain sensitive values; keep it local and do not commit or share it publicly.

## 5. Tear down learning resources

If resources were deliberately applied, review the target workspace and state before destroying anything. Run `terraform plan -destroy` first and inspect the result. Do not destroy shared or production infrastructure.
