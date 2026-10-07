"""Base for every view: shared chrome, theme rebuilds, paused polling."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.screen import Screen
from textual.theme import Theme
from textual.widgets import Footer

from .._theme import THEMES, set_theme, theme
from .components.header import SotHeader
from .keymap import VIEWS
from .state import SotWidget


class SotScreen(Screen):
    MODE: ClassVar[str]

    def __init__(self) -> None:
        super().__init__()
        self.sub_title = VIEWS[self.MODE]
        self._built_with = theme().name
        self._stale = False

    def compose(self) -> ComposeResult:
        yield SotHeader(self.MODE)
        yield from self.compose_view()
        yield Footer()

    def compose_view(self) -> ComposeResult:
        raise NotImplementedError

    def on_mount(self) -> None:
        self.app.theme_changed_signal.subscribe(self, self._theme_changed)

    def _theme_changed(self, new: Theme) -> None:
        if new.name not in THEMES or new.name == self._built_with:
            return
        set_theme(new.name)
        if self.is_current:
            self.call_later(self.rebuild)
        else:
            self._stale = True

    async def rebuild(self) -> None:
        """Compose the view again in the current theme, keeping focus."""
        focused = self.focused.id if self.focused else None
        self._built_with, self._stale = theme().name, False
        await self.recompose()
        self.rebuilt()
        if focused:
            for widget in self.query(f"#{focused}"):
                widget.focus()

    def rebuilt(self) -> None:
        """Restore view state that lives outside widgets after a rebuild."""

    def on_screen_suspend(self) -> None:
        for widget in self.query(SotWidget):
            widget.pause_polling()

    def on_screen_resume(self) -> None:
        if self._stale:
            self.call_later(self.rebuild)
        for widget in self.query(SotWidget):
            widget.resume_polling()
