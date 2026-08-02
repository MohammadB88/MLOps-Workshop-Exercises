#!/usr/bin/env bash
# Deterministic bootstrap for the RiverCast lab environment.
#
# Run once from the lab root (labs/03_advanced/rivercast) in a JupyterLab
# terminal after cloning the repository — or on any Linux/macOS machine.
# Creates a project-local virtual environment, installs the pinned package
# in editable mode, and registers a Jupyter kernel. Idempotent; safe to rerun.
#
# No Docker, no cluster privileges, no credentials required.

set -euo pipefail

if [[ ! -f "pyproject.toml" ]] || ! grep -q 'name = "rivercast"' pyproject.toml; then
    echo "ERROR: run this script from labs/03_advanced/rivercast/" >&2
    exit 1
fi

PYTHON="${PYTHON:-python3}"
VENV_DIR=".venv"

echo "==> Using $($PYTHON --version 2>&1) at $(command -v "$PYTHON")"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "==> Creating virtual environment in $VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Installing rivercast (editable) with dev tools"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -e ".[dev]"

echo "==> Registering Jupyter kernel 'rivercast'"
python -m ipykernel install --user --name rivercast --display-name "Python (rivercast)"

echo "==> Validating configuration"
rivercast config validate --config configs/local.yaml

echo "==> Running environment checks"
rivercast envcheck || true   # WARNs are expected before cluster services exist

cat <<'EOF'

Bootstrap complete. Next steps:
  source .venv/bin/activate
  make lint typecheck test          # quality gates
  jupyter lab                       # open notebooks/00_environment_check.ipynb
                                    # with the "Python (rivercast)" kernel
EOF
