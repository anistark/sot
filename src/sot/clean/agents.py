"""Cache locations for coding agents.

Cache paths are templates anchored to a named root, e.g.
``"{xdg_cache}/opencode"``. Roots are resolved at scan time from the
environment, falling back to the platform default when the variable is unset,
so a machine with a relocated cache directory is still cleaned correctly.

Entries for every platform live side by side -- the ones that don't apply
simply won't exist on disk and get filtered out before anything is shown.

Only caches, logs and scratch directories belong here. Conversation history,
sessions, credentials and config are deliberately left out, as is anything the
agent needs to keep running:

* ``~/.claude/projects`` holds the session transcripts ``claude --resume``
  reads.
* ``~/.local/share/claude/versions`` holds the installed binaries, including
  the one currently executing. Only versions nothing runs or links to go, see
  ``stale_versions``.
* ``~/.gemini/tmp`` holds gemini-cli checkpoints and history, despite its name.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Mapping, NamedTuple

import psutil


class CacheRoot(NamedTuple):
    """A base directory that cache paths are anchored to.

    ``env`` overrides ``default`` when set. A root with no ``default`` only
    exists when its variable is set -- paths anchored to it are skipped
    otherwise.
    """

    env: str | None
    default: str | None


class AgentCache(NamedTuple):
    """A coding agent and the cache paths it leaves behind."""

    name: str
    description: str
    paths: tuple[str, ...]


# Defaults are relative to the user's home directory.
CACHE_ROOTS: dict[str, CacheRoot] = {
    "home": CacheRoot(None, ""),
    # XDG base directory spec, honoured by opencode among others.
    "xdg_cache": CacheRoot("XDG_CACHE_HOME", ".cache"),
    "xdg_data": CacheRoot("XDG_DATA_HOME", ".local/share"),
    "xdg_config": CacheRoot("XDG_CONFIG_HOME", ".config"),
    # Claude Code relocates its whole state directory with this.
    "claude_config": CacheRoot("CLAUDE_CONFIG_DIR", ".claude"),
    # Developer tools.
    "cargo_home": CacheRoot("CARGO_HOME", ".cargo"),
    "rustup_home": CacheRoot("RUSTUP_HOME", ".rustup"),
    "gopath": CacheRoot("GOPATH", "go"),
    "gomodcache": CacheRoot("GOMODCACHE", None),
    "gocache": CacheRoot("GOCACHE", None),
    "gradle_home": CacheRoot("GRADLE_USER_HOME", ".gradle"),
    "bun_cache": CacheRoot("BUN_INSTALL_CACHE_DIR", None),
    "uv_cache": CacheRoot("UV_CACHE_DIR", None),
    "nvm_dir": CacheRoot("NVM_DIR", ".nvm"),
    "hf_home": CacheRoot("HF_HOME", None),
    "ollama_models": CacheRoot("OLLAMA_MODELS", None),
    # macOS.
    "mac_caches": CacheRoot(None, "Library/Caches"),
    "mac_app_support": CacheRoot(None, "Library/Application Support"),
    # Windows.
    "appdata": CacheRoot("APPDATA", "AppData/Roaming"),
    "localappdata": CacheRoot("LOCALAPPDATA", "AppData/Local"),
    "programdata": CacheRoot("PROGRAMDATA", None),
    "windir": CacheRoot("WINDIR", None),
    "systemdrive": CacheRoot("SYSTEMDRIVE", None),
    # VS Code portable mode keeps user data alongside the app instead.
    "vscode_portable": CacheRoot("VSCODE_PORTABLE", None),
}


def resolve_roots(environ: Mapping[str, str] | None = None) -> dict[str, Path]:
    """Resolve every cache root against the environment.

    ``sot`` inherits the invoking shell's environment, so exported overrides
    are picked up without shelling out. Roots whose variable is unset and that
    have no default are omitted.
    """
    env = os.environ if environ is None else environ
    home = Path.home()
    roots = {}

    for name, root in CACHE_ROOTS.items():
        value = env.get(root.env, "").strip() if root.env else ""
        if value:
            roots[name] = Path(value).expanduser()
        elif root.default is not None:
            roots[name] = home / root.default

    return roots


# VS Code style editors that host extension-based agents, in the per-platform
# locations they keep extension state under.
_EDITOR_GLOBAL_STORAGE = tuple(
    f"{{{root}}}/{editor}/User/globalStorage"
    for root in ("mac_app_support", "xdg_config", "appdata")
    for editor in ("Code", "Cursor", "VSCodium")
) + ("{vscode_portable}/user-data/User/globalStorage",)

_KILO_PATHS = ("{home}/.kilocode/cache",) + tuple(
    f"{storage}/kilocode.kilo-code/{subdir}"
    for storage in _EDITOR_GLOBAL_STORAGE
    for subdir in ("cache", "checkpoints")
)


CODING_AGENTS: tuple[AgentCache, ...] = (
    AgentCache(
        name="Claude Cache",
        description="Claude Code caches, debug logs and shell snapshots",
        paths=(
            "{claude_config}/cache",
            "{claude_config}/paste-cache",
            "{claude_config}/debug",
            "{claude_config}/shell-snapshots",
            "{claude_config}/session-env",
            "{claude_config}/statsig",
            "{xdg_cache}/claude",
            "{mac_caches}/claude-cli-nodejs",
        ),
    ),
    AgentCache(
        name="pi Cache",
        description="pi agent cache and logs",
        paths=(
            "{home}/.pi/cache",
            "{home}/.pi/logs",
            "{xdg_cache}/pi",
        ),
    ),
    AgentCache(
        name="opencode Cache",
        description="opencode cache and logs",
        paths=(
            "{xdg_cache}/opencode",
            "{xdg_data}/opencode/cache",
            "{xdg_data}/opencode/log",
            "{appdata}/opencode/cache",
        ),
    ),
    AgentCache(
        name="Codex Cache",
        description="Codex staging files, runtimes and logs",
        paths=(
            "{home}/.codex/.tmp",
            "{home}/.codex/log",
            "{xdg_cache}/codex-runtimes",
        ),
    ),
    AgentCache(
        name="Kilo Cache",
        description="Kilo Code cache and checkpoints",
        paths=_KILO_PATHS,
    ),
)


def expand_paths(
    templates: tuple[str, ...], roots: Mapping[str, Path] | None = None
) -> list[Path]:
    """Expand path templates against the resolved roots.

    Paths anchored to a root that isn't available are skipped. Templates
    holding glob wildcards expand to the paths they match.
    """
    resolved = resolve_roots() if roots is None else roots
    escaped = {name: glob.escape(str(path)) for name, path in resolved.items()}
    paths: list[Path] = []

    for template in templates:
        try:
            if any(char in template for char in "*?["):
                pattern = template.format(**escaped)
                paths.extend(Path(match) for match in sorted(glob.glob(pattern)))
            else:
                paths.append(Path(template.format(**resolved)))
        except KeyError:
            continue

    return paths


def agent_paths(
    agent: AgentCache, roots: Mapping[str, Path] | None = None
) -> list[Path]:
    """Expand an agent's templates against the resolved roots."""
    return expand_paths(agent.paths, roots)


