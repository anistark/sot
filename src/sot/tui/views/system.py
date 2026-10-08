"""System: what `sot info` prints, as panels, with live status."""

from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll

from ..._theme import theme
from ...info.cli import Section, collect_system_info, status_section, system_logo
from ...widgets.base_widget import BaseWidget
from .. import refresh
from ..screen import SotScreen


def _rows(rows: list[tuple[str, str]]) -> Table:
    c = theme().colors
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style=c.label, no_wrap=True)
    grid.add_column(style=c.text, overflow="fold")
    for label, value in rows:
        grid.add_row(label, value)
    return grid


class SectionPanel(BaseWidget):
    DEFAULT_CSS = """
    SectionPanel {
        height: auto;
        padding: 0 1;
    }
    """

    def __init__(self, section: Section, **kwargs):
        name, rows = section
        super().__init__(title=name, **kwargs)
        self.update_panel_content(_rows(rows))


class StatusPanel(SectionPanel):
    def __init__(self, **kwargs):
        super().__init__(status_section(), **kwargs)

    def on_mount(self) -> None:
        self.every(refresh.SYSTEM_STATUS, self.update_status)

    def update_status(self) -> None:
        self.update_panel_content(_rows(status_section()[1]))


class LogoPanel(BaseWidget):
    DEFAULT_CSS = """
    LogoPanel {
        width: auto;
        height: auto;
        padding: 1 2;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(title="", **kwargs)
        self.update_panel_content(
            Text("\n".join(system_logo()), style=theme().colors.logo)
        )


class SystemScreen(SotScreen):
    MODE = "system"

    DEFAULT_CSS = """
    SystemScreen #facts {
        width: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.sections: list[Section] | None = None

    def compose_view(self) -> ComposeResult:
        with Horizontal():
            yield LogoPanel()
            with VerticalScroll(id="facts"):
                yield from self._panels()

    def _panels(self):
        if self.sections is None:
            yield SectionPanel(("System", [("", "Collecting…")]), id="loading")
            return
        for name, rows in self.sections:
            if name == "Status":
                yield StatusPanel(id="section-status")
            elif rows:
                yield SectionPanel((name, rows), id=f"section-{name.lower()}")

    def on_mount(self) -> None:
        if self.sections is None:
            self.collect()

    @work(thread=True, exclusive=True)
    def collect(self) -> None:
        sections = collect_system_info()
        self.app.call_from_thread(self.call_later, self._collected, sections)

    async def _collected(self, sections: list[Section]) -> None:
        self.sections = sections
        facts = self.query_one("#facts")
        await facts.remove_children()
        await facts.mount_all(list(self._panels()))
