from __future__ import annotations

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from textual.widget import Widget

from .braille_stream import BrailleStream


class Sot(Widget):
    def __init__(self):
        super().__init__()

    def on_mount(self):
        self.table = Table(expand=True, show_header=False, padding=0, box=None)
        self.group = Group(self.table, "")
        self.read_stream = BrailleStream(20, 5, 0.0, 1.0e6)
        self.write_stream = BrailleStream(20, 5, 0.0, 1.0e6, flipud=True)

        self.panel = Panel(
            self.group,
            box=box.SIMPLE,
        )

    def render(self):
        return self.panel