class AgentVersions(NamedTuple):
    """An agent that keeps every binary it updated to, and its launcher."""

    name: str
    versions: tuple[str, ...]
    launcher: str


AGENT_VERSIONS: tuple[AgentVersions, ...] = (
    AgentVersions(
        "Claude Versions",
        ("{home}/.local/share/claude/versions", "{xdg_data}/claude/versions"),
        "{home}/.local/bin/claude",
    ),
    AgentVersions(
        "Cursor Agent Versions",
        ("{home}/.local/share/cursor-agent/versions",),
        "{home}/.local/bin/cursor-agent",
    ),
)


def _running_executables() -> set[Path]:
    found = set()
    for proc in psutil.process_iter(["exe"]):
        exe = proc.info.get("exe")
        if exe:
            found.add(Path(exe))
    return found


def stale_versions(
    agent: AgentVersions, roots: Mapping[str, Path] | None = None
) -> list[Path]:
    """Installed versions other than the newest, the linked and the running."""
    resolved = resolve_roots() if roots is None else roots
    launchers = expand_paths((agent.launcher,), resolved)
    linked = {path.resolve() for path in launchers if path.exists()}
    in_use = linked | _running_executables()
    stale: list[Path] = []

    for directory in dict.fromkeys(expand_paths(agent.versions, resolved)):
        try:
            versions = sorted(directory.iterdir(), key=lambda p: p.stat().st_mtime)
        except OSError:
            continue
        stale.extend(
            path
            for path in versions[:-1]
            if path.resolve() not in in_use
            and not any(exe.is_relative_to(path.resolve()) for exe in in_use)
        )

    return stale
