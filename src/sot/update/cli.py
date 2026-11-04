"""Find the newest sot release and move this install to it."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from http.client import HTTPException
from pathlib import Path
from urllib.request import Request, urlopen

from rich.console import Console
from rich.markup import escape

from ..__about__ import __version__
from .._theme import theme
from .install import HOMEBREW, detect_install, package_url, upgrade_commands

PYPI_URL = "https://pypi.org/pypi/sot/json"
TIMEOUT = 15
ON_WINDOWS = os.name == "nt"
USER_AGENT = {"User-Agent": f"sot/{__version__}"}
FINAL_RELEASE = re.compile(r"\d+(?:\.\d+)*")
VERSION_LINE = re.compile(r"Version:\s+(\S+)")

Version = tuple[int, ...]


def parse_version(text: str) -> Version:
    """The numeric part of a version, so 6.4.0rc1 reads as 6.4.0."""
    match = FINAL_RELEASE.match(text)
    return tuple(int(part) for part in match.group().split(".")) if match else ()


def fetch_releases() -> list[Version]:
    """Every final release on PyPI that hasn't been yanked."""
    request = Request(PYPI_URL, headers=USER_AGENT)
    with urlopen(request, timeout=TIMEOUT) as response:
        releases = json.load(response)["releases"]
    return [
        parse_version(version)
        for version, files in releases.items()
        if FINAL_RELEASE.fullmatch(version)
        and any(not file.get("yanked") for file in files)
    ]


def pick_target(
    current: Version, releases: list[Version], allow_major: bool
) -> Version | None:
    """The newest release above ``current``, within its major unless ``allow_major``."""
    newer = [
        release
        for release in releases
        if release > current and (allow_major or release[0] == current[0])
    ]
    return max(newer, default=None)


def _show(version: Version) -> str:
    return ".".join(str(part) for part in version)


def _print_commands(
    console: Console, commands: list[list[str]], url: str | None
) -> None:
    if url:
        console.print(f"Download {url}", markup=False, highlight=False, soft_wrap=True)
    for command in commands:
        console.print(
            f"$ {shlex.join(command)}", markup=False, highlight=False, soft_wrap=True
        )


def _download(url: str, path: Path) -> None:
    with urlopen(Request(url, headers=USER_AGENT), timeout=TIMEOUT) as response:
        with path.open("wb") as file:
            shutil.copyfileobj(response, file)


def _run_commands(commands: list[list[str]], url: str | None) -> bool:
    """Run ``commands`` from a scratch folder holding the package at ``url``."""
    with tempfile.TemporaryDirectory() as folder:
        if url:
            try:
                _download(url, Path(folder, url.rsplit("/", 1)[-1]))
            except (OSError, HTTPException) as error:
                print(f"❌ Couldn't download {url}: {error}")
                return False
        for command in commands:
            try:
                code = subprocess.run(command, cwd=folder).returncode
            except OSError as error:
                print(f"❌ Couldn't run {command[0]}: {error}")
                return False
            if code != 0:
                print(f"❌ {shlex.join(command)} failed with exit code {code}")
                return False
    return True


def _installed_version() -> str | None:
    """What the ``sot`` being run reports, read from a fresh process."""
    try:
        result = subprocess.run(
            [sys.argv[0], "--version"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = VERSION_LINE.search(result.stdout)
    return match.group(1) if match else None


def _report(manager: str, version: str) -> int:
    # The old environment may be gone by now, so stay off rich and its lazy imports.
    installed = _installed_version()
    if installed is None:
        print(f"✅ {manager} finished. `sot --version` should now show {version}.")
        return 0
    if installed != version:
        print(
            f"⚠️  {manager} finished, but sot still reports {installed}, not {version}."
        )
        return 1
    print(f"✅ sot is now {version}")
    return 0


def update_command(args) -> int:
    """Run ``sot update``, which stays on this major, or ``sot upgrade``, which doesn't."""
    console = Console()
    c = theme().colors
    allow_major = args.command == "upgrade"

    install = detect_install()
    console.print(
        f"📦 sot [{c.ok}]{__version__}[/] via [{c.ok}]{install.manager}[/] "
        f"[{c.muted}]{escape(str(install.location))}[/]",
        highlight=False,
        soft_wrap=True,
    )
    if install.blocked:
        console.print(f"[{c.warn}]{escape(install.blocked)}[/]", highlight=False)
        return 1

    try:
        releases = fetch_releases()
    except (OSError, ValueError, KeyError, HTTPException) as error:
        console.print(f"[{c.danger}]❌ Couldn't read PyPI: {escape(str(error))}[/]")
        return 1

    current = parse_version(__version__)
    newest = max(releases, default=current)
    target = pick_target(current, releases, allow_major)
    major_hint = None
    if newest[0] > current[0] and not allow_major:
        major_hint = (
            f"⬆️  {_show(newest)} is a major release: `sot upgrade` moves to it."
        )

    if target is None:
        scope = f"{current[0]}.x " if major_hint else ""
        console.print(
            f"[{c.ok}]✅ Already on the newest {scope}release[/]", highlight=False
        )
        if major_hint:
            console.print(major_hint, highlight=False)
        return 0

    if install.manager == HOMEBREW and target != newest:
        console.print(
            f"[{c.warn}]Homebrew only installs the newest release, {_show(newest)}. "
            f"`sot upgrade` moves to it.[/]",
            highlight=False,
        )
        return 1

    version = _show(target)
    commands = upgrade_commands(install, version, target == newest)
    url = package_url(install, version)
    console.print(f"🚀 [{c.ok}]{version}[/] is available", highlight=False)
    if major_hint:
        console.print(major_hint, highlight=False)

    if args.dry_run:
        _print_commands(console, commands, url)
        console.print(f"[{c.warn}]Dry run mode - nothing was changed[/]")
        return 0
    if ON_WINDOWS:
        console.print("Windows can't replace a running program, so run this instead:")
        _print_commands(console, commands, url)
        return 1

    _print_commands(console, commands, url)
    try:
        finished = _run_commands(commands, url)
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 1
    return _report(install.manager, version) if finished else 1
