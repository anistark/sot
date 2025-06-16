"""
Disk Widget

Displays disk usage and I/O statistics.
"""

import psutil
from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .base_widget import BaseWidget
from .._helpers import sizeof_fmt
from ..braille_stream import BrailleStream


class DiskWidget(BaseWidget):
    """Disk widget displaying usage and I/O statistics."""

    def __init__(self, **kwargs):
        super().__init__(title="Disk", **kwargs)

    def on_mount(self):
        self.mountpoints = [
            item.mountpoint
            for item in psutil.disk_partitions()
            if not item.device.startswith("/dev/loop")
        ]

        self.has_io_counters = False
        try:
            psutil.disk_io_counters()
        except Exception:
            pass
        else:
            self.has_io_counters = True

        if self.has_io_counters:
            self.down_box = Panel(
                "",
                title="read",
                title_align="left",
                style="aquamarine3",
                width=20,
                box=box.SQUARE,
            )
            self.up_box = Panel(
                "",
                title="write",
                title_align="left",
                style="yellow",
                width=20,
                box=box.SQUARE,
            )
            self.table = Table(expand=True, show_header=False, padding=0, box=None)
            self.table.add_column("graph", no_wrap=True, ratio=1)
            self.table.add_column("box", no_wrap=True, width=20)
            self.table.add_row("", self.down_box)
            self.table.add_row("", self.up_box)

            self.group = Group(self.table, "")

            self.last_io = None
            self.max_read_bytes_s = 0
            self.max_read_bytes_s_str = ""
            self.max_write_bytes_s = 0
            self.max_write_bytes_s_str = ""

            self.read_stream = BrailleStream(20, 5, 0.0, 1.0e6)
            self.write_stream = BrailleStream(20, 5, 0.0, 1.0e6, flipud=True)
        else:
            self.group = Group("")

        self.refresh_panel()

        self.interval_s = 2.0
        self.set_interval(self.interval_s, self.refresh_panel)

    def refresh_panel(self):
        if self.has_io_counters:
            self.refresh_io_counters()

        self.refresh_disk_usage()
        self.update_panel_content(self.group)

    def refresh_io_counters(self):
        io = psutil.disk_io_counters()

        if self.last_io is None:
            read_bytes_s_string = ""
            write_bytes_s_string = ""
        else:
            read_bytes_s = (io.read_bytes - self.last_io.read_bytes) / self.interval_s
            read_bytes_s_string = sizeof_fmt(read_bytes_s, fmt=".1f") + "/s"
            write_bytes_s = (
                io.write_bytes - self.last_io.write_bytes
            ) / self.interval_s
            write_bytes_s_string = sizeof_fmt(write_bytes_s, fmt=".1f") + "/s"

            if read_bytes_s > self.max_read_bytes_s:
                self.max_read_bytes_s = read_bytes_s
                self.max_read_bytes_s_str = sizeof_fmt(read_bytes_s, fmt=".1f") + "/s"

            if write_bytes_s > self.max_write_bytes_s:
                self.max_write_bytes_s = write_bytes_s
                self.max_write_bytes_s_str = sizeof_fmt(write_bytes_s, fmt=".1f") + "/s"

            self.read_stream.add_value(read_bytes_s)
            self.write_stream.add_value(write_bytes_s)

        self.last_io = io

        total_read_string = sizeof_fmt(io.read_bytes, sep=" ", fmt=".1f")
        total_write_string = sizeof_fmt(io.write_bytes, sep=" ", fmt=".1f")

        self.down_box.renderable = "\n".join(
            [
                f"{read_bytes_s_string}",
                f"max   {self.max_read_bytes_s_str}",
                f"total {total_read_string}",
            ]
        )
        self.up_box.renderable = "\n".join(
            [
                f"{write_bytes_s_string}",
                f"max   {self.max_write_bytes_s_str}",
                f"total {total_write_string}",
            ]
        )
        self.refresh_graphs()

    def refresh_graphs(self):
        if (
            hasattr(self.table.columns[0], "_cells")
            and len(self.table.columns[0]._cells) >= 2
        ):
            self.table.columns[0]._cells[0] = Text(
                "\n".join(self.read_stream.graph), style="aquamarine3"
            )
            self.table.columns[0]._cells[1] = Text(
                "\n".join(self.write_stream.graph), style="yellow"
            )
        else:
            if hasattr(self.table, "_clear"):
                self.table._clear()
            else:
                self.table = Table(expand=True, show_header=False, padding=0, box=None)
                self.table.add_column("graph", no_wrap=True, ratio=1)
                self.table.add_column("box", no_wrap=True, width=20)

            self.table.add_row(
                Text("\n".join(self.read_stream.graph), style="aquamarine3"),
                self.down_box,
            )
            self.table.add_row(
                Text("\n".join(self.write_stream.graph), style="yellow"), self.up_box
            )

            if len(self.group.renderables) > 0:
                self.group.renderables[0] = self.table

    def refresh_disk_usage(self):
        table = Table(box=None, show_header=False, expand=True)

        for mp in self.mountpoints:
            try:
                du = psutil.disk_usage(mp)
            except PermissionError:
                continue

            style = None
            if du.percent > 99:
                style = "red3 reverse bold"
            elif du.percent > 95:
                style = "dark_orange"

            table.add_row(
                f"[b]Free:[/] {sizeof_fmt(du.free, fmt='.1f')}",
                f"[b]Used:[/] {sizeof_fmt(du.used, fmt='.1f')}",
                f"[b]Total:[/] {sizeof_fmt(du.total, fmt='.1f')}",
                f"[b]🍕[/] {du.percent:.1f}%",
                style=style,
            )

        if len(self.group.renderables) > 1:
            self.group.renderables[-1] = table
        else:
            if len(self.group.renderables) == 1:
                self.group.renderables[0] = table
            else:
                self.group.renderables.append(table)

    async def on_resize(self, event):
        if self.has_io_counters:
            width = self.size.width - 25
            self.read_stream.reset_width(width)
            self.write_stream.reset_width(width)
            self.refresh_graphs()
