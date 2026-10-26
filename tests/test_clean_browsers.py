from pathlib import Path

from sot.clean import agents, browsers, cli


def _touch(path: Path, size: int = 16) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


def _names(paths: list[Path]) -> set[str]:
    return {f"{p.parent.parent.name}/{p.name}" for p in paths}


def test_chromium_keeps_the_newest_snapshot_of_each_kind(tmp_path):
    sessions = tmp_path / "Default" / "Sessions"
    for name in ("Session_100", "Session_200", "Tabs_50", "Tabs_10", "Apps_7"):
        _touch(sessions / name)

    found = browsers.chromium_sessions(tmp_path)

    assert _names(found.stale) == {"Default/Session_100", "Default/Tabs_10"}
    assert _names(found.current) == {
        "Default/Session_200",
        "Default/Tabs_50",
        "Default/Apps_7",
    }


def test_chromium_compares_stamps_as_numbers(tmp_path):
    # "Session_9" sorts after "Session_10" as text but is the older one.
    sessions = tmp_path / "Default" / "Sessions"
    _touch(sessions / "Session_9")
    _touch(sessions / "Session_10")

    found = browsers.chromium_sessions(tmp_path)

    assert [p.name for p in found.stale] == ["Session_9"]
    assert [p.name for p in found.current] == ["Session_10"]


def test_chromium_scans_every_profile_and_a_top_level_one(tmp_path):
    _touch(tmp_path / "Profile 1" / "Sessions" / "Tabs_1")
    _touch(tmp_path / "Profile 1" / "Sessions" / "Tabs_2")
    # Opera keeps its only profile at the top of the directory.
    _touch(tmp_path / "Sessions" / "Session_1")
    _touch(tmp_path / "Sessions" / "Session_2")

    found = browsers.chromium_sessions(tmp_path)

    assert {p.name for p in found.stale} == {"Tabs_1", "Session_1"}
    assert {p.name for p in found.current} == {"Tabs_2", "Session_2"}


def test_chromium_leaves_unrecognised_files_as_current(tmp_path):
    _touch(tmp_path / "Default" / "Sessions" / "Session_stamp")
    _touch(tmp_path / "Default" / "Sessions" / "notes")

    found = browsers.chromium_sessions(tmp_path)

    assert found.stale == []
    assert {p.name for p in found.current} == {"Session_stamp", "notes"}


def test_firefox_only_upgrade_backups_are_stale(tmp_path):
    profile = tmp_path / "abcd.default-release"
    _touch(profile / "sessionstore.jsonlz4")
    backups = profile / "sessionstore-backups"
    for name in (
        "recovery.jsonlz4",
        "recovery.baklz4",
        "previous.jsonlz4",
        "upgrade.jsonlz4-20250101000000",
        "upgrade.jsonlz4-20250201000000",
    ):
        _touch(backups / name)

    found = browsers.firefox_sessions(tmp_path)

    assert {p.name for p in found.stale} == {
        "upgrade.jsonlz4-20250101000000",
        "upgrade.jsonlz4-20250201000000",
    }
    assert {p.name for p in found.current} == {
        "sessionstore.jsonlz4",
        "recovery.jsonlz4",
        "recovery.baklz4",
        "previous.jsonlz4",
    }


def test_missing_profile_directories_find_nothing(tmp_path):
    for scan in (browsers.chromium_sessions, browsers.firefox_sessions):
        assert scan(tmp_path / "missing") == ([], [])


def test_browser_sessions_resolve_against_roots(tmp_path):
    # Only the one root, so the real machine's browsers stay out of it.
    roots = {"xdg_config": tmp_path}
    _touch(tmp_path / "google-chrome" / "Default" / "Sessions" / "Session_1")
    _touch(tmp_path / "google-chrome" / "Default" / "Sessions" / "Session_2")
    chrome = next(b for b in browsers.BROWSERS if b.name == "Chrome")

    found = browsers.browser_sessions(chrome, roots)

    assert [p.name for p in found.stale] == ["Session_1"]
    assert [p.name for p in found.current] == ["Session_2"]


def test_every_template_uses_a_known_root():
    roots = agents.resolve_roots({})
    known = set(agents.CACHE_ROOTS)
    for browser in browsers.BROWSERS:
        assert browser.engine in (browsers.CHROMIUM, browsers.FIREFOX)
        for template in browser.paths:
            root = template.split("}", 1)[0].lstrip("{")
            assert root in known, f"{browser.name}: unknown root {root!r}"
        for path in agents.expand_paths(browser.paths, roots):
            assert path not in roots.values(), f"{browser.name}: {path} is a root"


def _fake_chrome(monkeypatch, tmp_path) -> Path:
    sessions = tmp_path / "google-chrome" / "Default" / "Sessions"
    _touch(sessions / "Session_1", 100)
    _touch(sessions / "Session_2", 200)
    monkeypatch.setattr(
        cli,
        "resolve_roots",
        lambda: agents.resolve_roots(
            {"XDG_CONFIG_HOME": str(tmp_path), "XDG_DATA_HOME": str(tmp_path)}
        ),
    )
    # Keep the real machine's browsers out of the result.
    monkeypatch.setattr(
        cli,
        "BROWSERS",
        tuple(b for b in browsers.BROWSERS if b.name in ("Chrome", "Firefox")),
    )
    monkeypatch.setattr(agents.Path, "home", lambda: tmp_path)
    return sessions


def test_targets_hold_only_stale_sessions_by_default(monkeypatch, tmp_path):
    sessions = _fake_chrome(monkeypatch, tmp_path)

    targets = cli._get_browser_session_targets()

    assert [t.name for t in targets] == ["Chrome Sessions"]
    assert targets[0].path == [sessions / "Session_1"]
    assert cli.scan_target(targets[0])["size"] == 100


def test_forced_targets_include_current_sessions(monkeypatch, tmp_path):
    sessions = _fake_chrome(monkeypatch, tmp_path)

    (target,) = cli._get_browser_session_targets(force=True)

    assert target.path == [sessions / "Session_1", sessions / "Session_2"]
    assert "current" in target.description


def test_cleaning_removes_the_session_files_only(monkeypatch, tmp_path):
    sessions = _fake_chrome(monkeypatch, tmp_path)

    (target,) = cli._get_browser_session_targets()
    freed, warnings = cli.clean_target(target, elevated=False)

    assert (freed, warnings) == (100, [])
    assert [p.name for p in sessions.iterdir()] == ["Session_2"]


def test_browsers_without_sessions_are_left_out(monkeypatch, tmp_path):
    sessions = _fake_chrome(monkeypatch, tmp_path)
    (sessions / "Session_1").unlink()

    # The one remaining snapshot is current, so only --force has anything.
    assert cli._get_browser_session_targets() == []
    assert len(cli._get_browser_session_targets(force=True)) == 1
