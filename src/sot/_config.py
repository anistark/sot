"""User config (`config.toml`) and remembered state (`state.toml`)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

EXAMPLE = """\
# sot config. Every key is optional.

# theme = "cyberpunk"          # classic, cyberpunk
# default_view = "overview"    # overview, processes, disks, system, bench, clean
# net = "en0"                  # network interface on the overview
# disk = "/"                   # mountpoint on the overview

# [refresh]                    # seconds
# cpu = 2.0
# processes = 2.0

# [keymap]                     # binding id = keys, see `sot --keys`
# "sot.process.kill" = "ctrl+k"
"""


def _xdg(variable: str, fallback: str) -> Path:
    return Path(os.environ.get(variable) or Path.home() / fallback)


def config_path() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "sot" / "config.toml"


def state_path() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state") / "sot" / "state.toml"


@dataclass
class Config:
    theme: str | None = None
    default_view: str | None = None
    net: str | None = None
    disk: str | None = None
    refresh: dict[str, float] = field(default_factory=dict)
    keymap: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _read(path: Path, warnings: list[str]) -> dict:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError) as e:
        warnings.append(f"Ignoring {path}: {e}")
        return {}


def load_config(path: Path | None = None) -> Config:
    """Read the config, dropping (and reporting) anything that isn't valid."""
    from ._theme import THEMES
    from .tui import refresh
    from .tui.keymap import VIEWS

    config = Config()
    data = _read(path or config_path(), config.warnings)

    def choice(key: str, allowed) -> str | None:
        value = data.get(key)
        if value is None:
            return None
        if value not in allowed:
            config.warnings.append(f"Unknown {key} {value!r}, using the default")
            return None
        return value

    config.theme = choice("theme", THEMES)
    config.default_view = choice("default_view", VIEWS)
    for key in ("net", "disk"):
        if isinstance(data.get(key), str):
            setattr(config, key, data[key])

    for name, seconds in (data.get("refresh") or {}).items():
        valid = isinstance(seconds, (int, float)) and seconds > 0
        if hasattr(refresh, name.upper()) and valid:
            config.refresh[name.upper()] = float(seconds)
        else:
            config.warnings.append(f"Ignoring refresh.{name} = {seconds!r}")

    for binding_id, keys in (data.get("keymap") or {}).items():
        if isinstance(keys, str):
            config.keymap[binding_id] = keys
        else:
            config.warnings.append(f"Ignoring keymap.{binding_id}: keys must be text")
    return config


def apply_refresh(config: Config) -> None:
    from .tui import refresh

    for name, seconds in config.refresh.items():
        setattr(refresh, name, seconds)


def remembered_theme() -> str | None:
    value = _read(state_path(), []).get("theme")
    return value if isinstance(value, str) else None


def remember_theme(name: str) -> None:
    path = state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'theme = "{name}"\n')
    except OSError:
        pass
