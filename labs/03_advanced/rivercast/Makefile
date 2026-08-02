# RiverCast development targets. Run from the lab root with the project
# environment active (see scripts/bootstrap_workbench.sh).

PYTHON ?= python

.PHONY: install lint format typecheck test notebook-check check clean

install:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check src tests scripts
	$(PYTHON) -m ruff format --check src tests scripts

format:
	$(PYTHON) -m ruff format src tests scripts
	$(PYTHON) -m ruff check --fix src tests scripts

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
	$(PYTHON) -m jupyter nbconvert --to notebook --execute \
		--output-dir build/notebooks --output 01_source_and_data_quality.executed.ipynb \
		notebooks/01_source_and_data_quality.ipynb
	$(PYTHON) -m jupyter nbconvert --to notebook --execute \
		--output-dir build/notebooks --output 02_features_and_leakage.executed.ipynb \
		notebooks/02_features_and_leakage.ipynb
	$(PYTHON) -m jupyter nbconvert --to notebook --execute \
		--output-dir build/notebooks --output 03_baseline_training.executed.ipynb \
		notebooks/03_baseline_training.ipynb
	$(PYTHON) -m jupyter nbconvert --to notebook --execute \
		--output-dir build/notebooks --output 04_mlflow_tracking.executed.ipynb \
		notebooks/04_mlflow_tracking.ipynb

check: lint typecheck test notebook-check

clean:
	rm -rf build .pytest_cache .mypy_cache .ruff_cache src/rivercast.egg-info
