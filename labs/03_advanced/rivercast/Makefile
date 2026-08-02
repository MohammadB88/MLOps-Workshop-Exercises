# RiverCast development targets. Run from the lab root with the project
# environment active (see scripts/bootstrap_workbench.sh).

PYTHON ?= python

.PHONY: install lint format typecheck test notebook-check check clean

install:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m ruff format --check src tests

format:
	$(PYTHON) -m ruff format src tests
	$(PYTHON) -m ruff check --fix src tests

typecheck:
	$(PYTHON) -m mypy

test:
	$(PYTHON) -m pytest

# Fresh-kernel run-all smoke test for maintained notebooks (CLAUDE.md rule 18).
# Executed output goes to build/ so committed notebooks stay output-free.
notebook-check:
	$(PYTHON) -m jupyter nbconvert --to notebook --execute \
		--output-dir build/notebooks --output 00_environment_check.executed.ipynb \
		notebooks/00_environment_check.ipynb

check: lint typecheck test notebook-check

clean:
	rm -rf build .pytest_cache .mypy_cache .ruff_cache src/rivercast.egg-info
