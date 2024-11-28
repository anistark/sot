from rich.panel import Panel
from textual.widget import Widget


class BaseWidget(Widget):
    def __init__(self, title: str, border_style="bright_black"):
        super().__init__()
        self.title = title
        self.border_style = border_style
        self.panel = Panel(
            "",
            title=f"[b]{title}[/]",
            border_style=self.border_style,
            title_align="left",
        )

    def render(self):
        return self.panel
