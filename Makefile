.PHONY: test doctor validate plan

test:
	python3 -m unittest discover -s tests -v

doctor:
	python3 tools/orbit.py doctor

validate:
	python3 tools/orbit.py validate

plan:
	python3 tools/orbit.py plan

.PHONY: preflight

preflight:
	python3 tools/deployment_preflight.py --ci


.PHONY: ops-plan-development ops-drift-development ops-backup-development

ops-plan-development:
	python3 tools/infra_ops.py plan --environment development

ops-drift-development:
	python3 tools/infra_ops.py drift --environment development

ops-backup-development:
	python3 tools/infra_ops.py backup-state --environment development

.PHONY: production-readiness
production-readiness:
	python3 tools/production_readiness.py ci
