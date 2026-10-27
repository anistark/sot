"""Clean command implementation for system cleanup."""

from __future__ import annotations

import bisect
import os
import platform
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from .._theme import theme
from .agents import (
    AGENT_VERSIONS,
    CODING_AGENTS,
    agent_paths,
    expand_paths,
    resolve_roots,
    stale_versions,
)
from .apps import app_caches
from .browsers import (
    BROWSERS,
    browser_caches,
    browser_databases,
    browser_privacy,
    browser_sessions,
    free_space,
    vacuum,
)
from .devtools import DEV_CACHES, REVIEW
from .projects import ACTIVE_DAYS, project_artifacts
from .system import (
    code_sign_clones,
    darwin_targets,
    darwin_user_dir,
    device_support,
    journal_target,
    simulator_target,
    snap_target,
    system_targets,
)
from .targets import (
    CleanTarget,
    empty_path,
    keep_exactly,
    measure_target,
    run,
    target_paths,
)

__all__ = ["CleanTarget", "clean_command", "clean_target", "scan_target"]

SCAN_WORKERS = 8

# Live data under the cache folders that is costly or harmful to lose:
# fonts, search and iCloud state, interpreters, downloaded browsers and models.
CACHE_KEEP = (
    "com.apple.FontRegistry*",
    "com.apple.Spotlight*",
    "Spotlight*",
    "CloudKit*",
    "com.apple.finder",
    "kitty",
    "pypoetry/virtualenvs",
    "ms-playwright*",
    "puppeteer",
    "JetBrains*",
    "com.jetbrains.toolbox*",
    "lm-studio",
    "tealdeer",
    "org.R-project.R/R/renv",
)

PRIVACY_DESCRIPTIONS = {
    "Cookies": "Signs you out of every site",
    "History": "Browsing history and top sites",
    "Site Data": "Site storage and offline data",
}


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


def _sizeof_fmt(num: int | float, suffix: str = "B") -> str:
    """Format bytes to human readable format."""
    for unit in ["", "K", "M", "G", "T"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}P{suffix}"


def _unique(paths: list[Path]) -> list[Path]:
    return list(dict.fromkeys(paths))


def _cache_keep(root: Path) -> tuple[str, ...]:
    return tuple(
        keep_exactly(root) + os.sep + name.replace("/", os.sep) for name in CACHE_KEEP
    )


def _cache_dir(name: str, path: Path, description: str) -> CleanTarget:
    return CleanTarget(name, path, description, keep=_cache_keep(path))


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

    for versions in AGENT_VERSIONS:
        stale = stale_versions(versions, roots)
        if stale:
            targets.append(
                CleanTarget(versions.name, stale, "Old binaries nothing runs")
            )

    return targets


def _get_browser_session_targets(force: bool = False) -> list[CleanTarget]:
    """Get cleaning targets for browser session restore files.

    Only snapshots the browser won't read again are included, unless
    ``force`` is set: then the current ones go too, and with them the tabs
    the browser would restore. Browsers with nothing to clean are left out.
    See ``browsers.py`` for the paths and how files are told apart.
    """
    roots = resolve_roots()
    targets = []

    for browser in BROWSERS:
        sessions = browser_sessions(browser, roots)
        files = sessions.stale + sessions.current if force else sessions.stale
        if files:
            targets.append(
                CleanTarget(
                    name=f"{browser.name} Sessions",
                    path=files,
                    description=(
                        "Sessions, incl. current tabs"
                        if force
                        else "Old session snapshots"
                    ),
                )
            )

    return targets


def _get_browser_targets(privacy: bool = False) -> list[CleanTarget]:
    """Caches and database free space of every browser, and with ``privacy``
    its cookies, history and site data."""
    roots = resolve_roots()
    targets = []

    for browser in BROWSERS:
        caches = browser_caches(browser, roots)
        if caches:
            targets.append(
                CleanTarget(
                    f"{browser.name} Cache", caches, "Page, GPU, code and model caches"
                )
            )

        databases = browser_databases(browser, roots)
        if free_space(databases):
            targets.append(
                CleanTarget(
                    f"{browser.name} Databases",
                    databases,
                    "Free space in its databases",
                    action=partial(vacuum, databases),
                    measure=partial(free_space, databases),
                )
            )

        if privacy:
            for kind, paths in browser_privacy(browser, roots).items():
                targets.append(
                    CleanTarget(
                        f"{browser.name} {kind}", paths, PRIVACY_DESCRIPTIONS[kind]
                    )
                )

    return targets


