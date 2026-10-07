"""
Memory Widget

Displays memory usage information including virtual memory and swap.
"""

import psutil
from rich.console import Group

from .._helpers import sizeof_fmt
from .._theme import ThemedStream, theme
from .base_widget import BaseWidget

# Rows per memory graph, regardless of panel height.
_GRAPH_HEIGHT = 2


class MemoryWidget(BaseWidget):
    """Memory widget displaying virtual memory and swap usage."""

    STATE = ("mem_streams",)

    def __init__(self, **kwargs):
        super().__init__(title="Memory", **kwargs)
        self._color_list = theme().colors.memory
        self.attrs = []
        self.mem_streams = []
        self.mem_total_bytes = 0

    def on_mount(self):
        restored = self.restore_state()
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

        if not restored:
            for attr in self.attrs:
                total = swap.total if attr == "swap" else self.mem_total_bytes
                self.mem_streams.append(ThemedStream(40, _GRAPH_HEIGHT, 0.0, total))

        self.group = Group("", "", "", "", "")

        mem_total_string = sizeof_fmt(self.mem_total_bytes, fmt=".2f")
        self.set_title("Memory", mem_total_string)

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
            lines = [val_string + stream.graph[0][len(val_string) :]] + stream.graph[1:]
            if k < len(self.group.renderables):
                graph = theme().graph(lines, col)
                graph.stylize(col, 0, len(val_string))
                self.group.renderables[k] = graph

        self.update_panel_content(self.group)

    @property
    def panel_height(self) -> int:
        """Rows the panel needs: one graph per series plus the borders."""
        return len(self.attrs) * _GRAPH_HEIGHT + 2

    async def on_resize(self, event):
        for ms in self.mem_streams:
            ms.reset_width(self.size.width - 4)

        self.refresh_table()
