import asyncio

import pytest
from textual.app import ComposeResult

from sot import _theme
from sot._process_utils import ProcessActionResult
from sot.blockchar_stream import BlockCharStream
from sot.ps.ps_tui import ProcessListPanel
from sot.tui.base import SotBaseApp, SotThemeProvider
from sot.tui.messages import ProcessAction
from sot.tui.state import ListCursor
from sot.widgets.confirmation_modal import ConfirmModal


@pytest.fixture(autouse=True)
def _restore_theme():
    yield
    _theme.set_theme(_theme.DEFAULT_THEME)


def run_app(app, scenario):
    async def main():
        async with app.run_test(size=(120, 40)) as pilot:
            await scenario(app, pilot)

    asyncio.run(main())


async def wait_for(pilot, condition, timeout=10.0):
    for _ in range(int(timeout / 0.05)):
        if condition():
            return
        await pilot.pause(0.05)
    raise AssertionError("condition not met in time")


class Rows(ListCursor):
    def __init__(self, rows, visible=3):
        self.rows = rows
        self.visible_rows = visible
        self.selected_index = 0
        self.scroll_position = 0

    def row_count(self):
        return self.rows

    def redraw(self):
        pass


def test_list_cursor_scrolls_with_the_selection():
    rows = Rows(10)
    for _ in range(4):
        rows.action_cursor_down()
    assert (rows.selected_index, rows.scroll_position) == (4, 2)

    rows.action_page_down()
    assert (rows.selected_index, rows.scroll_position) == (7, 5)

    rows.action_last()
    assert (rows.selected_index, rows.scroll_position) == (9, 7)

    rows.action_page_up()
    assert (rows.selected_index, rows.scroll_position) == (6, 4)

    rows.action_first()
    rows.action_cursor_up()
    assert (rows.selected_index, rows.scroll_position) == (0, 0)


def test_list_cursor_clamps_when_rows_shrink():
    rows = Rows(10)
    rows.action_last()
    rows.rows = 4
    rows.clamp_cursor()
    assert (rows.selected_index, rows.scroll_position) == (3, 1)


class ProcessHost(SotBaseApp):
    def compose(self) -> ComposeResult:
        yield ProcessListPanel(id="list")

    def on_mount(self) -> None:
        self.query_one("#list").focus()


def _fake_action(calls):
    def run(action, pid, name):
        calls.append((action, pid))
        return ProcessActionResult(True, "done")

    return run


def test_theme_picker_only_lists_sot_themes():
    async def scenario(app, pilot):
        names = {name for name, _ in SotThemeProvider(app.screen).commands}
        assert names == set(_theme.THEMES)

    run_app(SotBaseApp(), scenario)


def test_process_actions_wait_for_confirmation(monkeypatch):
    calls = []
    monkeypatch.setattr("sot.tui.base.run_process_action", _fake_action(calls))

    async def scenario(app, pilot):
        app.post_message(ProcessAction("kill", {"pid": 4242, "name": "demo"}))
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmModal))
        await pilot.press("escape")
        assert not isinstance(app.screen, ConfirmModal)
        assert calls == []

        app.post_message(ProcessAction("terminate", {"pid": 4242, "name": "demo"}))
        await wait_for(pilot, lambda: isinstance(app.screen, ConfirmModal))
        await pilot.press("y")
        assert calls == [("terminate", 4242)]

    run_app(SotBaseApp(), scenario)


def test_sort_mode_only_accepts_sort_keys(monkeypatch):
    calls = []
    monkeypatch.setattr("sot.tui.base.run_process_action", _fake_action(calls))

    async def scenario(app, pilot):
        panel = app.query_one("#list", ProcessListPanel)
        await pilot.press("o")
        assert panel.sort_manager.sort_mode_active
        await pilot.press("k")
        assert not isinstance(app.screen, ConfirmModal)
        await pilot.press("escape")
        assert not panel.sort_manager.sort_mode_active
        await pilot.press("k")
        assert isinstance(app.screen, ConfirmModal)

    run_app(ProcessHost(), scenario)


def test_bindings_can_be_remapped_by_id():
    async def scenario(app, pilot):
        app.set_keymap({"sot.process.kill": "x"})
        await pilot.press("k")
        assert not isinstance(app.screen, ConfirmModal)
        await pilot.press("x")
        assert isinstance(app.screen, ConfirmModal)

    run_app(ProcessHost(), scenario)


def test_theme_switch_rebuilds_the_dashboard_and_keeps_its_data():
    from sot._app import SotApp

    async def scenario(app, pilot):
        procs = app.query_one("#procs-list")
        await pilot.press("down", "down")
        cpu_stream = app.query_one("#cpu-widget").cpu_total_stream

        app.theme = "cyberpunk"
        await wait_for(pilot, lambda: app.query_one("#procs-list") is not procs)
        await pilot.pause()

        assert _theme.theme() is _theme.CYBERPUNK
        assert app.has_class("-theme-cyberpunk")
        rebuilt = app.query_one("#procs-list")
        assert rebuilt.selected_index == 2
        assert app.focused is rebuilt
        assert app.query_one("#cpu-widget").cpu_total_stream is cpu_stream
        assert isinstance(cpu_stream._drawn(), BlockCharStream)

    run_app(SotApp(), scenario)


def test_theme_switch_keeps_the_selected_volume():
    from sot.disk.disk_tui import DiskTUIApp

    async def scenario(app, pilot):
        if len(app.volumes) < 2:
            pytest.skip("needs two volumes")
        list_view = app.query_one("#volume-list")
        await pilot.press("down")
        await wait_for(pilot, lambda: app.volume_index == 1)

        app.theme = "cyberpunk"
        await wait_for(pilot, lambda: app.query_one("#volume-list") is not list_view)
        await wait_for(pilot, lambda: app.query_one("#volume-list").index == 1)

    run_app(DiskTUIApp(), scenario)
