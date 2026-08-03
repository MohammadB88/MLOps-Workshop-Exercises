"""Print pyproject.toml's exactly-pinned runtime dependencies, one per line.

Used by CI's dependency-scan job to audit exactly the surface that ships in
the four container images (rule: pinned deps only, not the whole ambient
environment `pip-audit --local` would otherwise see).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def main() -> None:
    with _PYPROJECT.open("rb") as f:
        data = tomllib.load(f)
    print("\n".join(data["project"]["dependencies"]))


if __name__ == "__main__":
    main()
