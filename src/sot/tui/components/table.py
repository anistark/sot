"""Framed, keyed table shared by every list in the TUI."""

from __future__ import annotations

from rich.console import JustifyMethod
from rich.text import Text
from textual.widgets import DataTable

from ..._theme import theme
from ...widgets.base_widget import panel_title
from .. import keymap
from ..messages import SelectionMoved, ShowDetails
from ..state import SotWidget

Row = tuple[str, tuple]


def cell(value: object, style: str = "", justify: JustifyMethod = "left") -> Text:
    return Text(str(value), style=style, justify=justify, no_wrap=True)


class SotTable(DataTable, SotWidget, inherit_bindings=False):
    """A row table that keeps the cursor on the same row across refreshes."""

    # What the detail drawer shows for a row, see ``tui.details``.
    DETAIL_KIND: str | None = None

    BINDINGS = [*keymap.LIST]

    DEFAULT_CSS = """
    SotTable {
        height: 1fr;
        background: transparent;
    }

    SotTable > .datatable--header {
        background: transparent;
        color: $accent;
        text-style: bold;
    }

    SotTable:ansi > .datatable--header {
        background: transparent;
    }

    SotTable > .datatable--even-row {
        background: $sot-stripe;
    }
    """

    def __init__(self, title: str, **kwargs):
        super().__init__(
            cursor_type="row", zebra_stripes=theme().design.stripes, **kwargs
        )
        self.add_class("panel")
        self.label = title
        self.selected_row: str | None = None
        self.filter_text = ""
        self.set_title(title)

    def set_title(self, label: str, detail: str | None = None) -> None:
        if self.filter_text:
            filtered = f"[{theme().colors.warn}]/{self.filter_text}[/]"
            detail = f"{detail} · {filtered}" if detail else filtered
        self.border_title = panel_title(label, detail)

    def reload(self) -> None:
        raise NotImplementedError

    def set_filter(self, text: str) -> None:
        self.filter_text = text
        self.reload()

    def select_key(self, key: str) -> None:
        if key not in self.rows and self.filter_text:
            self.set_filter("")
        if key in self.rows:
            self.selected_row = key
            self.move_cursor(row=self.get_row_index(key))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.selected_row = event.row_key.value
        if self.DETAIL_KIND and self.selected_row is not None:
            self.post_message(SelectionMoved(self.DETAIL_KIND, self.selected_row))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # A click on the highlighted row, i.e. a double click.
        event.stop()
        self.action_details()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        event.stop()
        self.sort_by_column(str(event.column_key.value))

    def sort_by_column(self, key: str) -> None:
        """Sort when a column header is clicked."""

    def action_details(self) -> None:
        if self.DETAIL_KIND and self.selected_row is not None:
            self.post_message(ShowDetails(self.DETAIL_KIND, self.selected_row))

    def set_rows(self, rows: list[Row]) -> None:
        keep = self.selected_row
        if [key for key, _ in rows] == [row.key.value for row in self.ordered_rows]:
            for key, cells in rows:
                for column, value in zip(self.columns, cells):
                    if self.get_cell(key, column) != value:
                        self.update_cell(key, column, value)
            return

        scroll_y = self.scroll_y
        self.clear()
        for key, cells in rows:
            self.add_row(*cells, key=key)
        self.scroll_to(y=scroll_y, animate=False)
        if keep is not None and keep in self.rows:
            self.move_cursor(row=self.get_row_index(keep), scroll=False)
        self.selected_row = keep

    def action_first(self) -> None:
        self.move_cursor(row=0)

    def action_last(self) -> None:
        self.move_cursor(row=self.row_count - 1)
