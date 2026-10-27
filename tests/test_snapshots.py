import fake_system
import pytest
from textual.widgets import DataTable

from sot import _theme
from sot.tui.app import SotApp

SIZE = (120, 40)


@pytest.fixture(autouse=True)
def _fake_machine(monkeypatch):
    fake_system.install(monkeypatch)
    yield
    _theme.set_theme(_theme.DEFAULT_THEME)


def _resizing(app) -> bool:
    return any(
        table._require_update_dimensions or table._updated_cells
        for table in app.screen.query(DataTable)
    )


async def settle(pilot):
    await pilot.app.workers.wait_for_complete()
    await pilot.pause()
    # DataTable fits its columns to new rows on idle, which a busy CI runner
    # may not reach before the screenshot.
    for _ in range(100):
        if not _resizing(pilot.app):
            break
        await pilot.pause(0.01)
    await pilot.pause()


def app(mode="overview", theme="classic", **kwargs):
    return SotApp(start_mode=mode, theme_name=theme, **kwargs)


@pytest.mark.parametrize("theme", ["classic", "cyberpunk"])
@pytest.mark.parametrize(
    "mode", ["overview", "processes", "disks", "system", "bench", "clean"]
)
def test_view(snap_compare, mode, theme):
    assert snap_compare(app(mode, theme), terminal_size=SIZE, run_before=settle)


@pytest.mark.parametrize(
    "name, mode, keys",
    [
        ("confirm_kill", "processes", ["x"]),
        ("detail_drawer", "processes", ["enter"]),
        ("filter", "processes", ["slash", "p", "o"]),
        ("sort_mode", "overview", ["o"]),
        ("help", "overview", ["question_mark"]),
    ],
)
def test_interaction(snap_compare, name, mode, keys):
    async def press(pilot):
        await settle(pilot)
        await pilot.press(*keys)
        await settle(pilot)

    assert snap_compare(app(mode), terminal_size=SIZE, run_before=press)


def test_disk_picker(snap_compare, monkeypatch):
    monkeypatch.setattr(
        "sot.disk.volumes.volume_choices",
        lambda: [("System (500 GiB, 64% used)", "/"), ("Backup (2 TiB)", "/Volumes/B")],
    )
    assert snap_compare(app(pick_disk=True), terminal_size=SIZE, run_before=settle)
