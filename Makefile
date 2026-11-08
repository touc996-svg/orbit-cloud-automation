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
