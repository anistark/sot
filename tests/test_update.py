import argparse
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from sot import _app
from sot.update import cli
from sot.update import install as installs
from sot.update.install import Install


class FakeDist:
    def __init__(self, files=None, location="/env/site-packages"):
        self.files = files or {}
        self.location = Path(location)

    def read_text(self, name):
        return self.files.get(name)

    def locate_file(self, path):
        return self.location / path


@pytest.fixture
def prefix(tmp_path, monkeypatch):
    """Pretend sot runs from an empty environment under ``tmp_path``."""

    def enter(path="env", dist=None):
        root = tmp_path / path
        root.mkdir(parents=True)
        monkeypatch.setattr(installs.sys, "prefix", str(root))
        monkeypatch.setattr(
            installs.metadata, "distribution", lambda _: dist or FakeDist()
        )
        return root

    monkeypatch.setattr(installs, "DPKG_RECORD", tmp_path / "no-dpkg-record")
    return enter


LOCAL_BUILD = {"direct_url.json": json.dumps({"url": "file:///tmp/build"})}


@pytest.mark.parametrize("dist", [FakeDist(), FakeDist(LOCAL_BUILD)])
def test_homebrew_is_found_from_the_keg(prefix, dist):
    prefix("Cellar/sot/6.3.0/libexec", dist)

    assert installs.detect_install().manager == installs.HOMEBREW


def test_pip_into_homebrew_python_is_not_the_formula(prefix):
    prefix("Cellar/python@3.12/3.12.7/Frameworks/Python.framework")

    assert installs.detect_install().manager == installs.PIP


def test_system_packages_are_told_apart_by_the_dpkg_record(prefix, monkeypatch):
    root = prefix("opt/sot", FakeDist(LOCAL_BUILD))
    monkeypatch.setattr(installs, "PACKAGE_PREFIX", root)
    assert installs.detect_install().manager == installs.RPM

    record = root / "sot.list"
    record.touch()
    monkeypatch.setattr(installs, "DPKG_RECORD", record)
    assert installs.detect_install().manager == installs.DEB


def test_uvx_is_left_alone(prefix):
    prefix("uv/archive-v0/abc123")

    found = installs.detect_install()

    assert found.manager == "uvx"
    assert "uvx sot@latest" in found.blocked


@pytest.mark.parametrize(
    "cache", ["Library/Caches/pipx/abc", ".cache/pipx/abc", "pipx/.cache/abc"]
)
def test_pipx_run_is_not_a_pipx_install(prefix, cache):
    root = prefix(cache)
    (root / "pipx_metadata.json").touch()

    found = installs.detect_install()

    assert found.manager == "pipx run"
    assert found.blocked


def test_source_installs_are_left_alone(prefix):
    root = prefix("pipx/venvs/sot", FakeDist(LOCAL_BUILD))
    (root / "pipx_metadata.json").touch()

    found = installs.detect_install()

    assert found.manager == "source"
    assert "file:///tmp/build" in found.blocked


def test_running_without_an_install_counts_as_source(prefix, monkeypatch):
    prefix()

    def missing(_):
        raise installs.metadata.PackageNotFoundError

    monkeypatch.setattr(installs.metadata, "distribution", missing)

    assert installs.detect_install().blocked


def test_uv_tool_is_found_from_its_receipt(prefix):
    root = prefix(dist=FakeDist({"INSTALLER": "uv\n"}))
    (root / "uv-receipt.toml").touch()

    assert installs.detect_install().manager == installs.UV_TOOL


def test_pipx_on_the_uv_backend_is_still_pipx(prefix):
    root = prefix("pipx/venvs/sot", FakeDist({"INSTALLER": "uv\n"}))
    (root / "pipx_metadata.json").touch()

    assert installs.detect_install().manager == installs.PIPX


@pytest.mark.parametrize(
    "installer, manager",
    [("pip\n", installs.PIP), ("uv\n", installs.UV_PIP), (None, installs.PIP)],
)
def test_plain_environments_go_by_the_installer(prefix, installer, manager):
    prefix(dist=FakeDist({"INSTALLER": installer}, "/env/lib/site-packages"))

    found = installs.detect_install()

    assert found.manager == manager
    assert found.location == Path("/env/lib/site-packages").resolve()