def _get_app_targets() -> list[CleanTarget]:
    return [
        CleanTarget(f"{app.name} App Cache", app.paths, "Electron app caches and logs")
        for app in app_caches(resolve_roots())
    ]


def _get_dev_targets(elevated: bool = False) -> list[CleanTarget]:
    """Developer tool caches, cleaned by the tool itself when it's installed.

    Under sudo the tools would clean root's caches, so the paths are deleted.
    """
    roots = resolve_roots()
    targets = []

    for cache in DEV_CACHES:
        found = _unique([p for p in expand_paths(cache.paths, roots) if p.exists()])
        if not found:
            continue
        action = None
        if cache.command and not elevated and shutil.which(cache.command[0]):
            action = partial(run, cache.command, env=cache.env)
        targets.append(CleanTarget(cache.name, found, cache.description, action=action))

    return targets


def _get_review_targets() -> list[CleanTarget]:
    roots = resolve_roots()
    targets = []

    for review in REVIEW:
        found = _unique([p for p in expand_paths(review.paths, roots) if p.exists()])
        if found:
            targets.append(
                CleanTarget(review.name, found, review.description, review=True)
            )

    return targets


def _get_project_targets(root: Path, force: bool = False) -> list[CleanTarget]:
    """Build output and dependencies in projects under ``root``."""
    targets = []

    for name, found in sorted(project_artifacts(root).items()):
        paths = found.stale + found.current if force else found.stale
        if paths:
            when = "any project" if force else f"projects idle {ACTIVE_DAYS}+ days"
            targets.append(CleanTarget(f"{name}/", paths, f"{len(paths)} in {when}"))

    return targets


def _get_common_targets(
    force: bool = False, privacy: bool = False
) -> list[CleanTarget]:
    return [
        *_get_browser_targets(privacy),
        *_get_browser_session_targets(force),
        *_get_app_targets(),
        *_get_dev_targets(_is_elevated()),
        *_get_coding_agent_targets(),
        *system_targets(privacy, resolve_roots()),
        *_get_review_targets(),
    ]


