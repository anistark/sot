"""Inline filter for the focused list."""

from __future__ import annotations

from textual.widget import Widget
from textual.widgets import Input

from .. import keymap


def can_filter(widget: Widget | None) -> bool:
    return callable(getattr(widget, "set_filter", None))


class FilterBar(Input):
    DEFAULT_CSS = """
    FilterBar, FilterBar:focus {
        dock: bottom;
        display: none;
        border: none;
        height: 1;
        padding: 0 1;
    }

    FilterBar.-open {
        display: block;
    }
    """

    BINDINGS = [keymap.FILTER_CLEAR]

    def __init__(self, **kwargs):
        super().__init__(placeholder="/ filter…", **kwargs)
        self.target: Widget | None = None

    def open(self, target: Widget) -> None:
        self.target = target
        self.value = getattr(target, "filter_text", "")
        self.add_class("-open")
        self.focus()

    def _close(self) -> None:
        self.remove_class("-open")
        if self.target is not None:
            self.target.focus()

    def _apply(self, text: str) -> None:
        if can_filter(self.target):
            getattr(self.target, "set_filter")(text)

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        self._apply(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._close()

    def action_clear(self) -> None:
        self._apply("")
        self._close()
