"""Work out how sot was installed and which commands move it to a new version."""

from __future__ import annotations

import json
import os
import platform
import site
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

HOMEBREW = "Homebrew"
UV_TOOL = "uv tool"
UV_PIP = "uv pip"
PIPX = "pipx"
PIP = "pip"
DEB = "deb"
RPM = "rpm"
UVX = "uvx"
PIPX_RUN = "pipx run"

PACKAGE_PREFIX = Path("/opt/sot")
DPKG_RECORD = Path("/var/lib/dpkg/info/sot.list")
RELEASES_URL = "https://github.com/anistark/sot/releases/download"
DEB_ARCH = {"x86_64": "amd64", "aarch64": "arm64"}


@dataclass(frozen=True)
class Install:
    manager: str
    location: Path
    blocked: str | None = None


def detect_install() -> Install:
    """Identify the install running now from the environment it runs in."""
    prefix = Path(sys.prefix).resolve()

    # Both are built from a local file, so they'd pass for source installs below.
    if "/Cellar/sot/" in prefix.as_posix():
        return Install(HOMEBREW, prefix)
    if prefix == PACKAGE_PREFIX:
        return Install(DEB if DPKG_RECORD.exists() else RPM, prefix)

    if prefix.parent.name == "archive-v0":
        return Install(
            UVX, prefix, "uvx runs a cached copy. Use `uvx sot@latest` instead."
        )
    # `pipx run` environments carry the same metadata but sit outside venvs/.
    if (prefix / "pipx_metadata.json").exists() and prefix.parent.name != "venvs":
        return Install(
            PIPX_RUN, prefix, "pipx runs a cached copy. Use `pipx run sot` instead."
        )

    try:
        dist = metadata.distribution("sot")
    except metadata.PackageNotFoundError:
        source = Path(__file__).parents[2]
        return Install("source", source, f"Update the code in {source} instead.")

    origin = json.loads(dist.read_text("direct_url.json") or "{}").get("url")
    if origin:
        return Install(
            "source", prefix, f"Installed from {origin}, so update it from there."
        )

    if (prefix / "uv-receipt.toml").exists():
        return Install(UV_TOOL, prefix)
    if (prefix / "pipx_metadata.json").exists():
        return Install(PIPX, prefix)
    # pipx can install through uv as well, so this only means anything down here.
    manager = UV_PIP if (dist.read_text("INSTALLER") or "").strip() == "uv" else PIP
    return Install(manager, Path(str(dist.locate_file(""))).resolve())


def package_url(install: Install, version: str) -> str | None:
    """Where the release package lives, for installs that need one downloaded."""
    if install.manager not in (DEB, RPM):
        return None
    return f"{RELEASES_URL}/v{version}/{_package_name(install, version)}"


def upgrade_commands(install: Install, version: str, newest: bool) -> list[list[str]]:
    """The commands moving ``install`` to ``version``, the newest release if ``newest``."""
    pin = f"sot=={version}"
    if install.manager == HOMEBREW:
        return [["brew", "update"], ["brew", "upgrade", "sot"]]
    if install.manager == UV_TOOL:
        # A pin stays in uv's receipt and blocks `uv tool upgrade`; @latest clears it.
        return [["uv", "tool", "install", "sot@latest" if newest else pin]]
    if install.manager == PIPX:
        if newest:
            return [["pipx", "upgrade", "sot"]]
        return [["pipx", "install", "--force", pin]]
    if install.manager == UV_PIP:
        return [["uv", "pip", "install", "--python", sys.executable, pin]]
    if install.manager == PIP:
        user = _in_user_site(install)
        return [[sys.executable, "-m", "pip", "install", *user, pin]]

    tool = ["dpkg", "-i"] if install.manager == DEB else ["rpm", "-U"]
    sudo = [] if os.geteuid() == 0 else ["sudo"]
    return [[*sudo, *tool, _package_name(install, version)]]


def _package_name(install: Install, version: str) -> str:
    arch = platform.machine()
    if install.manager == DEB:
        arch = DEB_ARCH.get(arch, arch)
    return f"sot-v{version}-{arch}.{install.manager}"


def _in_user_site(install: Install) -> list[str]:
    user_site = Path(site.getusersitepackages()).resolve()
    return ["--user"] if install.location == user_site else []
