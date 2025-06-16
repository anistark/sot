"""
Base Widget Class

Provides common functionality for all SOT widgets.
"""

from rich import box
from rich.panel import Panel
from textual.widget import Widget


class BaseWidget(Widget):
    """Base class for all SOT widgets with common functionality."""
    
    def __init__(self, title: str, border_style="bright_black", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.border_style = border_style
        self.panel = Panel(
            "",
            title=f"[b]{title}[/]",
            border_style=self.border_style,
            title_align="left",
            box=box.SQUARE,
        )

    def render(self):
        return getattr(self, "panel", Panel("Loading...", title=f"[b]{self.title}[/]"))
    
    def update_panel_content(self, content):
        """Update the panel content with new data."""
        self.panel.renderable = content
        self.refresh()