@pytest.mark.parametrize(
    "manager, newest, expected",
    [
        (installs.UV_TOOL, True, ["uv", "tool", "install", "sot@latest"]),
        (installs.UV_TOOL, False, ["uv", "tool", "install", "sot==6.4.0"]),
        (installs.PIPX, True, ["pipx", "upgrade", "sot"]),
        (installs.PIPX, False, ["pipx", "install", "--force", "sot==6.4.0"]),
    ],
)
def test_tools_only_pin_when_staying_behind_the_newest(manager, newest, expected):
    commands = installs.upgrade_commands(Install(manager, Path("/x")), "6.4.0", newest)

    assert commands == [expected]


def test_homebrew_refreshes_the_tap_before_upgrading():
    commands = installs.upgrade_commands(
        Install(installs.HOMEBREW, Path("/x")), "7", True
    )

    assert commands == [["brew", "update"], ["brew", "upgrade", "sot"]]


def test_pip_uses_the_interpreter_running_sot(monkeypatch):
    monkeypatch.setattr(installs.sys, "executable", "/env/bin/python")

    commands = installs.upgrade_commands(
        Install(installs.PIP, Path("/x")), "6.4.0", True
    )

    assert commands == [["/env/bin/python", "-m", "pip", "install", "sot==6.4.0"]]


def test_uv_pip_targets_the_interpreter_running_sot(monkeypatch):
    monkeypatch.setattr(installs.sys, "executable", "/env/bin/python")

    commands = installs.upgrade_commands(
        Install(installs.UV_PIP, Path("/x")), "6.4.0", True
    )

    assert commands == [
        ["uv", "pip", "install", "--python", "/env/bin/python", "sot==6.4.0"]
    ]


def test_pip_stays_in_the_user_site(tmp_path, monkeypatch):
    monkeypatch.setattr(installs.site, "getusersitepackages", lambda: str(tmp_path))

    commands = installs.upgrade_commands(
        Install(installs.PIP, tmp_path.resolve()), "6.4.0", True
    )

    assert "--user" in commands[0]


@pytest.mark.parametrize(
    "manager, machine, name, tool",
    [
        (installs.DEB, "x86_64", "sot-v6.4.0-amd64.deb", ["dpkg", "-i"]),
        (installs.DEB, "aarch64", "sot-v6.4.0-arm64.deb", ["dpkg", "-i"]),
        (installs.RPM, "x86_64", "sot-v6.4.0-x86_64.rpm", ["rpm", "-U"]),
        (installs.RPM, "aarch64", "sot-v6.4.0-aarch64.rpm", ["rpm", "-U"]),
    ],
)
def test_packages_match_the_release_assets(monkeypatch, manager, machine, name, tool):
    monkeypatch.setattr(installs.platform, "machine", lambda: machine)
    monkeypatch.setattr(installs.os, "geteuid", lambda: 1000, raising=False)
    found = Install(manager, Path("/opt/sot"))

    assert installs.package_url(found, "6.4.0") == (
        f"https://github.com/anistark/sot/releases/download/v6.4.0/{name}"
    )
    assert installs.upgrade_commands(found, "6.4.0", True) == [["sudo", *tool, name]]


def test_root_needs_no_sudo(monkeypatch):
    monkeypatch.setattr(installs.os, "geteuid", lambda: 0, raising=False)

    commands = installs.upgrade_commands(
        Install(installs.DEB, Path("/x")), "6.4.0", True
    )

    assert commands[0][0] == "dpkg"


def test_only_packages_are_downloaded():
    assert installs.package_url(Install(installs.PIPX, Path("/x")), "6.4.0") is None


@pytest.mark.parametrize(
    "text, version",
    [("6.3.0", (6, 3, 0)), ("6.4", (6, 4)), ("6.4.0rc1", (6, 4, 0)), ("dev", ())],
)
def test_parse_version(text, version):
    assert cli.parse_version(text) == version


