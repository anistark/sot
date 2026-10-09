import asyncio
import os

import pytest
from textual.app import ComposeResult

from sot import _theme
from sot._process_utils import ProcessActionResult
from sot.blockchar_stream import BlockCharStream
from sot.tui.app import SotApp
from sot.tui.base import SotBaseApp, SotThemeProvider
from sot.tui.components.header import SotHeader
from sot.tui.components.process_table import ProcessTable
from sot.tui.components.table import SotTable, cell
from sot.tui.messages import ProcessAction
from sot.widgets.confirmation_modal import ConfirmModal


@pytest.fixture(autouse=True)
def _restore_theme():
    yield
    _theme.set_theme(_theme.DEFAULT_THEME)


def run_app(app, scenario, size=(120, 40)):
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


def _fake_action(calls):
    def run(action, pid, name):
        calls.append((action, pid))
        return ProcessActionResult(True, "done")

    return run


class Host(SotBaseApp):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def compose(self) -> ComposeResult:
        yield self.widget

    def on_mount(self) -> None:
        self.widget.focus()


def _rows(*keys):
    return [(key, (cell(key),)) for key in keys]


def test_table_keeps_the_cursor_on_the_same_row():
    table = SotTable("Things")

    async def scenario(app, pilot):
        table.add_column("Name", key="name")
        table.set_rows(_rows("a", "b", "c"))
        await pilot.press("j")
        await wait_for(pilot, lambda: table.selected_row == "b")

        table.set_rows(_rows("c", "a", "b"))
        await pilot.pause()
        assert table.cursor_row == 2
        assert table.selected_row == "b"

        table.set_rows([("c", (cell("C"),)), ("a", (cell("a"),)), ("b", (cell("b"),))])
        assert table.get_cell("c", "name").plain == "C"

    run_app(Host(table), scenario)


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


def test_sort_mode_only_accepts_sort_keys():
    table = ProcessTable(id="list")

    async def scenario(app, pilot):
        await pilot.press("o")
        assert table.sort_manager.sort_mode_active
        assert table.has_class("-alert")
        await pilot.press("x")
        assert not isinstance(app.screen, ConfirmModal)
        await pilot.press("escape")
        assert not table.sort_manager.sort_mode_active
        await pilot.press("x")
        assert isinstance(app.screen, ConfirmModal)

    run_app(Host(table), scenario)


def test_bindings_can_be_remapped_by_id():
    async def scenario(app, pilot):
        app.set_keymap({"sot.process.kill": "z"})
        await pilot.press("x")
        assert not isinstance(app.screen, ConfirmModal)
        await pilot.press("z")
        assert isinstance(app.screen, ConfirmModal)

    run_app(Host(ProcessTable(id="list")), scenario)


def test_narrow_process_table_drops_secondary_columns_first():
    table = ProcessTable(id="list")

    async def scenario(app, pilot):
        await pilot.pause()
        keys = table._layout[0]
        assert "name" in keys and "pid" in keys and "cpu" in keys
        assert "io" not in keys

    run_app(Host(table), scenario, size=(50, 20))


def test_number_keys_switch_views_and_pause_hidden_ones():
    async def scenario(app, pilot):
        cpu = app.screen.query_one("#cpu-widget")
        await pilot.press("2")
        await wait_for(pilot, lambda: app.current_mode == "processes")
        assert app.focused.id == "proc-table"
        assert cpu._paused

        await pilot.press("3")
        await wait_for(pilot, lambda: app.current_mode == "disks")
        await pilot.press("1")
        await wait_for(pilot, lambda: not cpu._paused)
        assert app.current_mode == "overview"

    run_app(SotApp(), scenario)


def test_clicking_a_header_tab_switches_view():
    async def scenario(app, pilot):
        header = app.screen.query_one(SotHeader)
        start, _, mode = header._tabs[1]
        await pilot.click(SotHeader, offset=(start + 1, 0))
        await wait_for(pilot, lambda: app.current_mode == mode)

    run_app(SotApp(), scenario)


def test_subcommands_start_on_their_view():
    async def scenario(app, pilot):
        assert app.current_mode == "processes"
        assert app.focused.id == "proc-table"

    run_app(SotApp(start_mode="processes"), scenario)


