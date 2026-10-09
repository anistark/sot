"""Side drawer showing live details for the selected item."""

from __future__ import annotations

from rich.console import Group
from rich.table import Table
from rich.text import Text

from ..._theme import theme
from ...widgets.base_widget import BaseWidget
from .. import refresh
from ..details import ACTIONABLE, details, timestamp


class DetailDrawer(BaseWidget):
    DEFAULT_CSS = """
    DetailDrawer {
        dock: right;
        width: 44;
        height: 1fr;
        display: none;
        padding: 0 1;
    }

    DetailDrawer.-open {
        display: block;
    }
    """

    STATE = ("subject",)

    def __init__(self, **kwargs):
        super().__init__(title="Details", **kwargs)
        self.subject: tuple[str, str] | None = None

    def on_mount(self) -> None:
        if self.restore_state() and self.subject:
            self.show(*self.subject)
        self.every(refresh.PROCESSES, self.redraw)

    @property
    def is_open(self) -> bool:
        return self.subject is not None

    def show(self, kind: str, key: str) -> None:
        self.subject = (kind, key)
        self.add_class("-open")
        self.redraw()

    def close(self) -> None:
        self.subject = None
        self.remove_class("-open")

    def redraw(self) -> None:
        if self.subject is None:
            return
        c = theme().colors
        kind, key = self.subject
        found = details(kind, key)
        if found is None:
            self.set_title("Details")
            self.update_panel_content(Text("No longer available", style=c.muted))
            return

        title, rows = found
        self.set_title("Details", title)
        grid = Table.grid(padding=(0, 1))
        grid.add_column(style=c.label, no_wrap=True)
        grid.add_column(style=c.text, overflow="fold")
        for label, value in rows:
            grid.add_row(label, value)

        hints = (
            "x kill · t terminate · esc close" if kind in ACTIONABLE else "esc close"
        )
        footer = Text(f"\n{hints}\nupdated {timestamp()}", style=c.muted)
        self.update_panel_content(Group(grid, footer))
