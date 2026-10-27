import os
import time
from pathlib import Path

from sot.clean import apps, projects, system


def _touch(path: Path, size: int = 16, age_days: float = 0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    if age_days:
        stamp = time.time() - age_days * 86400
        os.utime(path, (stamp, stamp))
    return path


def test_code_sign_clones_still_open_are_current(monkeypatch, tmp_path):
    clones = tmp_path / "X" / "com.google.Chrome.code_sign_clone"
    for name in ("code_sign_clone.aaaa", "code_sign_clone.bbbb"):
        _touch(clones / name / "Google Chrome.app.bundle" / "Info.plist")
    listing = f"p668\nn{clones}/code_sign_clone.bbbb/Google Chrome.app.bundle\n"
    monkeypatch.setattr(system, "capture", lambda *a, **k: listing)

    found = system.code_sign_clones(tmp_path)

    assert [p.name for p in found.stale] == ["code_sign_clone.aaaa"]
    assert [p.name for p in found.current] == ["code_sign_clone.bbbb"]


def test_code_sign_clones_are_all_current_without_lsof(monkeypatch, tmp_path):
    _touch(tmp_path / "X" / "a.code_sign_clone" / "code_sign_clone.aaaa" / "f")
    monkeypatch.setattr(system, "capture", lambda *a, **k: None)

    assert system.code_sign_clones(tmp_path).stale == []


def test_device_support_keeps_the_newest_two(tmp_path):
    support = tmp_path / "Library" / "Developer" / "Xcode" / "iOS DeviceSupport"
    for age, version in enumerate(("18.2", "18.1", "17.5", "16.4")):
        _touch(support / version / "Symbols" / "dyld", age_days=age)
        os.utime(support / version, (time.time() - age * 86400,) * 2)

    found = system.device_support({"home": tmp_path})

    assert sorted(p.name for p in found.stale) == ["16.4", "17.5"]
    assert sorted(p.name for p in found.current) == ["18.1", "18.2"]


def test_disabled_snap_revisions_are_found(monkeypatch):
    listing = (
        "Name   Version  Rev   Tracking       Publisher  Notes\n"
        "core   16-2.61  16928 latest/stable  canonical  core,disabled\n"
        "core   16-2.62  17200 latest/stable  canonical  core\n"
        "lxd    5.21     29351 5.21/stable    canonical  disabled\n"
    )
    monkeypatch.setattr(system, "capture", lambda *a, **k: listing)
    ran = []
    monkeypatch.setattr(system, "run", lambda *commands: ran.extend(commands) or [])

    (target,) = system.snap_target()
    target.action()

    assert ran == [
        ("snap", "remove", "core", "--revision=16928"),
        ("snap", "remove", "lxd", "--revision=29351"),
    ]


def test_privacy_specs_need_the_flag(tmp_path):
    _touch(tmp_path / "recently-used.xbel")
    roots = {"xdg_data": tmp_path}

    def names(privacy):
        return {t.name for t in system.system_targets(privacy, roots)}

    assert "Recent Items" not in names(False)
    assert "Recent Items" in names(True)


def test_electron_apps_are_found_by_their_caches(tmp_path):
    _touch(tmp_path / "Slack" / "Code Cache" / "js" / "index")
    _touch(tmp_path / "Slack" / "Cache" / "Cache_Data" / "f_0")
    _touch(tmp_path / "Slack" / "Partitions" / "team" / "Cache" / "f_0")
    _touch(tmp_path / "Slack" / "Cookies")
    _touch(tmp_path / "Notes" / "Cache" / "f_0")
    _touch(tmp_path / "google-chrome" / "GPUCache" / "data_0")

    (found,) = apps.app_caches({"xdg_config": tmp_path})

    assert found.name == "Slack"
    assert set(found.paths) == {
        tmp_path / "Slack" / "Cache",
        tmp_path / "Slack" / "Code Cache",
        tmp_path / "Slack" / "Partitions" / "team" / "Cache",
    }


def test_artifacts_need_their_marker_file(tmp_path):
    _touch(tmp_path / "app" / "package.json", age_days=30)
    _touch(tmp_path / "app" / "node_modules" / "left-pad" / "index.js", age_days=30)
    # A folder named target with no Cargo.toml beside it is someone's data.
    _touch(tmp_path / "photos" / "target" / "shot.jpg", age_days=30)
    _touch(tmp_path / "lib" / "Cargo.toml")
    _touch(tmp_path / "lib" / "target" / "debug" / "lib.rlib")
    stamp = time.time() - 30 * 86400
    for path in (tmp_path / "app").rglob("*"):
        os.utime(path, (stamp, stamp))

    found = projects.project_artifacts(tmp_path)

    assert set(found) == {"node_modules", "target"}
    assert found["node_modules"].stale == [tmp_path / "app" / "node_modules"]
    # Built just now, so the project is in use.
    assert found["target"].stale == []
    assert found["target"].current == [tmp_path / "lib" / "target"]
