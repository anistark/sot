"""Widget helpers shared by every view."""

from __future__ import annotations

from typing import ClassVar

from textual.widget import Widget


class KeepsState(Widget):
    """A widget whose data survives being remounted, e.g. on a theme switch.

    Name the attributes to keep in ``STATE`` and call ``restore_state()`` at
    the start of ``on_mount``.
    """

    STATE: ClassVar[tuple[str, ...]] = ()

    def _store(self) -> dict | None:
        return getattr(self.app, "widget_state", None)

    def _state_key(self) -> str:
        return self.id or type(self).__name__

    def restore_state(self) -> bool:
        store = self._store()
        saved = store.pop(self._state_key(), None) if store is not None else None
        if not saved:
            return False
        for name, value in saved.items():
            setattr(self, name, value)
        return True

    def on_unmount(self) -> None:
        store = self._store()
        if store is not None and self.STATE:
            store[self._state_key()] = {
                name: getattr(self, name) for name in self.STATE if hasattr(self, name)
            }


class ListCursor:
    """Cursor and scrolling over a list of rows, driven by ``keymap.LIST``."""

    selected_index: int = 0
    scroll_position: int = 0
    visible_rows: int = 10

    def row_count(self) -> int:
        raise NotImplementedError

    def redraw(self) -> None:
        raise NotImplementedError

    def clamp_cursor(self) -> None:
        rows = self.row_count()
        self.selected_index = max(0, min(self.selected_index, rows - 1))
        self.scroll_position = max(
            0, min(self.scroll_position, rows - self.visible_rows)
        )

    def select(self, index: int) -> None:
        rows = self.row_count()
        if not rows:
            return
        self.selected_index = max(0, min(index, rows - 1))
        if self.selected_index < self.scroll_position:
            self.scroll_position = self.selected_index
        elif self.selected_index >= self.scroll_position + self.visible_rows:
            self.scroll_position = self.selected_index - self.visible_rows + 1
        self.redraw()

    def action_cursor_up(self) -> None:
        self.select(self.selected_index - 1)

    def action_cursor_down(self) -> None:
        self.select(self.selected_index + 1)

    def action_page_up(self) -> None:
        self.scroll_position = max(0, self.scroll_position - self.visible_rows)
        self.select(self.selected_index - self.visible_rows)

    def action_page_down(self) -> None:
        max_scroll = max(0, self.row_count() - self.visible_rows)
        self.scroll_position = min(max_scroll, self.scroll_position + self.visible_rows)
        self.select(self.selected_index + self.visible_rows)

    def action_first(self) -> None:
        self.scroll_position = 0
        self.select(0)

    def action_last(self) -> None:
        self.select(self.row_count() - 1)
