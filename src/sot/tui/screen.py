"""Base for every view: shared chrome, theme rebuilds, paused polling."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.theme import Theme
from textual.widgets import Footer

from .._theme import THEMES, set_theme, theme
from . import keymap
from .components.drawer import DetailDrawer
from .components.filter_bar import FilterBar, can_filter
from .components.header import SotHeader
from .keymap import VIEWS
from .messages import SelectionMoved, ShowDetails
from .state import SotWidget


class SotScreen(Screen):
    MODE: ClassVar[str]
    BINDINGS = [keymap.BACK, keymap.FILTER]

    DEFAULT_CSS = """
    SotScreen #body {
        height: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.sub_title = VIEWS[self.MODE]
        self._built_with = theme().name
        self._stale = False

    def compose(self) -> ComposeResult:
        yield SotHeader(self.MODE)
        with Container(id="body"):
            yield from self.compose_view()
            yield DetailDrawer(id=f"{self.MODE}-details")
        yield Footer()

    def compose_view(self) -> ComposeResult:
        raise NotImplementedError

    @property
    def drawer(self) -> DetailDrawer:
        return self.query_one(DetailDrawer)

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

    def reveal(self, target: str, key: str | None) -> None:
        """Focus ``target`` and select ``key`` in it, for drill-downs."""
        widget = self.query_one(f"#{target}")
        widget.focus()
        select = getattr(widget, "select_key", None)
        if key is not None and callable(select):
            select(key)

    def on_show_details(self, message: ShowDetails) -> None:
        if self.drawer.subject == (message.kind, message.key):
            self.drawer.close()
        else:
            self.drawer.show(message.kind, message.key)
        self.refresh_bindings()

    def on_selection_moved(self, message: SelectionMoved) -> None:
        if self.drawer.is_open:
            self.drawer.show(message.kind, message.key)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "back":
            return self.drawer.is_open or bool(getattr(self.app, "back_mode", None))
        if action == "filter":
            return can_filter(self.focused)
        return True

    async def action_back(self) -> None:
        if self.drawer.is_open:
            self.drawer.close()
            self.refresh_bindings()
            return
        back = getattr(self.app, "back_mode", None)
        if back:
            await self.app.run_action(f"switch_mode('{back}')")

    async def action_filter(self) -> None:
        target = self.focused
        if target is None or not can_filter(target):
            return
        # Mounted on first use: an Input mounted while the screen is still
        # being installed trips Textual's selection handling.
        bars = self.query(FilterBar)
        bar = bars.first() if bars else None
        if bar is None:
            bar = FilterBar(id=f"{self.MODE}-filter")
            await self.query_one("#body").mount(bar)
        bar.open(target)

    def on_screen_suspend(self) -> None:
        for widget in self.query(SotWidget):
            widget.pause_polling()

    def on_screen_resume(self) -> None:
        if self._stale:
            self.call_later(self.rebuild)
        for widget in self.query(SotWidget):
            widget.resume_polling()