def test_fetch_releases_keeps_only_installable_final_releases(monkeypatch):
    body = {
        "releases": {
            "6.3.0": [{"yanked": False}],
            "10.0.0": [{"yanked": True}, {"yanked": False}],
            "6.4.0": [{"yanked": True}],
            "7.0.0rc1": [{"yanked": False}],
            "8.0.0": [],
        }
    }
    monkeypatch.setattr(
        cli, "urlopen", lambda *_, **__: io.BytesIO(json.dumps(body).encode())
    )

    assert sorted(cli.fetch_releases()) == [(6, 3, 0), (10, 0, 0)]


RELEASES = [(5, 9, 0), (6, 3, 0), (6, 3, 1), (6, 4, 0), (7, 0, 0), (7, 1, 0)]


@pytest.mark.parametrize(
    "current, allow_major, target",
    [
        ((6, 3, 0), False, (6, 4, 0)),
        ((6, 3, 0), True, (7, 1, 0)),
        ((6, 4, 0), False, None),
        ((7, 1, 0), True, None),
        ((8, 0, 0), True, None),
    ],
)
def test_pick_target(current, allow_major, target):
    assert cli.pick_target(current, RELEASES, allow_major) == target


@pytest.fixture
def machine(monkeypatch):
    """A pipx install of 6.3.0 with a recording stand-in for subprocess.run."""
    state = SimpleNamespace(
        install=Install(installs.PIPX, Path("/env")),
        releases=[(6, 3, 0), (6, 4, 0)],
        reports=None,
        exit_code=0,
        ran=[],
    )

    def fake_run(command, **_):
        if "--version" in command:
            return SimpleNamespace(stdout=f"│ Version:   {state.reports} │")
        state.ran.append(command)
        return SimpleNamespace(returncode=state.exit_code)

    def fake_fetch():
        return state.releases

    monkeypatch.setattr(cli, "__version__", "6.3.0")
    monkeypatch.setattr(cli, "detect_install", lambda: state.install)
    monkeypatch.setattr(cli, "fetch_releases", fake_fetch)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    return state


def _run(command, dry_run=False):
    return cli.update_command(argparse.Namespace(command=command, dry_run=dry_run))


def test_update_moves_to_the_newest_minor(machine, capsys):
    machine.reports = "6.4.0"

    assert _run("update") == 0
    assert machine.ran == [["pipx", "upgrade", "sot"]]
    assert "sot is now 6.4.0" in capsys.readouterr().out


def test_update_stays_on_the_major_and_points_at_upgrade(machine, capsys):
    machine.releases = [(6, 3, 0), (6, 4, 0), (7, 0, 0)]
    machine.reports = "6.4.0"

    assert _run("update") == 0
    assert machine.ran == [["pipx", "install", "--force", "sot==6.4.0"]]
    assert "sot upgrade" in capsys.readouterr().out


def test_update_leaves_a_new_major_to_upgrade(machine, capsys):
    machine.releases = [(6, 3, 0), (7, 0, 0)]

    assert _run("update") == 0
    assert machine.ran == []
    out = capsys.readouterr().out
    assert "Already on the newest" in out
    assert "7.0.0 is a major release" in out


def test_upgrade_crosses_major_versions(machine):
    machine.releases = [(6, 3, 0), (6, 4, 0), (7, 0, 0)]
    machine.reports = "7.0.0"

    assert _run("upgrade") == 0
    assert machine.ran == [["pipx", "upgrade", "sot"]]


def test_upgrade_takes_a_minor_release_too(machine):
    machine.reports = "6.4.0"

    assert _run("upgrade") == 0
    assert machine.ran == [["pipx", "upgrade", "sot"]]


def test_nothing_runs_when_up_to_date(machine, capsys):
    machine.releases = [(6, 3, 0)]

    assert _run("upgrade") == 0
    assert machine.ran == []
    assert "Already on the newest" in capsys.readouterr().out


def test_homebrew_cannot_stay_behind_a_new_major(machine, capsys):
    machine.install = Install(installs.HOMEBREW, Path("/env"))
    machine.releases = [(6, 3, 0), (6, 4, 0), (7, 0, 0)]

    assert _run("update") == 1
    assert machine.ran == []
    assert "sot upgrade" in capsys.readouterr().out


