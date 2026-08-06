from pathlib import Path

from rich.console import Console

from sot.clean import cli

# Nothing under test cares about the output, so keep the suite quiet.
QUIET = Console(quiet=True)


def _payload(tmp_path: Path) -> Path:
    """A directory holding one 4KB file, standing in for a real cache."""
    path = tmp_path / "payload"
    path.mkdir()
    (path / "blob.bin").write_bytes(b"x" * 4096)
    return path


def _results(target: cli.CleanTarget, size: int) -> dict:
    """The scan result shape ``_clean_targets`` consumes."""
    return {target.name: {"target": target, "size": size, "exists": True}}


def test_sudo_target_is_skipped_without_elevation(tmp_path):
    payload = _payload(tmp_path)
    target = cli.CleanTarget("Sudo Target", payload, "test", requires_sudo=True)

    freed = cli._clean_targets(_results(target, 4096), QUIET, elevated=False)

    assert freed == 0
    assert (payload / "blob.bin").exists()


def test_sudo_target_is_cleaned_when_elevated(tmp_path):
    payload = _payload(tmp_path)
    target = cli.CleanTarget("Sudo Target", payload, "test", requires_sudo=True)

    freed = cli._clean_targets(_results(target, 4096), QUIET, elevated=True)

    assert freed == 4096
    # Contents go, the directory itself stays.
    assert list(payload.iterdir()) == []
    assert payload.is_dir()


def test_plain_target_ignores_the_elevation_flag(tmp_path):
    payload = _payload(tmp_path)
    target = cli.CleanTarget("Plain Target", payload, "test")

    freed = cli._clean_targets(_results(target, 4096), QUIET, elevated=False)

    assert freed == 4096
    assert list(payload.iterdir()) == []


def test_is_elevated_follows_euid(monkeypatch):
    monkeypatch.setattr(cli.os, "geteuid", lambda: 0, raising=False)
    assert cli._is_elevated()

    monkeypatch.setattr(cli.os, "geteuid", lambda: 501, raising=False)
    assert not cli._is_elevated()


def test_is_elevated_is_false_when_euid_is_unavailable(monkeypatch):
    # Windows has no geteuid, and the shell API lookup fails off Windows.
    # That must report unprivileged rather than raise.
    monkeypatch.delattr(cli.os, "geteuid", raising=False)
    assert not cli._is_elevated()


def test_macos_targets_include_install_data():
    target = next(t for t in cli._get_macos_targets() if t.name == "macOS Install Data")

    assert target.requires_sudo
    assert Path("/System/Volumes/Data/macOS Install Data") in target.path


def test_no_target_points_at_a_bare_root():
    # A target resolving to home or / would empty the whole directory.
    forbidden = {Path.home(), Path("/")}
    builders = (
        cli._get_macos_targets,
        cli._get_linux_targets,
        cli._get_windows_targets,
    )

    for build in builders:
        for target in build():
            paths = target.path if isinstance(target.path, list) else [target.path]
            for path in paths:
                assert path not in forbidden, f"{target.name}: {path} is a root"
