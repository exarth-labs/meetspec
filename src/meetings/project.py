"""Find the project's .meetings folder."""

from __future__ import annotations

import sys
from pathlib import Path

DIR_NAME = ".meetings"


def find_base(start: Path | None = None) -> Path | None:
    """Return the nearest .meetings folder in the current directory or one of its parents."""
    here = (start or Path.cwd()).resolve()
    for folder in (here, *here.parents):
        if (folder / DIR_NAME).is_dir():
            return folder / DIR_NAME
    return None


def require_base() -> Path:
    base = find_base()
    if base is None:
        sys.exit(f"No {DIR_NAME}/ folder here or in any parent folder. "
                 "Run `meetings install` in the project root first.")
    return base
