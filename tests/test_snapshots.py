import fake_system
import pytest

from sot import _theme
from sot.tui.app import SotApp

SIZE = (120, 40)


@pytest.fixture(autouse=True)
def _fake_machine(monkeypatch):
    fake_system.install(monkeypatch)
    yield
    _theme.set_theme(_theme.DEFAULT_THEME)


async def settle(pilot):
    await pilot.app.workers.wait_for_complete()
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
    assert snap_compare(app(mode), press=keys, terminal_size=SIZE, run_before=settle)


def test_disk_picker(snap_compare, monkeypatch):
    monkeypatch.setattr(
        "sot.disk.volumes.volume_choices",
        lambda: [("System (500 GiB, 64% used)", "/"), ("Backup (2 TiB)", "/Volumes/B")],
    )
    assert snap_compare(app(pick_disk=True), terminal_size=SIZE, run_before=settle)
