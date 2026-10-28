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

Beyond sessions this finds each browser's caches, the cookies, history and
site data cleared with ``--privacy``, and the SQLite databases whose free
pages a ``VACUUM`` gives back.

Paths use the cache roots from ``agents.py``, with entries for every platform
side by side -- the ones that don't apply simply won't exist on disk.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Mapping, NamedTuple

from .agents import expand_paths, resolve_roots


class Browser(NamedTuple):
    """A browser and where it keeps its profiles.

    For Chromium browsers ``paths`` are the user data directories holding the
    profiles; for Firefox browsers they're the directories of profiles.
    ``caches`` are the platform cache directories kept apart from them.
    """

    name: str
    engine: str
    paths: tuple[str, ...]
    caches: tuple[str, ...] = ()


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
        ("{mac_caches}/Google/Chrome", "{xdg_cache}/google-chrome"),
    ),
    Browser(
        "Chromium",
        CHROMIUM,
        (
            "{mac_app_support}/Chromium",
            "{xdg_config}/chromium",
            "{localappdata}/Chromium/User Data",
        ),
        ("{mac_caches}/Chromium", "{xdg_cache}/chromium"),
    ),
    Browser(
        "Edge",
        CHROMIUM,
        (
            "{mac_app_support}/Microsoft Edge",
            "{xdg_config}/microsoft-edge",
            "{localappdata}/Microsoft/Edge/User Data",
        ),
        ("{mac_caches}/Microsoft Edge", "{xdg_cache}/microsoft-edge"),
    ),
    Browser(
        "Brave",
        CHROMIUM,
        (
            "{mac_app_support}/BraveSoftware/Brave-Browser",
            "{xdg_config}/BraveSoftware/Brave-Browser",
            "{localappdata}/BraveSoftware/Brave-Browser/User Data",
        ),
        (
            "{mac_caches}/BraveSoftware/Brave-Browser",
            "{xdg_cache}/BraveSoftware/Brave-Browser",
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
        ("{mac_caches}/Vivaldi", "{xdg_cache}/vivaldi"),
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
        ("{mac_caches}/com.operasoftware.Opera", "{xdg_cache}/opera"),
    ),
    Browser(
        "Arc", CHROMIUM, ("{mac_app_support}/Arc/User Data",), ("{mac_caches}/Arc",)
    ),
    Browser(
        "Firefox",
        FIREFOX,
        (
            "{mac_app_support}/Firefox/Profiles",
            "{home}/.mozilla/firefox",
            "{home}/snap/firefox/common/.mozilla/firefox",
            "{appdata}/Mozilla/Firefox/Profiles",
        ),
        (
            "{mac_caches}/Firefox",
            "{xdg_cache}/mozilla/firefox",
            "{localappdata}/Mozilla/Firefox/Profiles",
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
        (
            "{mac_caches}/librewolf",
            "{xdg_cache}/librewolf",
            "{localappdata}/librewolf/Profiles",
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
        (
            "{mac_caches}/zen",
            "{xdg_cache}/zen",
            "{localappdata}/zen/Profiles",
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


CHROMIUM_ROOT_CACHES = (
    "GrShaderCache",
    "ShaderCache",
    "GraphiteDawnCache",
    "GPUPersistentCache",
    "component_crx_cache",
    "extensions_crx_cache",
    "OptGuideOnDeviceModel",
    "OptGuideOnDeviceClassifierModel",
    "Crashpad/completed",
    "Crashpad/pending",
)
CHROMIUM_PROFILE_CACHES = (
    "Cache",
    "Code Cache",
    "GPUCache",
    "DawnCache",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
    "Media Cache",
    "Service Worker/CacheStorage",
    "Service Worker/ScriptCache",
)
FIREFOX_PROFILE_CACHES = (
    "cache2",
    "startupCache",
    "shader-cache",
    "minidumps",
    "saved-telemetry-pings",
)

# Firefox keeps history and bookmarks in one database, so it has no history.
PRIVACY: dict[str, dict[str, tuple[str, ...]]] = {
    CHROMIUM: {
        "Cookies": (
            "Cookies",
            "Cookies-journal",
            "Network/Cookies",
            "Network/Cookies-journal",
        ),
        "History": (
            "History",
            "History-journal",
            "Visited Links",
            "Top Sites",
            "Top Sites-journal",
            "Shortcuts",
            "Shortcuts-journal",
            "Network Action Predictor",
            "Network Action Predictor-journal",
        ),
        "Site Data": (
            "IndexedDB",
            "Local Storage",
            "Session Storage",
            "Service Worker",
            "File System",
            "databases",
            "WebStorage",
            "Shared Storage",
        ),
    },
    FIREFOX: {
        "Cookies": ("cookies.sqlite", "cookies.sqlite-wal", "cookies.sqlite-shm"),
        "Site Data": ("storage/default", "webappsstore.sqlite"),
    },
}

DATABASES = {
    CHROMIUM: (
        "History",
        "Favicons",
        "Web Data",
        "Top Sites",
        "Shortcuts",
        "Network Action Predictor",
        "Cookies",
        "Network/Cookies",
    ),
    FIREFOX: (
        "places.sqlite",
        "cookies.sqlite",
        "favicons.sqlite",
        "formhistory.sqlite",
        "permissions.sqlite",
        "content-prefs.sqlite",
    ),
}


def _existing(bases: list[Path], names: tuple[str, ...]) -> list[Path]:
    return [base / name for base in bases for name in names if (base / name).exists()]


def browser_profiles(
    browser: Browser, roots: Mapping[str, Path] | None = None
) -> list[Path]:
    """Every profile directory, including Opera's top-level one."""
    profiles: list[Path] = []
    for path in expand_paths(browser.paths, roots):
        if browser.engine == CHROMIUM:
            candidates = [path, *_subdirs(path)]
            profiles.extend(p for p in candidates if (p / "Preferences").is_file())
        else:
            profiles.extend(_subdirs(path))
    return profiles


def browser_caches(
    browser: Browser, roots: Mapping[str, Path] | None = None
) -> list[Path]:
    """The cache directories, and the GPU, code and model caches in profiles."""
    resolved = resolve_roots() if roots is None else roots
    found = [path for path in expand_paths(browser.caches, resolved) if path.exists()]
    profiles = browser_profiles(browser, resolved)
    if browser.engine == CHROMIUM:
        user_data = [p for p in expand_paths(browser.paths, resolved) if p.is_dir()]
        found += _existing(user_data, CHROMIUM_ROOT_CACHES)
        found += _existing(profiles, CHROMIUM_PROFILE_CACHES)
    else:
        found += _existing(profiles, FIREFOX_PROFILE_CACHES)
    return found


def browser_privacy(
    browser: Browser, roots: Mapping[str, Path] | None = None
) -> dict[str, list[Path]]:
    """Cookies, history and site data, by kind; kinds with none are left out."""
    profiles = browser_profiles(browser, roots)
    found = {
        kind: _existing(profiles, names)
        for kind, names in PRIVACY[browser.engine].items()
    }
    return {kind: paths for kind, paths in found.items() if paths}


def browser_databases(
    browser: Browser, roots: Mapping[str, Path] | None = None
) -> list[Path]:
    profiles = browser_profiles(browser, roots)
    return [p for p in _existing(profiles, DATABASES[browser.engine]) if p.is_file()]


def _free_pages(path: Path) -> int:
    try:
        with open(path, "rb") as f:
            header = f.read(100)
    except OSError:
        return 0
    if len(header) < 100 or not header.startswith(b"SQLite format 3\0"):
        return 0
    page_size = int.from_bytes(header[16:18], "big")
    if page_size == 1:
        page_size = 65536
    return int.from_bytes(header[36:40], "big") * page_size


def free_space(paths: list[Path]) -> int:
    """Bytes in the databases' free pages, read from their headers."""
    return sum(_free_pages(path) for path in paths)


def vacuum(paths: list[Path]) -> list[str]:
    """Rewrite each database without its free pages.

    A browser that's running holds a lock, so its databases are skipped.
    """
    warnings = []
    for path in paths:
        try:
            with closing(sqlite3.connect(path, timeout=1)) as db:
                db.execute("VACUUM")
        except sqlite3.Error as e:
            warnings.append(f"Skipped {path.parent.name}/{path.name}: {e}")
    return warnings
