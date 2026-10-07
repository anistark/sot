"""
Base Widget Class

Provides common functionality for all SOT widgets.
"""

from rich.panel import Panel

from .._theme import theme
from ..tui.state import KeepsState


class BaseWidget(KeepsState):
    """Base class for all SOT widgets with common functionality."""

    def __init__(self, title: str, border_style=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        t = theme()
        self.border_style = t.colors.border if border_style is None else border_style
        self.panel = Panel(
            "",
            title=t.title(title) if title else "",
            border_style=self.border_style,
            title_align="left",
            box=t.design.box,
        )

    def set_title(self, label: str, detail: str | None = None) -> None:
        self.panel.title = theme().title(label, detail)

    def render(self):
        return getattr(
            self, "panel", Panel("Loading...", title=theme().title(self.title))
        )

    def update_panel_content(self, content):
        """Update the panel content with new data."""
        self.panel.renderable = content
        self.refresh()
