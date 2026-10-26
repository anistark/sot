"""Session restore files left behind by web browsers.

Browsers snapshot the open windows and tabs to disk so they can be restored
after a restart or a crash. Only the newest snapshot is ever read back; older
ones pile up per profile and are safe to remove. The newest ones are what
brings your tabs back, so they're only touched with ``--force``.

* Chromium browsers keep ``Session_<stamp>``, ``Tabs_<stamp>`` and
  ``Apps_<stamp>`` files under ``<profile>/Sessions``. The highest stamp of
  each kind is the live one.
* Firefox browsers keep ``sessionstore.jsonlz4`` in the profile and
  ``recovery``/``previous`` snapshots under ``sessionstore-backups``. The
  ``upgrade.jsonlz4-<build>`` copies taken on each version upgrade are never
  read unless you roll Firefox back.

Paths use the cache roots from ``agents.py``, with entries for every platform
side by side -- the ones that don't apply simply won't exist on disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, NamedTuple

from .agents import expand_paths


class Browser(NamedTuple):
    """A browser and where it keeps its profiles.

    For Chromium browsers ``paths`` are the user data directories holding the
    profiles; for Firefox browsers they're the directories of profiles.
    """

    name: str
    engine: str
    paths: tuple[str, ...]


class SessionFiles(NamedTuple):
    """Session files split by whether the browser will read them again."""

    stale: list[Path]
    current: list[Path]


CHROMIUM = "chromium"
FIREFOX = "firefox"

BROWSERS: tuple[Browser, ...] = (
    Browser(
        "Chrome",
        CHROMIUM,
        (
            "{mac_app_support}/Google/Chrome",
            "{xdg_config}/google-chrome",
            "{localappdata}/Google/Chrome/User Data",
        ),
    ),
    Browser(
        "Chromium",
        CHROMIUM,
        (
            "{mac_app_support}/Chromium",
            "{xdg_config}/chromium",
            "{localappdata}/Chromium/User Data",
        ),
    ),
    Browser(
        "Edge",
        CHROMIUM,
        (
            "{mac_app_support}/Microsoft Edge",
            "{xdg_config}/microsoft-edge",
            "{localappdata}/Microsoft/Edge/User Data",
        ),
    ),
    Browser(
        "Brave",
        CHROMIUM,
        (
            "{mac_app_support}/BraveSoftware/Brave-Browser",
            "{xdg_config}/BraveSoftware/Brave-Browser",
            "{localappdata}/BraveSoftware/Brave-Browser/User Data",
        ),
    ),
    Browser(
        "Vivaldi",
        CHROMIUM,
        (
            "{mac_app_support}/Vivaldi",
            "{xdg_config}/vivaldi",
            "{localappdata}/Vivaldi/User Data",
        ),
    ),
    # Opera keeps its single profile at the top of the directory.
    Browser(
        "Opera",
        CHROMIUM,
        (
            "{mac_app_support}/com.operasoftware.Opera",
            "{xdg_config}/opera",
            "{appdata}/Opera Software/Opera Stable",
        ),
    ),
    Browser("Arc", CHROMIUM, ("{mac_app_support}/Arc/User Data",)),
    Browser(
        "Firefox",
        FIREFOX,
        (
            "{mac_app_support}/Firefox/Profiles",
            "{home}/.mozilla/firefox",
            "{home}/snap/firefox/common/.mozilla/firefox",
            "{appdata}/Mozilla/Firefox/Profiles",
        ),
    ),
    Browser(
        "LibreWolf",
        FIREFOX,
        (
            "{mac_app_support}/librewolf/Profiles",
            "{home}/.librewolf",
            "{appdata}/librewolf/Profiles",
        ),
    ),
    Browser(
        "Zen",
        FIREFOX,
        (
            "{mac_app_support}/zen/Profiles",
            "{home}/.zen",
            "{appdata}/zen/Profiles",
        ),
    ),
)


def _subdirs(path: Path) -> list[Path]:
    try:
        return sorted(p for p in path.iterdir() if p.is_dir())
    except OSError:
        return []


def _files(path: Path) -> list[Path]:
    try:
        return sorted(p for p in path.iterdir() if p.is_file())
    except OSError:
        return []


def chromium_sessions(user_data: Path) -> SessionFiles:
    """Split every profile's ``Sessions`` files into stale and current.

    Files are grouped by the name before the stamp, and only the newest of
    each group is current. Anything not named that way is left as current, so
    it's only removed with ``--force``.
    """
    stale: list[Path] = []
    current: list[Path] = []

    for profile in [user_data, *_subdirs(user_data)]:
        groups: dict[str, list[tuple[int, Path]]] = {}
        for path in _files(profile / "Sessions"):
            kind, _, stamp = path.name.rpartition("_")
            if kind and stamp.isdigit():
                groups.setdefault(kind, []).append((int(stamp), path))
            else:
                current.append(path)

        for snapshots in groups.values():
            snapshots.sort()
            stale.extend(path for _, path in snapshots[:-1])
            current.append(snapshots[-1][1])

    return SessionFiles(stale, current)


def firefox_sessions(profiles: Path) -> SessionFiles:
    """Split every profile's session store into stale and current."""
    stale: list[Path] = []
    current: list[Path] = []

    for profile in _subdirs(profiles):
        store = profile / "sessionstore.jsonlz4"
        if store.is_file():
            current.append(store)
        for path in _files(profile / "sessionstore-backups"):
            if path.name.startswith("upgrade.jsonlz4-"):
                stale.append(path)
            else:
                current.append(path)

    return SessionFiles(stale, current)


def browser_sessions(
    browser: Browser, roots: Mapping[str, Path] | None = None
) -> SessionFiles:
    """Every session file the browser has on this machine."""
    scan = chromium_sessions if browser.engine == CHROMIUM else firefox_sessions
    stale: list[Path] = []
    current: list[Path] = []

    for path in expand_paths(browser.paths, roots):
        if path.is_dir():
            found = scan(path)
            stale.extend(found.stale)
            current.extend(found.current)

    return SessionFiles(stale, current)
