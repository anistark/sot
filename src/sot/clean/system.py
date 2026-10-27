"""Operating system leftovers: temp folders, crash dumps, journals, clones.

Simple ones are path templates in ``SYSTEM``; the ones that have to ask a
tool what is stale (``lsof``, ``simctl``, ``snap``) are functions.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Mapping, NamedTuple

from .agents import expand_paths, resolve_roots
from .browsers import SessionFiles
from .targets import CleanTarget, capture, run


class SystemSpec(NamedTuple):
    name: str
    description: str
    paths: tuple[str, ...]
    requires_sudo: bool = False
    older_than: int | None = None
    privacy: bool = False


SYSTEM: tuple[SystemSpec, ...] = (
    SystemSpec(
        "Mail Downloads",
        "Attachments Mail opened",
        (
            "{home}/Library/Containers/com.apple.mail/Data/Library/Mail Downloads",
            "{home}/Library/Mail Downloads",
        ),
    ),
    SystemSpec(
        "Messages Previews",
        "Link and attachment previews",
        ("{home}/Library/Messages/Caches/Previews",),
    ),
    SystemSpec(
        "Diagnostic Reports",
        "System crash reports over 30 days old",
        ("/Library/Logs/DiagnosticReports",),
        requires_sudo=True,
        older_than=30,
    ),
    SystemSpec("Trash", "Trash bin contents", ("{xdg_data}/Trash",)),
    SystemSpec(
        "Core Dumps",
        "Crashed process memory dumps",
        ("/var/lib/systemd/coredump", "/var/crash"),
        requires_sudo=True,
    ),
    SystemSpec(
        "Crash Dumps",
        "App crash dumps and error reports",
        ("{localappdata}/CrashDumps", "{localappdata}/Microsoft/Windows/WER"),
    ),
    SystemSpec(
        "System Crash Dumps",
        "Windows crash dumps and error reports",
        (
            "{windir}/Minidump",
            "{windir}/MEMORY.DMP",
            "{programdata}/Microsoft/Windows/WER",
        ),
        requires_sudo=True,
    ),
    SystemSpec(
        "Shader Caches",
        "DirectX and GPU driver shader caches",
        (
            "{localappdata}/D3DSCache",
            "{localappdata}/NVIDIA/DXCache",
            "{localappdata}/NVIDIA/GLCache",
            "{localappdata}/AMD/DxCache",
            "{localappdata}/AMD/GLCache",
        ),
    ),
    SystemSpec(
        "Thumbnail Cache",
        "Explorer thumbnails",
        ("{localappdata}/Microsoft/Windows/Explorer/thumbcache_*.db",),
    ),
    SystemSpec(
        "Update Downloads",
        "Downloaded Windows updates",
        (
            "{windir}/SoftwareDistribution/Download",
            "{windir}/ServiceProfiles/NetworkService/AppData/Local/Microsoft/"
            "Windows/DeliveryOptimization/Cache",
        ),
        requires_sudo=True,
    ),
    SystemSpec(
        "Saved App State",
        "Window state over 30 days old",
        ("{home}/Library/Saved Application State",),
        older_than=30,
        privacy=True,
    ),
    SystemSpec(
        "Recent Items",
        "Recently opened files lists",
        (
            "{mac_app_support}/com.apple.sharedfilelist/*Recent*",
            "{xdg_data}/recently-used.xbel",
            "{appdata}/Microsoft/Windows/Recent",
        ),
        privacy=True,
    ),
)


def system_targets(
    privacy: bool = False, roots: Mapping[str, Path] | None = None
) -> list[CleanTarget]:
    resolved = resolve_roots() if roots is None else roots
    targets = []
    for spec in SYSTEM:
        if spec.privacy and not privacy:
            continue
        found = [p for p in expand_paths(spec.paths, resolved) if p.exists()]
        if found:
            targets.append(
                CleanTarget(
                    spec.name,
                    found,
                    spec.description,
                    requires_sudo=spec.requires_sudo,
                    older_than=spec.older_than,
                )
            )
    return targets


def darwin_user_dir() -> Path | None:
    """The per-user ``/var/folders`` directory holding ``T``, ``C`` and ``X``."""
    base = Path(os.environ.get("TMPDIR") or tempfile.gettempdir()).parent
    return base if (base / "C").is_dir() and (base / "T").is_dir() else None


def darwin_targets(base: Path) -> list[CleanTarget]:
    caches = [
        *base.glob("C/com.apple.metal"),
        *base.glob("C/clang"),
        *base.glob("C/*.helper"),
        *base.glob("C/*.helper.*"),
    ]
    targets = [
        CleanTarget(
            "User Temp",
            base / "T",
            "Temp files over 3 days old",
            older_than=3,
        )
    ]
    if caches:
        targets.append(
            CleanTarget(
                "GPU & Helper Caches",
                caches,
                "Metal shaders, clang modules, app helpers",
            )
        )
    return targets


def code_sign_clones(base: Path) -> SessionFiles:
    """Copies Chromium browsers make of themselves at launch.

    A clone that no process has open was left by a browser that crashed or was
    killed before removing it. Without ``lsof`` to tell, all count as current.
    """
    clones = sorted(base.glob("X/*.code_sign_clone/code_sign_clone.*"))
    if not clones:
        return SessionFiles([], [])
    listing = capture("lsof", "-nP", "-Fn", strict=False)
    if listing is None:
        return SessionFiles([], clones)
    open_names = set(re.findall(r"code_sign_clone\.[A-Za-z0-9]+", listing))
    stale = [c for c in clones if c.name not in open_names]
    current = [c for c in clones if c.name in open_names]
    return SessionFiles(stale, current)


def device_support(roots: Mapping[str, Path] | None = None) -> SessionFiles:
    """Xcode's per-OS-version device symbols; the newest two of each are kept."""
    stale: list[Path] = []
    current: list[Path] = []
    pattern = ("{home}/Library/Developer/Xcode/*DeviceSupport",)
    for platform in expand_paths(pattern, roots):
        try:
            versions = sorted(
                (p for p in platform.iterdir() if p.is_dir()),
                key=lambda p: p.stat().st_mtime,
            )
        except OSError:
            continue
        stale.extend(versions[:-2])
        current.extend(versions[-2:])
    return SessionFiles(stale, current)