def _get_macos_targets(force: bool = False, privacy: bool = False) -> list[CleanTarget]:
    """Get cleaning targets for macOS."""
    home = Path.home()
    targets = [
        _cache_dir(
            "User Caches", home / "Library" / "Caches", "Application cache files"
        ),
        _cache_dir("XDG Cache", home / ".cache", "Command line tool caches"),
        CleanTarget(
            name="User Logs",
            path=home / "Library" / "Logs",
            description="Application log files",
        ),
        CleanTarget(
            name="Temp Files",
            path=Path("/tmp"),
            description="Temp files over 3 days old",
            requires_sudo=True,
            older_than=3,
        ),
        CleanTarget(
            name="System Logs",
            path=Path("/var/log"),
            description="System logs over 7 days old",
            requires_sudo=True,
            older_than=7,
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
        CleanTarget(
            name="Safari Cache",
            path=home / "Library" / "Caches" / "com.apple.Safari",
            description="Safari browser cache",
        ),
    ]

    darwin = darwin_user_dir()
    if darwin:
        targets.extend(darwin_targets(darwin))
        clones = code_sign_clones(darwin)
        paths = clones.stale + clones.current if force else clones.stale
        if paths:
            targets.append(
                CleanTarget(
                    "Browser Clones",
                    paths,
                    "Copies Chrome-based browsers leaked",
                )
            )

    symbols = device_support()
    paths = symbols.stale + symbols.current if force else symbols.stale
    if paths:
        targets.append(
            CleanTarget("Device Support", paths, "Old iOS symbols; keeps newest two")
        )
    targets.extend(simulator_target())
    targets.extend(_get_common_targets(force, privacy))

    return targets


def _get_linux_targets(force: bool = False, privacy: bool = False) -> list[CleanTarget]:
    """Get cleaning targets for Linux."""
    home = Path.home()
    targets = [
        _cache_dir("User Cache", home / ".cache", "User application cache"),
        CleanTarget(
            name="Thumbnails",
            path=home / ".thumbnails",
            description="Image thumbnails cache",
        ),
        CleanTarget(
            name="Temp Files",
            path=Path("/tmp"),
            description="Temp files over 3 days old",
            requires_sudo=True,
            older_than=3,
        ),
        CleanTarget(
            name="Var Temp",
            path=Path("/var/tmp"),
            description="Temp files over 7 days old",
            requires_sudo=True,
            older_than=7,
        ),
        CleanTarget(
            name="System Logs",
            path=Path("/var/log"),
            description="System logs over 7 days old",
            requires_sudo=True,
            older_than=7,
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

    targets.extend(journal_target())
    targets.extend(snap_target())
    targets.extend(_get_common_targets(force, privacy))

    return targets


def _get_windows_targets(
    force: bool = False, privacy: bool = False
) -> list[CleanTarget]:
    """Get cleaning targets for Windows."""
    home = Path.home()
    temp_env = os.environ.get("TEMP", "")
    temp_path = Path(temp_env) if temp_env else home / "AppData" / "Local" / "Temp"

    targets = [
        CleanTarget(
            name="User Temp",
            path=temp_path,
            description="Temp files over 3 days old",
            older_than=3,
        ),
        CleanTarget(
            name="Windows Temp",
            path=Path("C:/Windows/Temp"),
            description="Temp files over 3 days old",
            requires_sudo=True,
            older_than=3,
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

    targets.extend(_get_common_targets(force, privacy))

    return targets


def _separate(targets: list[CleanTarget]) -> list[CleanTarget]:
    """Keep a path another target covers out of every target holding it.

    ``~/Library/Caches`` holds the Homebrew and browser caches listed on
    their own rows, so it skips them: each byte is counted and removed once,
    and unticking a row really leaves it alone.
    """
    owned = sorted(
        (str(path), index)
        for index, target in enumerate(targets)
        for path in target_paths(target)
    )
    names = [name for name, _ in owned]
    separated = []

    for index, target in enumerate(targets):
        nested = []
        for path in target_paths(target):
            prefix = str(path).rstrip(os.sep) + os.sep
            start = bisect.bisect_left(names, prefix)
            for name, owner in owned[start:]:
                if not name.startswith(prefix):
                    break
                if owner != index:
                    nested.append(keep_exactly(Path(name)))
        separated.append(
            target._replace(keep=target.keep + tuple(nested)) if nested else target
        )

    return separated


def _unique_names(targets: list[CleanTarget]) -> list[CleanTarget]:
    seen: dict[str, int] = {}
    named = []
    for target in targets:
        count = seen[target.name] = seen.get(target.name, 0) + 1
        named.append(
            target if count == 1 else target._replace(name=f"{target.name} ({count})")
        )
    return named


def _get_targets(
    force: bool = False, privacy: bool = False, projects: Path | None = None
) -> list[CleanTarget]:
    """Get cleaning targets based on current OS.

    ``force`` also includes data still in use, like the browser sessions
    that restore open tabs. ``privacy`` adds cookies, history and site data,
    ``projects`` the build output of the projects under that folder.
    """
    system = platform.system()

    if system == "Darwin":
        targets = _get_macos_targets(force, privacy)
    elif system == "Linux":
        targets = _get_linux_targets(force, privacy)
    elif system == "Windows":
        targets = _get_windows_targets(force, privacy)
    else:
        return []

    if projects is not None:
        targets.extend(_get_project_targets(projects, force))

    return _unique_names(_separate(targets))


def scan_target(target: CleanTarget) -> dict:
    """Whether a target exists and how much it holds."""
    exists = any(os.path.lexists(path) for path in target_paths(target))
    return {
        "target": target,
        "size": measure_target(target) if exists else 0,
        "exists": exists,
    }


def scan_targets(
    targets: list[CleanTarget],
    scanned: Callable[[CleanTarget], None] | None = None,
) -> dict[str, dict]:
    """Scan targets in parallel, keyed by name in their original order.

    Package stores hold millions of files and the walk is spent waiting on
    the kernel, so threads overlap well. ``scanned`` hears of each one done.
    """
    with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
        futures = {pool.submit(scan_target, target): target for target in targets}
        for future in as_completed(futures):
            if scanned is not None:
                scanned(futures[future])
    return {target.name: future.result() for future, target in futures.items()}


def _scan_targets(targets: list[CleanTarget], console: Console) -> dict:
    """Scan targets and calculate sizes."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning...", total=len(targets))

        def scanned(target: CleanTarget) -> None:
            progress.update(task, description=f"Scanned {target.name}...")
            progress.advance(task)

        return scan_targets(targets, scanned)


def clean_target(
    target: CleanTarget, elevated: bool, size: int | None = None
) -> tuple[int, list[str]]:
    """Clean every path of a target; sudo-only targets need ``elevated``.

    Returns the bytes freed, measured again afterwards against ``size`` from
    the scan, and the warnings.
    """
    if target.review:
        return 0, [f"Skipping {target.name} (review only)"]
    if target.requires_sudo and not elevated:
        return 0, [f"Skipping {target.name} (requires sudo)"]

    before = measure_target(target) if size is None else size
    if target.action is not None:
        warnings = target.action()
    else:
        warnings = [
            warning
            for path in target_paths(target)
            for warning in empty_path(path, target.keep, target.older_than)
        ]
    return max(before - measure_target(target), 0), warnings


def _clean_targets(results: dict, console: Console, elevated: bool) -> int:
    """Clean the targets and return total bytes freed.

    Targets flagged ``requires_sudo`` are only attempted when running with
    the privileges to do so; otherwise they are reported and left alone.
    """
    c = theme().colors
    total_freed = 0
    targets_to_clean = [
        r
        for r in results.values()
        if r["exists"] and r["size"] > 0 and not r["target"].review
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Cleaning...", total=len(targets_to_clean))

        for result in targets_to_clean:
            target = result["target"]
            progress.update(task, description=f"Cleaning {target.name}...")
            freed, warnings = clean_target(target, elevated, result["size"])
            total_freed += freed
            for warning in warnings:
                failed = warning.startswith("Failed")
                marker = f"[{c.danger}]✗[/]" if failed else f"[{c.warn}]⚠[/] "
                console.print(f"  {marker} {warning}")
            progress.advance(task)

    return total_freed


def _print_options(args, console: Console) -> tuple[bool, bool, Path | None]:
    """Announce the flags widening the scan; returns ``_get_targets`` args."""
    c = theme().colors
    force = getattr(args, "force", False)
    if force:
        console.print(f"💪 Forced: [{c.warn}]data still in use included[/]")
    privacy = getattr(args, "privacy", False)
    if privacy:
        console.print(
            f"🍪 Privacy: [{c.warn}]cookies, history and site data included[/]"
        )
    projects = getattr(args, "projects", None)
    if projects:
        projects = Path(projects).expanduser().resolve()
        console.print(f"📁 Projects: [{c.ok}]{projects}[/]")
    console.print()
    return force, privacy, projects


def _print_review(review: list[dict], console: Console) -> None:
    if not review:
        return
    t = theme()
    c = t.colors
    table = Table(
        title="Review (never cleaned)",
        show_header=True,
        header_style=f"bold {c.accent}",
        box=t.design.app_box,
    )
    table.add_column("Target", style=c.text, width=20)
    table.add_column("Size", justify="right", width=12)
    table.add_column("Description", style=c.muted, width=40)
    for result in review:
        target = result["target"]
        table.add_row(target.name, _sizeof_fmt(result["size"]), target.description)
    console.print(table)
    console.print()


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
    targets = _get_targets(*_print_options(args, console))

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

    review = [r for r in results.values() if r["target"].review and r["size"] > 0]

    for result in results.values():
        target = result["target"]
        size = result["size"]
        exists = result["exists"]
        if target.review:
            continue

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
    _print_review(review, console)

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
