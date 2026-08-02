"""Best-effort Git commit lookup for artifact lineage (rule 10)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def current_commit(cwd: Path | None = None) -> str | None:
    """Full HEAD commit hash, or None outside a repository / without git."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
