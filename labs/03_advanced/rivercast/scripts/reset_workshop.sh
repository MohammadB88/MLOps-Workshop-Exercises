#!/usr/bin/env bash
# Reset the RiverCast workshop to a clean, no-champion state (PLAN.md Phase 14).
#
# Run from the lab root (labs/03_advanced/rivercast) between workshop
# cohorts, or whenever a trainee's local run needs a genuine "start over":
# removes every locally-generated run, model, and promoted champion, and
# restores champion state to "none set yet" -- the same state a fresh clone
# starts in. Never touches anything tracked by git (fixtures, configs,
# committed reports like reports/baseline/baseline_report.md, source code).
#
# No Docker, no cluster privileges, no credentials required. Safe to rerun.

set -euo pipefail

if [[ ! -f "pyproject.toml" ]] || ! grep -q 'name = "rivercast"' pyproject.toml; then
    echo "ERROR: run this script from labs/03_advanced/rivercast/" >&2
    exit 1
fi

# Everything below is exactly what .gitignore lists as this lab's
# locally-generated state (local object store, local MLflow tracking store,
# locally-trained model artifacts, executed-notebook build output) -- see
# .gitignore for the authoritative list this mirrors.
TARGETS=(
    "artifacts"
    "models/local"
    "mlflow.db"
    "mlruns"
    "mlartifacts"
    "build"
    ".pytest_cache"
    ".mypy_cache"
    ".ruff_cache"
)

echo "==> Resetting RiverCast workshop state"
for target in "${TARGETS[@]}"; do
    if [[ -e "$target" ]]; then
        echo "    removing $target"
        rm -rf -- "$target"
    fi
done

cat <<'EOF'

Reset complete. No champion is set for any horizon; no runs, predictions,
or datasets remain locally. To rebuild from scratch:

  source .venv/bin/activate   # or: bash scripts/bootstrap_workbench.sh
  rivercast envcheck
  jupyter lab                 # notebooks/00_environment_check.ipynb onward
EOF