def test_homebrew_updates_when_the_newest_is_on_this_major(machine):
    machine.install = Install(installs.HOMEBREW, Path("/env"))
    machine.reports = "6.4.0"

    assert _run("update") == 0
    assert machine.ran == [["brew", "update"], ["brew", "upgrade", "sot"]]


def test_dry_run_shows_the_commands_and_runs_none(machine, capsys):
    assert _run("update", dry_run=True) == 0
    assert machine.ran == []
    assert "$ pipx upgrade sot" in capsys.readouterr().out


def test_blocked_installs_never_reach_pypi(machine, monkeypatch, capsys):
    machine.install = Install("source", Path("/src"), "Update the code instead.")
    monkeypatch.setattr(cli, "fetch_releases", lambda: pytest.fail("reached PyPI"))

    assert _run("update") == 1
    assert "Update the code instead." in capsys.readouterr().out


def test_unreachable_pypi_is_reported(machine, monkeypatch, capsys):
    def offline():
        raise OSError("no route to host")

    monkeypatch.setattr(cli, "fetch_releases", offline)

    assert _run("update") == 1
    assert "no route to host" in capsys.readouterr().out


def test_a_failing_manager_is_reported(machine, capsys):
    machine.exit_code = 3

    assert _run("update") == 1
    assert "failed with exit code 3" in capsys.readouterr().out


def test_a_missing_manager_is_reported(machine, monkeypatch, capsys):
    def missing(*_, **__):
        raise FileNotFoundError("pipx")

    monkeypatch.setattr(cli.subprocess, "run", missing)

    assert _run("update") == 1
    assert "Couldn't run pipx" in capsys.readouterr().out


def test_success_is_not_claimed_when_the_version_did_not_move(machine, capsys):
    machine.reports = "6.3.0"

    assert _run("update") == 1
    assert "still reports 6.3.0" in capsys.readouterr().out


def test_an_unreadable_version_does_not_fail_the_update(machine, monkeypatch, capsys):
    machine.reports = "6.4.0"
    monkeypatch.setattr(cli, "_installed_version", lambda: None)

    assert _run("update") == 0
    assert "pipx finished" in capsys.readouterr().out


def test_windows_prints_the_command_instead_of_running_it(machine, monkeypatch, capsys):
    monkeypatch.setattr(cli, "ON_WINDOWS", True)

    assert _run("update") == 1
    assert machine.ran == []
    assert "$ pipx upgrade sot" in capsys.readouterr().out


def test_package_is_downloaded_next_to_the_install_command(machine, monkeypatch):
    machine.install = Install(installs.DEB, Path("/opt/sot"))
    machine.reports = "6.4.0"
    monkeypatch.setattr(installs.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(installs.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(cli, "urlopen", lambda *_, **__: io.BytesIO(b"package"))
    seen = {}

    def fake_run(command, **kwargs):
        if "--version" in command:
            return SimpleNamespace(stdout="Version: 6.4.0")
        seen["bytes"] = Path(kwargs["cwd"], command[-1]).read_bytes()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    assert _run("update") == 0
    assert seen["bytes"] == b"package"


def test_a_missing_package_is_reported(machine, monkeypatch, capsys):
    machine.install = Install(installs.RPM, Path("/opt/sot"))
    monkeypatch.setattr(installs.os, "geteuid", lambda: 0, raising=False)

    def not_found(*_, **__):
        raise OSError("HTTP Error 404")

    monkeypatch.setattr(cli, "urlopen", not_found)

    assert _run("update") == 1
    assert machine.ran == []
    assert "Couldn't download" in capsys.readouterr().out


@pytest.mark.parametrize("command", ["update", "upgrade"])
def test_cli_routes_both_commands(monkeypatch, command):
    seen = []
    monkeypatch.setattr(cli, "update_command", lambda args: seen.append(args) or 0)

    assert _app.run([command, "--dry-run"]) == 0
    assert seen[0].command == command
    assert seen[0].dry_run
