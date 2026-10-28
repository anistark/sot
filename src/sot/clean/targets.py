"""Cleaning targets and the primitives that measure and empty them."""

from __future__ import annotations

import glob
import os
import shutil
import stat
import subprocess
import time
from fnmatch import fnmatch
from pathlib import Path
from typing import Callable, Mapping, NamedTuple, Sequence


class CleanTarget(NamedTuple):
    """Something ``sot clean`` can report and, unless ``review``, remove.

    ``keep`` holds glob patterns of absolute paths left untouched inside
    ``path``. With ``older_than`` only files not modified for that many days
    go, and directories stay. ``action`` replaces deleting the paths, which
    then only measure the target, unless ``measure`` does that too.
    """

    name: str
    path: Path | list[Path]
    description: str
    requires_sudo: bool = False
    keep: tuple[str, ...] = ()
    older_than: int | None = None
    action: Callable[[], list[str]] | None = None
    measure: Callable[[], int] | None = None
    review: bool = False


def target_paths(target: CleanTarget) -> list[Path]:
    return target.path if isinstance(target.path, list) else [target.path]


def keep_exactly(path: Path) -> str:
    """A ``keep`` pattern matching ``path`` and nothing else."""
    return glob.escape(str(path))


def _kept(path: str, keep: Sequence[str]) -> bool:
    return any(fnmatch(path, pattern) for pattern in keep)


def _holds_kept(path: str, keep: Sequence[str]) -> bool:
    prefix = path.rstrip(os.sep) + os.sep
    return any(pattern.startswith(prefix) for pattern in keep)


def _file_size(st: os.stat_result) -> int:
    # Allocated blocks, so sparse disk images count what they really take.
    blocks = getattr(st, "st_blocks", None)
    return st.st_size if blocks is None else min(st.st_size, blocks * 512)


def _cutoff(older_than: int | None) -> float | None:
    return None if older_than is None else time.time() - older_than * 86400


def _counted(st: os.stat_result, cutoff: float | None) -> int:
    if cutoff is not None and (not stat.S_ISREG(st.st_mode) or st.st_mtime > cutoff):
        return 0
    return _file_size(st)


def _usage(path: str, keep: Sequence[str], cutoff: float | None) -> int:
    if keep and _kept(path, keep):
        return 0
    try:
        st = os.lstat(path)
    except OSError:
        return 0
    if not stat.S_ISDIR(st.st_mode):
        return _counted(st, cutoff)

    total = 0
    pending = [path]
    while pending:
        try:
            with os.scandir(pending.pop()) as entries:
                for entry in entries:
                    if keep and _kept(entry.path, keep):
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(entry.path)
                    else:
                        total += _counted(entry.stat(follow_symlinks=False), cutoff)
        except OSError:
            continue
    return total


def disk_usage(
    path: Path, keep: Sequence[str] = (), older_than: int | None = None
) -> int:
    """Bytes under ``path``, leaving out kept paths and, with ``older_than``,
    recent files. Symlinks are never followed."""
    return _usage(str(path), keep, _cutoff(older_than))


def measure_target(target: CleanTarget) -> int:
    if target.measure is not None:
        return target.measure()
    return sum(
        disk_usage(path, target.keep, target.older_than)
        for path in target_paths(target)
    )


def _remove(path: str, keep: Sequence[str], cutoff: float | None) -> list[str]:
    if _kept(path, keep):
        return []
    try:
        st = os.lstat(path)
        if stat.S_ISDIR(st.st_mode) and (cutoff is not None or _holds_kept(path, keep)):
            return _empty(path, keep, cutoff)
        if stat.S_ISDIR(st.st_mode):
            shutil.rmtree(path)
        elif cutoff is None or (stat.S_ISREG(st.st_mode) and st.st_mtime < cutoff):
            os.unlink(path)
    except (PermissionError, OSError) as e:
        return [f"Skipped {os.path.basename(path)}: {e}"]
    return []


def _empty(path: str, keep: Sequence[str], cutoff: float | None) -> list[str]:
    with os.scandir(path) as entries:
        names = [entry.path for entry in entries]
    warnings = []
    for name in names:
        warnings.extend(_remove(name, keep, cutoff))
    return warnings


def empty_path(
    path: Path, keep: Sequence[str] = (), older_than: int | None = None
) -> list[str]:
    """Remove a file, or a directory's contents; returns a warning per failure.

    The directory itself stays, and so do kept paths and, with
    ``older_than``, recent files and every directory.
    """
    if not os.path.lexists(path) or _kept(str(path), keep):
        return []
    try:
        if path.is_dir() and not path.is_symlink():
            return _empty(str(path), keep, _cutoff(older_than))
        return _remove(str(path), keep, _cutoff(older_than))
    except (PermissionError, OSError) as e:
        return [f"Failed to clean {path.name}: {e}"]


def run(
    *commands: Sequence[str],
    timeout: int = 900,
    env: Mapping[str, str] | None = None,
) -> list[str]:
    """Run commands in order; returns a warning per one that failed.

    ``env`` is added to the environment they inherit.
    """
    environ = {**os.environ, **env} if env else None
    warnings = []
    for command in commands:
        try:
            done = subprocess.run(
                list(command),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=environ,
            )
        except (OSError, subprocess.SubprocessError) as e:
            warnings.append(f"{command[0]} failed: {e}")
            continue
        if done.returncode != 0:
            lines = (done.stderr or done.stdout).strip().splitlines()
            reason = lines[-1] if lines else f"exit code {done.returncode}"
            warnings.append(f"{' '.join(command)}: {reason}")
    return warnings


def capture(*command: str, timeout: int = 30, strict: bool = True) -> str | None:
    """A command's output, or None when it can't be run or, if ``strict``,
    exits with an error."""
    if not shutil.which(command[0]):
        return None
    try:
        done = subprocess.run(
            list(command), capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 or not strict else None
