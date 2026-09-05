.PHONY: lint type test docs-sync docs-check check

lint:
	ruff check .


type:
	mypy src tests


test:
	pytest --cov=study_os_pir --cov-branch --cov-report=term-missing --cov-fail-under=100


docs-sync:
	python tools/sync_repository_docs.py --write


docs-check:
	python tools/sync_repository_docs.py --check


check: lint type test docs-check