def test_theme_switch_rebuilds_the_overview_and_keeps_its_data():
    async def scenario(app, pilot):
        procs = app.screen.query_one("#procs-list")
        await pilot.press("j", "j")
        await wait_for(pilot, lambda: procs.selected_row is not None)
        selected = procs.selected_row
        cpu_stream = app.screen.query_one("#cpu-widget").cpu_total_stream

        app.theme = "cyberpunk"
        await wait_for(pilot, lambda: app.screen.query_one("#procs-list") is not procs)
        await pilot.pause()

        assert _theme.theme() is _theme.CYBERPUNK
        rebuilt = app.screen.query_one("#procs-list")
        assert rebuilt.selected_row == selected
        assert app.focused is rebuilt
        assert app.screen.query_one("#cpu-widget").cpu_total_stream is cpu_stream
        assert isinstance(cpu_stream._drawn(), BlockCharStream)

    run_app(SotApp(), scenario)


def test_hidden_views_rebuild_in_the_new_theme_when_shown():
    async def scenario(app, pilot):
        cpu = app.screen.query_one("#cpu-widget")
        await pilot.press("2")
        await wait_for(pilot, lambda: app.current_mode == "processes")
        app.theme = "cyberpunk"
        await pilot.pause()

        await pilot.press("1")
        await wait_for(pilot, lambda: app.screen.query_one("#cpu-widget") is not cpu)
        assert app.screen._built_with == "cyberpunk"

    run_app(SotApp(), scenario)


def test_theme_switch_keeps_the_selected_volume():
    async def scenario(app, pilot):
        screen = app.screen
        if len(screen.volumes) < 2:
            pytest.skip("needs two volumes")
        list_view = screen.query_one("#volume-list")
        await pilot.press("j")
        await wait_for(pilot, lambda: screen.volume_index == 1)

        app.theme = "cyberpunk"
        await wait_for(pilot, lambda: screen.query_one("#volume-list") is not list_view)
        await wait_for(pilot, lambda: screen.query_one("#volume-list").index == 1)

    run_app(SotApp(start_mode="disks"), scenario)


def test_enter_opens_a_drawer_that_follows_the_cursor():
    async def scenario(app, pilot):
        table = app.screen.query_one("#proc-table")
        drawer = app.screen.drawer
        await pilot.press("enter")
        assert drawer.subject == ("process", table.selected_row)
        await pilot.press("j")
        await wait_for(pilot, lambda: drawer.subject[1] == table.selected_row)
        await pilot.press("escape")
        assert not drawer.is_open

    run_app(SotApp(start_mode="processes"), scenario)


def test_overview_drills_down_and_escape_goes_back():
    async def scenario(app, pilot):
        procs = app.screen.query_one("#procs-list")
        await pilot.press("j")
        await wait_for(pilot, lambda: procs.selected_row is not None)
        pid = procs.selected_row
        await pilot.press("enter")
        await wait_for(pilot, lambda: app.screen.MODE == "processes")
        assert app.screen.query_one("#proc-table").selected_row == pid
        assert app.back_mode == "overview"

        await pilot.press("escape")
        await wait_for(pilot, lambda: app.current_mode == "overview")
        assert app.back_mode is None

    run_app(SotApp(), scenario)


def test_disk_panel_drills_into_the_disks_view():
    async def scenario(app, pilot):
        app.screen.query_one("#disk-widget").focus()
        await pilot.press("enter")
        await wait_for(pilot, lambda: app.current_mode == "disks")
        assert app.focused.id == "volume-list"

    run_app(SotApp(), scenario)


def test_slash_filters_the_focused_list_and_escape_clears_it():
    async def scenario(app, pilot):
        table = app.screen.query_one("#proc-table")
        total = table.row_count
        await pilot.press("slash", *str(os.getpid()))
        await wait_for(pilot, lambda: table.row_count < total)
        assert str(os.getpid()) in table.rows
        await pilot.press("escape")
        await wait_for(pilot, lambda: table.filter_text == "")
        assert app.focused is table

    run_app(SotApp(start_mode="processes"), scenario)


def test_palette_finds_a_process_and_shows_it():
    from sot.tui.commands import SotCommands

    pid = str(os.getpid())

    async def scenario(app, pilot):
        provider = SotCommands(app.screen)
        hits = [hit async for hit in provider.search(pid)]
        target = next(h for h in hits if h.help == "Show in Processes")
        target.command()
        await wait_for(pilot, lambda: app.screen.MODE == "processes")
        await wait_for(
            pilot, lambda: app.screen.query_one("#proc-table").selected_row == pid
        )

    run_app(SotApp(), scenario)


def test_header_click_sorts_by_that_column():
    table = ProcessTable(id="list")

    async def scenario(app, pilot):
        table.sort_by_column("memory")
        assert table.sort_manager.current_column().key == "memory_rss"

    run_app(Host(table), scenario)


def test_details_describe_a_live_process():
    from sot.tui.details import details

    title, rows = details("process", str(os.getpid()))
    assert dict(rows)["PID"] == str(os.getpid())
    assert details("process", "999999999") is None
