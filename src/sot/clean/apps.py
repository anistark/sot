"""Caches of Electron and other Chromium-based desktop apps.

These apps keep a Chromium cache set (``Cache``, ``Code Cache``,
``GPUCache``…) in their data directory, outside the platform cache folder.
Any data directory holding ``Code Cache`` or ``GPUCache`` counts as one, so
new apps are found without listing them. Cookies, local storage and settings
next to the caches are left alone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, NamedTuple

from .agents import expand_paths, resolve_roots
from .browsers import BROWSERS

APP_DIRS = (
    "{mac_app_support}/*",
    "{home}/Library/Containers/*/Data/Library/Application Support/*",
    "{xdg_config}/*",
    "{appdata}/*",
    "{localappdata}/*",
)

MARKERS = ("Code Cache", "GPUCache")

CACHE_DIRS = (
    "Cache",
    "Code Cache",
    "GPUCache",
    "DawnCache",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
    "GraphiteDawnCache",
    "GrShaderCache",
    "ShaderCache",
    "CachedData",
    "CachedExtensionVSIXs",
    "CachedProfilesData",
    "Crashpad/completed",
    "Crashpad/pending",
    "Service Worker/CacheStorage",
    "Service Worker/ScriptCache",
    "logs",
    "Partitions/*/Cache",
    "Partitions/*/Code Cache",
    "Partitions/*/GPUCache",
)


class AppCache(NamedTuple):
    name: str
    paths: list[Path]


def app_caches(roots: Mapping[str, Path] | None = None) -> list[AppCache]:
    """Every Chromium-based app with caches, browsers excluded."""
    resolved = resolve_roots() if roots is None else roots
    browsers = {
        path for browser in BROWSERS for path in expand_paths(browser.paths, resolved)
    }
    found = []

    for app in expand_paths(APP_DIRS, resolved):
        if app in browsers or not any((app / m).is_dir() for m in MARKERS):
            continue
        paths: list[Path] = []
        for name in CACHE_DIRS:
            if "*" in name:
                paths.extend(p for p in app.glob(name) if p.exists())
            elif (app / name).exists():
                paths.append(app / name)
        if paths:
            found.append(AppCache(app.name, paths))

    return found
