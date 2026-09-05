.PHONY: lint type test check

lint:
	ruff check .


type:
	mypy src tests


test:
	pytest --cov=study_os_pir --cov-branch --cov-report=term-missing


check: lint type test
