"""Clean command implementation for system cleanup."""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path
from typing import NamedTuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text


class CleanTarget(NamedTuple):
    """Represents a cleaning target with metadata."""

    name: str
    path: Path | list[Path]
    description: str
    requires_sudo: bool = False
    recursive: bool = True


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


def _sizeof_fmt(num: int, suffix: str = "B") -> str:
    """Format bytes to human readable format."""
    for unit in ["", "K", "M", "G", "T"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}P{suffix}"


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
            home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
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

            size = 0
            exists = False

            if isinstance(target.path, list):
                for path in target.path:
                    if path.exists():
                        exists = True
                        size += _get_size(path)
            else:
                if target.path.exists():
                    exists = True
                    size = _get_size(target.path)

            results[target.name] = {
                "target": target,
                "size": size,
                "exists": exists,
            }

            progress.advance(task)

    return results


def _clean_path(path: Path, console: Console) -> int:
    """Clean a single path and return bytes freed."""
    if not path.exists():
        return 0

    size = _get_size(path)

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
                    console.print(f"  [yellow]⚠[/yellow]  Skipped {item.name}: {e}")
        return size
    except (PermissionError, OSError) as e:
        console.print(f"  [red]✗[/red] Failed to clean {path.name}: {e}")
        return 0


def _clean_targets(results: dict, console: Console) -> int:
    """Clean the targets and return total bytes freed."""
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

            if target.requires_sudo:
                console.print(
                    f"  [yellow]⚠[/yellow]  Skipping {target.name} (requires sudo)"
                )
                progress.advance(task)
                continue

            progress.update(task, description=f"Cleaning {target.name}...")

            if isinstance(target.path, list):
                for path in target.path:
                    total_freed += _clean_path(path, console)
            else:
                total_freed += _clean_path(target.path, console)

            progress.advance(task)

    return total_freed


def clean_command(args) -> int:
    """Execute the clean command."""
    console = Console()

    # Show header
    header = Text()
    header.append("🧹 System Cleanup\n", style="bold bright_cyan")
    header.append("Deep clean your machine", style="dim")
    console.print(Panel(header, border_style="bright_cyan"))
    console.print()

    # Detect OS
    system = platform.system()
    os_name = {
        "Darwin": "macOS",
        "Linux": "Linux",
        "Windows": "Windows",
    }.get(system, system)

    console.print(f"📍 Detected OS: [bright_green]{os_name}[/]")
    console.print()

    # Get targets
    targets = _get_targets()

    if not targets:
        console.print("[red]❌ No cleaning targets available for this OS[/]")
        return 1

    # Scan targets
    console.print("🔍 Scanning for cleanable items...")
    results = _scan_targets(targets, console)

    # Display results
    table = Table(title="Cleaning Targets", show_header=True, header_style="bold cyan")
    table.add_column("Target", style="bright_white", width=20)
    table.add_column("Status", width=10)
    table.add_column("Size", justify="right", width=12)
    table.add_column("Description", style="dim", width=30)
    table.add_column("Requires Sudo", justify="center", width=13)

    total_size = 0
    sudo_size = 0
    cleanable_count = 0

    for result in results.values():
        target = result["target"]
        size = result["size"]
        exists = result["exists"]

        if exists and size > 0:
            status = "[green]✓[/]"
            size_str = _sizeof_fmt(size)
            total_size += size
            cleanable_count += 1

            if target.requires_sudo:
                sudo_size += size
        elif exists:
            status = "[dim]○[/]"
            size_str = "[dim]empty[/]"
        else:
            status = "[dim]-[/]"
            size_str = "[dim]n/a[/]"

        sudo_marker = "[yellow]✓[/]" if target.requires_sudo else "[dim]-[/]"

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
        console.print("[green]✨ Nothing to clean! Your system is already clean.[/]")
        return 0

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()

    summary.add_row("Total cleanable:", f"[bright_green]{_sizeof_fmt(total_size)}[/]")
    if sudo_size > 0:
        summary.add_row(
            "Requires sudo:",
            f"[yellow]{_sizeof_fmt(sudo_size)}[/] [dim](will be skipped)[/]",
        )
    summary.add_row(
        "Can clean now:",
        f"[bright_cyan]{_sizeof_fmt(total_size - sudo_size)}[/]",
    )

    console.print(Panel(summary, title="Summary", border_style="green"))
    console.print()

    # Dry run mode
    if getattr(args, "dry_run", False):
        console.print("[bright_yellow]🏃 Dry run mode - no files will be deleted[/]")
        return 0

    # Confirmation
    if sudo_size > 0:
        console.print(
            "[yellow]⚠[/yellow]  Items requiring sudo will be skipped. "
            "Run with sudo to clean them."
        )
        console.print()

    try:
        response = console.input(
            "[bold bright_yellow]⚠ Proceed with cleaning? (y/N):[/] "
        )
        if response.lower() not in ["y", "yes"]:
            console.print("[dim]Cancelled.[/]")
            return 0
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Cancelled.[/]")
        return 0

    console.print()

    # Clean
    console.print("🧹 Cleaning...")
    freed = _clean_targets(results, console)

    console.print()

    # Final summary
    success = Text()
    success.append("✨ Cleaning Complete!\n", style="bold bright_green")
    success.append(f"Freed {_sizeof_fmt(freed)} of disk space", style="bright_white")

    console.print(Panel(success, border_style="bright_green"))

    return 0
