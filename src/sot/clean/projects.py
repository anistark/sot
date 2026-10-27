"""Build output and dependencies inside project folders.

A directory only counts when the file that makes it rebuildable sits next to
it: ``target`` beside ``Cargo.toml``, ``node_modules`` beside
``package.json``. Folders touched in the last two weeks belong to projects
still being worked on and are only included with ``--force``.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import NamedTuple

from .browsers import SessionFiles

ACTIVE_DAYS = 14

NODE = ("package.json",)
PYTHON = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "uv.lock")
GRADLE = ("build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts")

# Artifact directory -> files, one of which must sit beside it. Empty means
# the name alone is unambiguous.
ARTIFACTS: dict[str, tuple[str, ...]] = {
    "node_modules": NODE,
    ".next": NODE,
    ".nuxt": NODE,
    ".svelte-kit": NODE,
    ".turbo": NODE,
    ".parcel-cache": NODE,
    ".angular": NODE,
    "target": ("Cargo.toml", "pom.xml"),
    ".venv": PYTHON,
    "venv": PYTHON,
    ".tox": ("tox.ini", *PYTHON),
    "__pycache__": (),
    ".pytest_cache": (),
    ".mypy_cache": (),
    ".ruff_cache": (),
    ".gradle": GRADLE,
    "build": GRADLE,
    "Pods": ("Podfile",),
    ".build": ("Package.swift",),
    ".zig-cache": ("build.zig",),
    "zig-cache": ("build.zig",),
    "_build": ("mix.exs",),
    ".stack-work": ("stack.yaml",),
    "dist-newstyle": ("cabal.project",),
}


class Artifact(NamedTuple):
    path: Path
    marker: Path | None


def _newest_mtime(paths: list[Path]) -> float:
    newest = 0.0
    for path in paths:
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue
    return newest


def _in_use(artifact: Artifact, cutoff: float) -> bool:
    try:
        children = list(artifact.path.iterdir())
    except OSError:
        children = []
    markers = [artifact.marker] if artifact.marker else []
    return _newest_mtime([artifact.path, *markers, *children]) > cutoff


def find_artifacts(root: Path) -> list[Artifact]:
    """Artifact directories under ``root``; their insides aren't searched."""
    found = []
    home = Path.home()
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        keep = []
        for name in dirnames:
            if name in ARTIFACTS:
                markers = ARTIFACTS[name]
                marker = next((m for m in markers if m in filenames), None)
                if marker or not markers:
                    found.append(
                        Artifact(here / name, here / marker if marker else None)
                    )
                    continue
            if name.startswith(".") or (
                here == home and name in ("Library", "AppData")
            ):
                continue
            keep.append(name)
        dirnames[:] = keep
    return found


def project_artifacts(root: Path) -> dict[str, SessionFiles]:
    """Artifacts grouped by directory name, split by whether they're in use."""
    cutoff = time.time() - ACTIVE_DAYS * 86400
    groups: dict[str, SessionFiles] = {}
    for artifact in find_artifacts(root):
        group = groups.setdefault(artifact.path.name, SessionFiles([], []))
        if _in_use(artifact, cutoff):
            group.current.append(artifact.path)
        else:
            group.stale.append(artifact.path)
    return groups
