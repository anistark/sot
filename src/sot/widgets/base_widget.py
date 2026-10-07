"""
Base Widget Class

Provides common functionality for all SOT widgets.
"""

from rich.text import Text

from .._theme import theme
from ..tui.state import SotWidget


def panel_title(label: str, detail: str | None = None) -> Text:
    return Text.from_markup(theme().title(label, detail))


class BaseWidget(SotWidget):
    """A framed panel; the frame comes from the theme via the ``panel`` class."""

    def __init__(self, title: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.content = ""
        if title:
            self.add_class("panel")
            self.set_title(title)

    def set_title(self, label: str, detail: str | None = None) -> None:
        self.border_title = panel_title(label, detail)

    def render(self):
        return self.content

    def update_panel_content(self, content):
        """Update the panel content with new data."""
        self.content = content
        self.refresh()
