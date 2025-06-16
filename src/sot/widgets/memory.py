"""
Memory Widget

Displays memory usage information including virtual memory and swap.
"""

import psutil
from rich.console import Group
from rich.text import Text

from .base_widget import BaseWidget
from .._helpers import sizeof_fmt
from ..braille_stream import BrailleStream


class MemoryWidget(BaseWidget):
    """Memory widget displaying virtual memory and swap usage."""

    def __init__(self, **kwargs):
        super().__init__(title="Memory", **kwargs)
        self._color_list = ["yellow", "aquamarine3", "sky_blue3", "slate_blue1", "red3"]
        self.attrs = []
        self.mem_streams = []
        self.mem_total_bytes = 0

    def on_mount(self):
        mem = psutil.virtual_memory()
        self.mem_total_bytes = mem.total

        self.attrs = []
        for attr in ["free", "available", "cached", "used"]:
            if hasattr(mem, attr):
                self.attrs.append(attr)

        swap = psutil.swap_memory()
        if swap is not None:
            self.attrs.append("swap")

        maxlen = max(len(string) for string in self.attrs)
        maxlen = min(maxlen, 5)
        self.labels = [attr[:maxlen].ljust(maxlen) for attr in self.attrs]

        for attr in self.attrs:
            total = swap.total if attr == "swap" else self.mem_total_bytes
            self.mem_streams.append(BrailleStream(40, 4, 0.0, total))

        self.group = Group("", "", "", "", "")

        mem_total_string = sizeof_fmt(self.mem_total_bytes, fmt=".2f")
        self.panel.title = f"[b]Memory[/] - {mem_total_string}"

        self.refresh_table()
        self.set_interval(2.0, self.refresh_table)

    def refresh_table(self):
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        for k, (attr, label, stream, col) in enumerate(
            zip(self.attrs, self.labels, self.mem_streams, self._color_list)
        ):
            if attr == "swap":
                val = swap.used
                total = swap.total
                if total == 0:
                    total = 1
            else:
                val = getattr(mem, attr)
                total = self.mem_total_bytes

            stream.add_value(val)
            val_string = " ".join(
                [
                    label,
                    sizeof_fmt(val, fmt=".2f"),
                    f"({val / total * 100:.0f}%)",
                ]
            )
            graph = "\n".join(
                [val_string + stream.graph[0][len(val_string) :]] + stream.graph[1:]
            )
            if k < len(self.group.renderables):
                self.group.renderables[k] = Text(graph, style=col)

        self.update_panel_content(self.group)

    async def on_resize(self, event):
        for ms in self.mem_streams:
            ms.reset_width(self.size.width - 4)

        n = len(self.attrs)
        available_height = self.size.height - 2
        heights = [available_height // n] * n
        for k in range(available_height % n):
            heights[k] += 1

        for ms, h in zip(self.mem_streams, heights):
            ms.reset_height(h)

        self.refresh_table()
