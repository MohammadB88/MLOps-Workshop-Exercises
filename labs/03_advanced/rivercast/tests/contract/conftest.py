from pathlib import Path

import pytest

LAB_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def lab_root() -> Path:
    return LAB_ROOT


@pytest.fixture()
def configs_dir() -> Path:
    return LAB_ROOT / "configs"
