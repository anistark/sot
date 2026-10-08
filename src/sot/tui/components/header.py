"""Header shown on every view: title, view tabs, host and clock."""

from __future__ import annotations

import platform
from datetime import datetime

from rich.text import Text
from textual import events

from ..._theme import theme
from .. import keymap, refresh
from ..state import SotWidget


class SotHeader(SotWidget):
    DEFAULT_CSS = """
    SotHeader {
        dock: top;
        height: 1;
    }
    """

    def __init__(self, mode: str, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
        self.host = platform.node().split(".")[0]
        self._tabs: list[tuple[int, int, str]] = []

    def on_mount(self) -> None:
        self.every(refresh.CLOCK, self.refresh)

    def render(self) -> Text:
        t = theme()
        c = t.colors
        text = Text(no_wrap=True, overflow="crop")
        text.append(" SOT ", style=c.title_tag if t.design.title == "tag" else "bold")
        text.append("  ")

        self._tabs = []
        for n, (mode, label) in enumerate(keymap.VIEWS.items(), 1):
            tab = f" {n} {label} "
            start = len(text)
            text.append(tab, style=c.selected if mode == self.mode else c.muted)
            self._tabs.append((start, len(text), mode))
            text.append(" ")

        right = f"{self.host}  {datetime.now():%H:%M:%S} "
        text.append(" " * max(1, self.size.width - len(text) - len(right)))
        text.append(right, style=c.muted)
        return text

    async def on_click(self, event: events.Click) -> None:
        for start, end, mode in self._tabs:
            if start <= event.x < end:
                await self.app.run_action(f"switch_mode('{mode}')")
                return
