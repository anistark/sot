import os
import time
from pathlib import Path

from sot.clean import cli, targets


def _touch(path: Path, size: int = 16, age_days: float = 0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    if age_days:
        stamp = time.time() - age_days * 86400
        os.utime(path, (stamp, stamp))
    return path


def test_kept_paths_are_neither_counted_nor_removed(tmp_path):
    _touch(tmp_path / "pypoetry" / "cache" / "wheel", 100)
    _touch(tmp_path / "pypoetry" / "virtualenvs" / "env" / "python", 200)
    _touch(tmp_path / "pip" / "wheel", 300)
    keep = (targets.keep_exactly(tmp_path) + "/pypoetry/virtualenvs",)

    assert targets.disk_usage(tmp_path, keep) == 400
    assert targets.empty_path(tmp_path, keep) == []

    # The kept directory's parent stays so the kept one can.
    assert (tmp_path / "pypoetry" / "virtualenvs" / "env" / "python").exists()
    assert not (tmp_path / "pypoetry" / "cache").exists()
    assert not (tmp_path / "pip").exists()


def test_age_limit_spares_recent_files_and_every_directory(tmp_path):
    _touch(tmp_path / "old.log", 100, age_days=10)
    _touch(tmp_path / "new.log", 200)
    _touch(tmp_path / "nginx" / "old.log.gz", 300, age_days=10)

    assert targets.disk_usage(tmp_path, older_than=7) == 400
    targets.empty_path(tmp_path, older_than=7)

    assert sorted(p.name for p in tmp_path.rglob("*")) == ["new.log", "nginx"]


def test_symlinks_are_removed_not_followed(tmp_path):
    outside = _touch(tmp_path / "outside" / "precious", 100)
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "link").symlink_to(outside.parent)

    assert targets.disk_usage(cache) < 100
    targets.empty_path(cache)

    assert outside.exists()
    assert list(cache.iterdir()) == []


def test_run_reports_failing_commands():
    assert targets.run(("true",)) == []
    (warning,) = targets.run(("false",))
    assert warning.startswith("false")
    (warning,) = targets.run(("sot-no-such-command",))
    assert "failed" in warning


def test_action_replaces_deleting_and_freed_is_remeasured(tmp_path):
    payload = _touch(tmp_path / "store" / "blob", 4096)

    def prune():
        payload.unlink()
        return []

    target = targets.CleanTarget("Tool Cache", payload.parent, "test", action=prune)

    freed, warnings = cli.clean_target(target, elevated=False)

    assert (freed, warnings) == (4096, [])
    assert payload.parent.is_dir()


def test_review_targets_are_never_cleaned(tmp_path):
    payload = _touch(tmp_path / "models" / "llama", 4096)
    target = targets.CleanTarget("Models", payload.parent, "test", review=True)

    freed, _ = cli.clean_target(target, elevated=True)

    assert freed == 0
    assert payload.exists()


def test_nested_targets_are_kept_out_of_their_parent(tmp_path):
    _touch(tmp_path / "Caches" / "Homebrew" / "bottle", 100)
    _touch(tmp_path / "Caches" / "other" / "blob", 200)
    parent = targets.CleanTarget("User Caches", tmp_path / "Caches", "test")
    child = targets.CleanTarget("Homebrew", tmp_path / "Caches" / "Homebrew", "test")

    parent, child = cli._separate([parent, child])

    assert cli.scan_target(parent)["size"] == 200
    assert cli.scan_target(child)["size"] == 100
    cli.clean_target(parent, elevated=False)
    assert (tmp_path / "Caches" / "Homebrew" / "bottle").exists()


def test_clashing_names_get_numbered():
    a = targets.CleanTarget("Claude Cache", Path("/a"), "test")
    b = targets.CleanTarget("Claude Cache", Path("/b"), "test")

    assert [t.name for t in cli._unique_names([a, b])] == [
        "Claude Cache",
        "Claude Cache (2)",
    ]


def test_dev_cache_uses_its_tool_unless_elevated(monkeypatch, tmp_path):
    _touch(tmp_path / "Library" / "Caches" / "Homebrew" / "bottle")
    monkeypatch.setattr(cli.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"/bin/{name}")

    def homebrew(elevated):
        targets = cli._get_dev_targets(elevated)
        return next(t for t in targets if t.name == "Homebrew Cache")

    assert homebrew(elevated=False).action is not None
    assert homebrew(elevated=True).action is None


def test_scan_targets_keeps_the_original_order(tmp_path):
    found = [
        targets.CleanTarget(name, _touch(tmp_path / name), "test")
        for name in ("b", "a", "c")
    ]

    assert list(cli.scan_targets(found)) == ["b", "a", "c"]


def test_cache_folders_keep_live_data(tmp_path):
    _touch(tmp_path / "com.apple.FontRegistry" / "fonts", 100)
    _touch(tmp_path / "ms-playwright" / "chromium-1200" / "chrome", 100)
    _touch(tmp_path / "Yarn" / "blob", 100)
    caches = cli._cache_dir("User Caches", tmp_path, "test")

    cli.clean_target(caches, elevated=False)

    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "com.apple.FontRegistry",
        "ms-playwright",
    ]