def unavailable_simulators(roots: Mapping[str, Path] | None = None) -> list[Path]:
    """Simulators whose runtime is no longer installed."""
    devices = expand_paths(("{home}/Library/Developer/CoreSimulator/Devices",), roots)
    if not devices or not devices[0].is_dir():
        return []
    listing = capture("xcrun", "simctl", "list", "devices", "unavailable", "-j")
    try:
        runtimes = json.loads(listing or "{}").get("devices", {})
    except ValueError:
        return []
    return [
        devices[0] / device["udid"]
        for runtime in runtimes.values()
        for device in runtime
        if not device.get("isAvailable", True)
        and (devices[0] / device["udid"]).exists()
    ]


def simulator_target(roots: Mapping[str, Path] | None = None) -> list[CleanTarget]:
    paths = unavailable_simulators(roots)
    if not paths:
        return []
    return [
        CleanTarget(
            "Old Simulators",
            paths,
            "Simulators for removed iOS runtimes",
            action=lambda: run(("xcrun", "simctl", "delete", "unavailable")),
        )
    ]


def journal_target() -> list[CleanTarget]:
    journal = Path("/var/log/journal")
    if not (shutil.which("journalctl") and journal.is_dir()):
        return []
    return [
        CleanTarget(
            "Journal Logs",
            journal,
            "systemd journal over 7 days old",
            requires_sudo=True,
            older_than=7,
            action=lambda: run(("journalctl", "--vacuum-time=7d")),
        )
    ]


def snap_target() -> list[CleanTarget]:
    """Disabled snap revisions, kept around after every refresh."""
    listing = capture("snap", "list", "--all")
    if not listing:
        return []
    old = []
    for line in listing.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 6 and "disabled" in fields[-1]:
            old.append((fields[0], fields[2]))
    files = [Path(f"/var/lib/snapd/snaps/{name}_{rev}.snap") for name, rev in old]
    if not old:
        return []
    commands = [("snap", "remove", name, f"--revision={rev}") for name, rev in old]
    return [
        CleanTarget(
            "Old Snaps",
            [f for f in files if f.exists()],
            "Disabled snap revisions",
            requires_sudo=True,
            action=lambda: run(*commands),
        )
    ]
