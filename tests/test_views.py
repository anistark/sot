import asyncio
import time

import pytest

from sot import _theme
from sot.bench.core import BenchmarkResult, DiskBenchmark
from sot.clean.cli import CleanTarget
from sot.tui.app import SotApp
from sot.tui.components.picker import PickerScreen
from sot.widgets.confirmation_modal import ConfirmModal


@pytest.fixture(autouse=True)
def _restore_theme():
    yield
    _theme.set_theme(_theme.DEFAULT_THEME)


def run_app(app, scenario, size=(130, 40)):
    async def main():
        async with app.run_test(size=size) as pilot:
            await scenario(app, pilot)

    asyncio.run(main())


async def wait_for(pilot, condition, timeout=10.0):
    for _ in range(int(timeout / 0.05)):
        if condition():
            return
        await pilot.pause(0.05)
    raise AssertionError("condition not met in time")


def test_number_keys_reach_the_new_views(monkeypatch):
    monkeypatch.setattr(
        "sot.tui.views.system.collect_system_info", lambda: [("System", [])]
    )
    monkeypatch.setattr("sot.tui.views.clean._get_targets", lambda: [])

    async def scenario(app, pilot):
        for key, mode in (("4", "system"), ("5", "bench"), ("6", "clean")):
            await pilot.press(key)
            await wait_for(pilot, lambda: app.screen.MODE == mode)

    run_app(SotApp(), scenario)


def test_system_view_shows_collected_sections(monkeypatch):
    sections = [("Software", [("OS", "TestOS 1")]), ("Status", [("Uptime", "1d")])]
    monkeypatch.setattr("sot.tui.views.system.collect_system_info", lambda: sections)

    async def scenario(app, pilot):
        await wait_for(pilot, lambda: app.screen.query("#section-software"))
        assert app.screen.query("#section-status")

    run_app(SotApp(start_mode="system"), scenario)


@pytest.fixture
def fake_bench(monkeypatch, tmp_path):
    disk = {
        "disk_id": "/dev/test0",
        "partitions": [{"device": "/dev/test0s1", "mountpoint": str(tmp_path)}],
        "largest_partition": {"device": "/dev/test0s1", "mountpoint": str(tmp_path)},
        "total_bytes": 10**9,
        "free_bytes": 10**8,
    }
    monkeypatch.setattr("sot.tui.views.bench.get_physical_disks", lambda: [disk])
    monkeypatch.setattr("sot.tui.views.bench.get_bench_cache_dir", lambda: tmp_path)
    monkeypatch.chdir(tmp_path)

    def fake(name):
        def run(self):
            time.sleep(0.25)
            return BenchmarkResult(test_name=name, throughput_mbps=100.0)

        return run

    for method in (
        "sequential_read_test",
        "sequential_write_test",
        "random_read_test",
        "random_write_test",
    ):
        monkeypatch.setattr(DiskBenchmark, method, fake(method))
    return tmp_path


def test_bench_runs_on_the_selected_disk_and_exports(fake_bench):
    async def scenario(app, pilot):
        screen = app.screen
        await pilot.press("minus")
        assert screen.duration == 9
        await pilot.press("enter")
        await wait_for(
            pilot, lambda: screen.running is None and len(screen.results) == 4
        )
        await pilot.press("e")
        assert list(fake_bench.glob("sot-bench-dev-test0-*.json"))

    run_app(SotApp(start_mode="bench"), scenario)


def test_escape_cancels_a_running_benchmark(fake_bench):
    async def scenario(app, pilot):
        screen = app.screen
        await pilot.press("enter")
        await wait_for(pilot, lambda: screen.running is not None)
        await pilot.press("escape")
        await wait_for(pilot, lambda: screen.running is None)
        assert len(screen.results) < 4
        assert app.screen is screen

    run_app(SotApp(start_mode="bench"), scenario)


@pytest.fixture
def cache(monkeypatch, tmp_path):
    folder = tmp_path / "cache"
    folder.mkdir()
    (folder / "blob").write_bytes(b"x" * 2048)
    target = CleanTarget("Test Cache", folder, "test files")
    monkeypatch.setattr("sot.tui.views.clean._get_targets", lambda: [target])
    return folder


def test_clean_view_asks_then_empties_the_selected_targets(cache):
    async def scenario(app, pilot):
        screen = app.screen
        await wait_for(pilot, lambda: screen.selected == {"Test Cache"})
        await pilot.press("c")
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmModal))
        await pilot.press("y")
        await wait_for(pilot, lambda: screen.report.startswith("Freed"))
        assert not any(cache.iterdir())

    run_app(SotApp(start_mode="clean"), scenario)


def test_clean_dry_run_deletes_nothing(cache):
    async def scenario(app, pilot):
        screen = app.screen
        await wait_for(pilot, lambda: screen.selected == {"Test Cache"})
        await pilot.press("d", "c")
        assert screen.report.startswith("Dry run")
        assert not isinstance(app.screen, ConfirmModal)
        assert any(cache.iterdir())

    run_app(SotApp(start_mode="clean"), scenario)


def test_disk_picker_sets_the_monitored_disk(monkeypatch):
    monkeypatch.setattr(
        "sot.disk.volumes.volume_choices", lambda: [("Root", "/"), ("Other", "/tmp")]
    )

    async def scenario(app, pilot):
        await wait_for(pilot, lambda: isinstance(app.screen, PickerScreen))
        await pilot.press("down", "enter")
        await wait_for(pilot, lambda: app.disk_mountpoint == "/tmp")

    run_app(SotApp(pick_disk=True), scenario)


def test_find_disk_matches_ids_and_mountpoints():
    from sot.bench.cli import find_disk

    disks = [
        {"disk_id": "/dev/disk3", "partitions": [{"mountpoint": "/"}]},
        {"disk_id": "/dev/sdb", "partitions": [{"mountpoint": "/data"}]},
    ]
    assert find_disk(disks, "disk3") == 0
    assert find_disk(disks, "/dev/sdb") == 1
    assert find_disk(disks, "/data") == 1
    assert find_disk(disks, "nope") == -1


@pytest.mark.parametrize(
    "argv, tty, expected",
    [
        (["clean"], True, "view:clean"),
        (["clean", "--dry-run"], True, "printed:clean"),
        (["clean"], False, "printed:clean"),
        (["bench"], True, "view:bench"),
        (["bench", "--disk", "disk3"], True, "printed:bench"),
        (["bench", "-o", "out.json"], True, "printed:bench"),
    ],
)
def test_bench_and_clean_open_their_view_only_in_a_terminal(
    monkeypatch, argv, tty, expected
):
    from sot import _app

    seen = []
    monkeypatch.setattr("sys.stdin.isatty", lambda: tty)
    monkeypatch.setattr("sys.stdout.isatty", lambda: tty)
    monkeypatch.setattr(
        "sot.clean.cli.clean_command", lambda args: seen.append("printed:clean") or 0
    )
    monkeypatch.setattr(
        "sot.bench.cli.benchmark_command",
        lambda args: seen.append("printed:bench") or 0,
    )
    monkeypatch.setattr(
        _app.SotApp, "run", lambda self: seen.append(f"view:{self.DEFAULT_MODE}")
    )
    assert _app.run(argv) == 0
    assert seen == [expected]
