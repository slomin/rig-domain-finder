from __future__ import annotations

import os
from pathlib import Path


def _find_project_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Could not locate project root (missing pyproject.toml in parent paths).")


def require_uv_project_env() -> None:
    project_root = _find_project_root(Path(__file__).resolve())
    required_venv = (project_root / ".venv").resolve()
    uv_bin = os.environ.get("UV")
    active_venv = os.environ.get("VIRTUAL_ENV")

    if not uv_bin:
        raise RuntimeError(
            "This RIG must be run with uv. Use: `uv sync` then `uv run <command>`."
        )
    if not active_venv:
        raise RuntimeError(
            "No active virtual environment detected. Use: `uv sync` then `uv run <command>`."
        )

    resolved_active_venv = Path(active_venv).resolve()
    if resolved_active_venv != required_venv:
        raise RuntimeError(
            "This RIG requires the project environment at "
            f"`{required_venv}`. Current: `{resolved_active_venv}`. "
            "Run commands via `uv run ...` from the project root."
        )
