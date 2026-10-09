"""Clean command implementation for system cleanup."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import NamedTuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from .._theme import theme
from .agents import CODING_AGENTS, agent_paths, resolve_roots


class CleanTarget(NamedTuple):
    """Represents a cleaning target with metadata."""

    name: str
    path: Path | list[Path]
    description: str
    requires_sudo: bool = False
    recursive: bool = True


def _is_elevated() -> bool:
    """Whether this process can touch targets that need admin rights.

    ``geteuid`` is POSIX only, so Windows is asked through the shell API
    instead. Anything that fails to answer counts as unprivileged -- the
    targets are then skipped rather than attempted and half completed.
    """
    if hasattr(os, "geteuid"):
        return os.geteuid() == 0

    try:
        import ctypes

        return bool(getattr(ctypes, "windll").shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _get_size(path: Path) -> int:
    """Calculate total size of a path (file or directory)."""
    try:
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            total = 0
            for entry in path.rglob("*"):
                try:
                    if entry.is_file():
                        total += entry.stat().st_size
                except (PermissionError, OSError):
                    continue
            return total
    except (PermissionError, OSError, FileNotFoundError):
        pass
    return 0


def _sizeof_fmt(num: int | float, suffix: str = "B") -> str:
    """Format bytes to human readable format."""
    for unit in ["", "K", "M", "G", "T"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}P{suffix}"


def _get_coding_agent_targets() -> list[CleanTarget]:
    """Get cleaning targets for coding agent caches.

    Only agents with at least one existing cache path are returned, so the
    table stays limited to the agents actually installed on this machine.
    See ``agents.py`` for the paths themselves.
    """
    roots = resolve_roots()
    targets = []

    for agent in CODING_AGENTS:
        found = [path for path in agent_paths(agent, roots) if path.exists()]
        if found:
            targets.append(
                CleanTarget(
                    name=agent.name,
                    path=found,
                    description=agent.description,
                )
            )

    return targets


def _get_macos_targets() -> list[CleanTarget]:
    """Get cleaning targets for macOS."""
    home = Path.home()
    targets = [
        CleanTarget(
            name="User Caches",
            path=home / "Library" / "Caches",
            description="Application cache files",
        ),
        CleanTarget(
            name="User Logs",
            path=home / "Library" / "Logs",
            description="Application log files",
        ),
        CleanTarget(
            name="Homebrew Cache",
            path=home / "Library" / "Caches" / "Homebrew",
            description="Homebrew package cache",
        ),
        CleanTarget(
            name="Temp Files",
            path=Path("/tmp"),
            description="Temporary files",
            requires_sudo=True,
        ),
        CleanTarget(
            name="System Logs",
            path=Path("/var/log"),
            description="System log files",
            requires_sudo=True,
        ),
        # Leftover macOS update payload, routinely 10GB+. The data volume path
        # is the modern layout; the root one covers pre-Catalina installs.
        # A small "Locked Files" stub inside is SIP protected and survives even
        # under sudo -- it gets skipped with a warning like any other failure.
        CleanTarget(
            name="macOS Install Data",
            path=[
                Path("/System/Volumes/Data/macOS Install Data"),
                Path("/macOS Install Data"),
            ],
            description="Leftover macOS installer payload",
            requires_sudo=True,
        ),
        CleanTarget(
            name="Python Cache",
            path=[
                home / "Library" / "Caches" / "pip",
                home / ".cache" / "pip",
            ],
            description="Python pip cache",
        ),
        CleanTarget(
            name="npm Cache",
            path=home / ".npm",
            description="Node.js npm cache",
        ),
        CleanTarget(
            name="Trash",
            path=home / ".Trash",
            description="Trash bin contents",
        ),
    ]

    # Browser caches
    browser_paths = [
        (
            "Chrome Cache",
            home / "Library" / "Caches" / "Google" / "Chrome",
            "Google Chrome cache",
        ),
        (
            "Safari Cache",
            home / "Library" / "Caches" / "com.apple.Safari",
            "Safari browser cache",
        ),
        (
            "Firefox Cache",
            home / "Library" / "Caches" / "Firefox",
            "Firefox browser cache",
        ),
    ]

    for name, path, desc in browser_paths:
        targets.append(CleanTarget(name=name, path=path, description=desc))

    targets.extend(_get_coding_agent_targets())

    return targets


def _get_linux_targets() -> list[CleanTarget]:
    """Get cleaning targets for Linux."""
    home = Path.home()
    targets = [
        CleanTarget(
            name="User Cache",
            path=home / ".cache",
            description="User application cache",
        ),
        CleanTarget(
            name="Thumbnails",
            path=home / ".thumbnails",
            description="Image thumbnails cache",
        ),
        CleanTarget(
            name="Temp Files",
            path=Path("/tmp"),
            description="Temporary files",
            requires_sudo=True,
        ),
        CleanTarget(
            name="Var Temp",
            path=Path("/var/tmp"),
            description="Variable temporary files",
            requires_sudo=True,
        ),
        CleanTarget(
            name="Python Cache",
            path=home / ".cache" / "pip",
            description="Python pip cache",
        ),
        CleanTarget(
            name="npm Cache",
            path=home / ".npm",
            description="Node.js npm cache",
        ),
    ]

    # Package manager caches (check if they exist)
    pkg_caches = [
        (
            "APT Cache",
            Path("/var/cache/apt/archives"),
            "APT package cache",
            True,
        ),
        (
            "DNF Cache",
            Path("/var/cache/dnf"),
            "DNF package cache",
            True,
        ),
        (
            "Yum Cache",
            Path("/var/cache/yum"),
            "Yum package cache",
            True,
        ),
    ]

    for name, path, desc, sudo in pkg_caches:
        if path.exists():
            targets.append(
                CleanTarget(name=name, path=path, description=desc, requires_sudo=sudo)
            )

    # Browser caches
    browser_paths = [
        (
            "Chrome Cache",
            home / ".cache" / "google-chrome",
            "Google Chrome cache",
        ),
        (
            "Firefox Cache",
            home / ".cache" / "mozilla" / "firefox",
            "Firefox browser cache",
        ),
    ]

    for name, path, desc in browser_paths:
        targets.append(CleanTarget(name=name, path=path, description=desc))

    targets.extend(_get_coding_agent_targets())

    return targets


def _get_windows_targets() -> list[CleanTarget]:
    """Get cleaning targets for Windows."""
    home = Path.home()
    temp_env = os.environ.get("TEMP", "")
    temp_path = Path(temp_env) if temp_env else home / "AppData" / "Local" / "Temp"

    targets = [
        CleanTarget(
            name="User Temp",
            path=temp_path,
            description="User temporary files",
        ),
        CleanTarget(
            name="Windows Temp",
            path=Path("C:/Windows/Temp"),
            description="Windows temporary files",
            requires_sudo=True,
        ),
        CleanTarget(
            name="Prefetch",
            path=Path("C:/Windows/Prefetch"),
            description="Windows prefetch files",
            requires_sudo=True,
        ),
        CleanTarget(
            name="Python Cache",
            path=home / "AppData" / "Local" / "pip" / "Cache",
            description="Python pip cache",
        ),
        CleanTarget(
            name="npm Cache",
            path=home / "AppData" / "Roaming" / "npm-cache",
            description="Node.js npm cache",
        ),
    ]

    # Browser caches
    browser_paths = [
        (
            "Chrome Cache",
            home
            / "AppData"
            / "Local"
            / "Google"
            / "Chrome"
            / "User Data"
            / "Default"
            / "Cache",
            "Google Chrome cache",
        ),
        (
            "Firefox Cache",
            home / "AppData" / "Local" / "Mozilla" / "Firefox" / "Profiles",
            "Firefox browser cache",
        ),
    ]

    for name, path, desc in browser_paths:
        targets.append(CleanTarget(name=name, path=path, description=desc))

    targets.extend(_get_coding_agent_targets())

    return targets


def _get_targets() -> list[CleanTarget]:
    """Get cleaning targets based on current OS."""
    system = platform.system()

    if system == "Darwin":
        return _get_macos_targets()
    elif system == "Linux":
        return _get_linux_targets()
    elif system == "Windows":
        return _get_windows_targets()
    else:
        return []


def target_paths(target: CleanTarget) -> list[Path]:
    return target.path if isinstance(target.path, list) else [target.path]


def scan_target(target: CleanTarget) -> dict:
    """Whether a target exists and how much it holds."""
    paths = [path for path in target_paths(target) if path.exists()]
    return {
        "target": target,
        "size": sum(_get_size(path) for path in paths),
        "exists": bool(paths),
    }


def _scan_targets(targets: list[CleanTarget], console: Console) -> dict:
    """Scan targets and calculate sizes."""
    results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning...", total=len(targets))

        for target in targets:
            progress.update(task, description=f"Scanning {target.name}...")
            results[target.name] = scan_target(target)
            progress.advance(task)

    return results


def clean_path_quietly(path: Path) -> tuple[int, list[str]]:
    """Empty a path; returns bytes freed and a warning per item that failed."""
    if not path.exists():
        return 0, []

    size = _get_size(path)
    warnings = []
    try:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            # Remove contents but keep the directory
            for item in path.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except (PermissionError, OSError) as e:
                    warnings.append(f"Skipped {item.name}: {e}")
        return size, warnings
    except (PermissionError, OSError) as e:
        return 0, [f"Failed to clean {path.name}: {e}"]


def _clean_path(path: Path, console: Console) -> int:
    """Clean a single path and return bytes freed."""
    freed, warnings = clean_path_quietly(path)
    c = theme().colors
    for warning in warnings:
        marker = (
            f"[{c.danger}]✗[/]" if warning.startswith("Failed") else f"[{c.warn}]⚠[/] "
        )
        console.print(f"  {marker} {warning}")
    return freed


def clean_target(target: CleanTarget, elevated: bool) -> tuple[int, list[str]]:
    """Clean every path of a target; sudo-only targets need ``elevated``."""
    if target.requires_sudo and not elevated:
        return 0, [f"Skipping {target.name} (requires sudo)"]
    freed, warnings = 0, []
    for path in target_paths(target):
        path_freed, path_warnings = clean_path_quietly(path)
        freed += path_freed
        warnings.extend(path_warnings)
    return freed, warnings


def _clean_targets(results: dict, console: Console, elevated: bool) -> int:
    """Clean the targets and return total bytes freed.

    Targets flagged ``requires_sudo`` are only attempted when running with
    the privileges to do so; otherwise they are reported and left alone.
    """
    total_freed = 0
    targets_to_clean = [r for r in results.values() if r["exists"] and r["size"] > 0]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Cleaning...", total=len(targets_to_clean))

        for result in targets_to_clean:
            target = result["target"]

            if target.requires_sudo and not elevated:
                console.print(
                    f"  [{theme().colors.warn}]⚠[/]  Skipping {target.name} (requires sudo)"
                )
                progress.advance(task)
                continue

            progress.update(task, description=f"Cleaning {target.name}...")
            for path in target_paths(target):
                total_freed += _clean_path(path, console)
            progress.advance(task)

    return total_freed


def clean_command(args) -> int:
    """Execute the clean command."""
    console = Console()
    t = theme()
    c = t.colors

    # Show header
    header = Text()
    header.append("🧹 System Cleanup\n", style=f"bold {c.accent}")
    header.append("Deep clean your machine", style=c.muted)
    console.print(Panel(header, border_style=c.accent, box=t.design.app_box))
    console.print()

    # Detect OS
    system = platform.system()
    os_name = {
        "Darwin": "macOS",
        "Linux": "Linux",
        "Windows": "Windows",
    }.get(system, system)

    console.print(f"📍 Detected OS: [{c.ok}]{os_name}[/]")

    elevated = _is_elevated()
    if elevated:
        console.print(f"🔑 Running elevated: [{c.ok}]sudo targets included[/]")
    console.print()

    # Get targets
    targets = _get_targets()

    if not targets:
        console.print(f"[{c.danger}]No cleaning targets available for this OS[/]")
        return 1

    # Scan targets
    console.print("🔍 Scanning for cleanable items...")
    results = _scan_targets(targets, console)

    # Display results
    table = Table(
        title="Cleaning Targets",
        show_header=True,
        header_style=f"bold {c.accent}",
        box=t.design.app_box,
    )
    table.add_column("Target", style=c.text, width=20)
    table.add_column("Status", width=10)
    table.add_column("Size", justify="right", width=12)
    table.add_column("Description", style=c.muted, width=30)
    table.add_column("Requires Sudo", justify="center", width=13)

    total_size = 0
    sudo_size = 0
    cleanable_count = 0

    for result in results.values():
        target = result["target"]
        size = result["size"]
        exists = result["exists"]

        if exists and size > 0:
            status = f"[{c.ok}]✓[/]"
            size_str = _sizeof_fmt(size)
            total_size += size
            cleanable_count += 1

            if target.requires_sudo:
                sudo_size += size
        elif exists:
            status = f"[{c.muted}]○[/]"
            size_str = f"[{c.muted}]empty[/]"
        else:
            status = f"[{c.muted}]-[/]"
            size_str = f"[{c.muted}]n/a[/]"

        sudo_marker = f"[{c.warn}]✓[/]" if target.requires_sudo else f"[{c.muted}]-[/]"

        table.add_row(
            target.name,
            status,
            size_str,
            target.description,
            sudo_marker,
        )

    console.print()
    console.print(table)
    console.print()

    # Summary
    if cleanable_count == 0:
        console.print(f"[{c.ok}]Nothing to clean! Your system is already clean.[/]")
        return 0

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()

    summary.add_row("Total cleanable:", f"[{c.ok}]{_sizeof_fmt(total_size)}[/]")
    if sudo_size > 0:
        note = "" if elevated else f" [{c.muted}](will be skipped)[/]"
        summary.add_row(
            "Requires sudo:",
            f"[{c.warn}]{_sizeof_fmt(sudo_size)}[/]{note}",
        )
    summary.add_row(
        "Can clean now:",
        f"[{c.accent}]{_sizeof_fmt(total_size if elevated else total_size - sudo_size)}[/]",
    )

    console.print(
        Panel(summary, title="Summary", border_style=c.ok, box=t.design.app_box)
    )
    console.print()

    # Dry run mode
    if getattr(args, "dry_run", False):
        console.print(f"[{c.warn}]Dry run mode - no files will be deleted[/]")
        return 0

    # Confirmation
    if sudo_size > 0 and not elevated:
        console.print(
            f"[{c.warn}]⚠[/]  Items requiring sudo will be skipped. "
            "Run with sudo to clean them."
        )
        console.print()

    try:
        response = console.input(f"[bold {c.warn}]⚠ Proceed with cleaning? (y/N):[/] ")
        if response.lower() not in ["y", "yes"]:
            console.print(f"[{c.muted}]Cancelled.[/]")
            return 0
    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{c.muted}]Cancelled.[/]")
        return 0

    console.print()

    # Clean
    console.print("🧹 Cleaning...")
    freed = _clean_targets(results, console, elevated)

    console.print()

    # Final summary
    success = Text()
    success.append("✨ Cleaning Complete!\n", style=f"bold {c.ok}")
    success.append(f"Freed {_sizeof_fmt(freed)} of disk space", style=c.text)

    console.print(Panel(success, border_style=c.ok, box=t.design.app_box))

    return 0
