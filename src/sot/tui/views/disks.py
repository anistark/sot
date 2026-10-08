"""Disks: volume list and details."""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.timer import Timer
from textual.widgets import ListItem, ListView, Static

from ..._helpers import sizeof_fmt
from ..._theme import theme
from ...disk.volumes import get_volume_info, usage_style
from ...widgets.base_widget import BaseWidget, panel_title
from .. import refresh
from ..screen import SotScreen


def _framed(content: RenderableType) -> Panel:
    t = theme()
    return Panel(
        content, border_style=t.colors.accent, box=t.design.app_box, padding=(0, 1)
    )


def volume_details(volume: dict) -> Group:
    t = theme()
    c = t.colors
    # Build volume information table
    info_table = Table(box=None, show_header=False, expand=True, padding=(0, 1))
    info_table.add_column("Label", style=f"bold {c.accent}", width=18)
    info_table.add_column("Value", style=c.text)

    # Volume/Disk identification
    volume_name = volume["volume_name"]
    disk_id = volume["disk_id"]
    info_table.add_row("Volume Name", volume_name)
    info_table.add_row("Physical Disk", disk_id)

    # Aggregate volume usage
    usage = volume["usage"]
    info_table.add_row("Total Capacity", sizeof_fmt(usage.total, fmt=".2f"))
    info_table.add_row("Used Space", sizeof_fmt(usage.used, fmt=".2f"))
    info_table.add_row("Free Space", sizeof_fmt(usage.free, fmt=".2f"))
    info_table.add_row("Usage", f"{usage.percent:.3f}%")

    # Main disk usage bar
    bar_width = 40

    main_bar_style = usage_style(usage.percent)

    used_str = sizeof_fmt(usage.used, fmt=".1f")
    free_str = sizeof_fmt(usage.free, fmt=".1f")

    main_usage_bar = Text()
    main_usage_bar.append(f"{used_str} ", style=f"bold {c.text}")
    main_usage_bar.append_text(
        t.meter(usage.percent / 100, bar_width, main_bar_style, empty_style=c.muted)
    )
    main_usage_bar.append(f" {free_str}", style=f"bold {c.text}")

    main_percent = Text(
        f"{usage.percent:.3f}%", style=f"bold {main_bar_style}", justify="center"
    )

    # Get primary mountpoint for subtitle
    partitions = volume.get("partitions", [])
    primary_mountpoint = "/"
    if partitions and partitions[0].get("mountpoint"):
        primary_mountpoint = partitions[0]["mountpoint"]

    # Build content with partition boxes
    content_parts: list[RenderableType] = [
        Text(f"\n{volume_name}", style=f"bold {c.accent}"),
        Text(f"{primary_mountpoint}\n", style=c.muted),
        info_table,
        Text(""),
        main_usage_bar,
        main_percent,
    ]

    # I/O Statistics (aggregate from all disks)
    io_stats = volume.get("io_stats")
    if io_stats:
        content_parts.append(Text("\nI/O Statistics", style=f"bold {c.primary}"))
        io_table = Table(box=None, show_header=False, padding=(0, 1))
        io_table.add_column("Label", style=c.muted, width=12)
        io_table.add_column("Value", style=c.text)
        io_table.add_row(
            "Read",
            f"{io_stats['read_count']:,} ({sizeof_fmt(io_stats['read_bytes'], fmt='.1f')})",
        )
        io_table.add_row(
            "Write",
            f"{io_stats['write_count']:,} ({sizeof_fmt(io_stats['write_bytes'], fmt='.1f')})",
        )
        content_parts.append(io_table)

    # Partitions as compact visual boxes
    if partitions:
        content_parts.append(
            Text(f"\n{len(partitions)} Partition(s):", style=f"bold {c.primary}")
        )

        # Create rows of 2 partitions each for compact layout
        for i in range(0, len(partitions), 2):
            row_parts = []

            for j in range(2):
                if i + j >= len(partitions):
                    break

                part = partitions[i + j]
                part_usage = part["usage"]

                # Choose color based on usage
                bar_style = usage_style(part_usage.percent)

                # Build compact partition info
                part_bar_width = 10

                part_used_str = sizeof_fmt(part_usage.used, fmt=".1f")

                usage_bar = t.meter(
                    part_usage.percent / 100,
                    part_bar_width,
                    bar_style,
                    empty_style=c.muted,
                )

                # Create a compact table for this partition
                part_display = Table.grid(padding=(0, 1))
                part_display.add_column(style=f"bold {c.accent}", justify="left")
                part_display.add_row(f"[bold]{part['partition_id']}[/bold]")
                part_display.add_row(f"[{c.muted}]{part['mountpoint']}[/]")
                part_display.add_row(
                    f"{part_used_str} / {sizeof_fmt(part_usage.total, fmt='.1f')}"
                )
                part_display.add_row(usage_bar)
                part_display.add_row(
                    f"[{bar_style}]{part_usage.percent:.3f}%[/{bar_style}]"
                )

                row_parts.append(part_display)

            # Create a row with the partitions side by side
            if len(row_parts) == 2:
                row_table = Table.grid(expand=True)
                row_table.add_column(ratio=1)
                row_table.add_column(ratio=1)
                row_table.add_row(
                    _framed(row_parts[0]),
                    _framed(row_parts[1]),
                )
                content_parts.append(row_table)
            elif len(row_parts) == 1:
                content_parts.append(_framed(row_parts[0]))

    return Group(*content_parts)


class VolumeItem(ListItem):
    def __init__(self, volume: dict) -> None:
        usage = volume["usage"]
        c = theme().colors
        label = Text()
        label.append(f"{volume['volume_name']} ", style=f"bold {c.text}")
        used = sizeof_fmt(usage.used, fmt=".1f", sep="")
        total = sizeof_fmt(usage.total, fmt=".1f", sep="")
        label.append(f"\n  {used}/{total} ", style=c.muted)
        label.append(f"({usage.percent:.3f}%)", style=usage_style(usage.percent))
        super().__init__(Static(label))
        self.volume = volume


class VolumeList(ListView):
    BINDINGS = [
        Binding("up,k", "cursor_up", "Up", show=False, id="sot.list.up"),
        Binding("down,j", "cursor_down", "Down", show=False, id="sot.list.down"),
    ]

    class FilterChanged(Message):
        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    @property
    def filter_text(self) -> str:
        return getattr(self.screen, "volume_filter", "")

    def set_filter(self, text: str) -> None:
        self.post_message(self.FilterChanged(text))


def _volume_text(volume: dict) -> str:
    mountpoints = " ".join(p.get("mountpoint") or "" for p in volume["partitions"])
    return f"{volume['volume_name']} {volume['disk_id']} {mountpoints}".lower()


def _holds(volume: dict, key: str) -> bool:
    return key == volume["disk_id"] or any(
        p.get("mountpoint") == key for p in volume["partitions"]
    )


class VolumeInfo(BaseWidget):
    def __init__(self, **kwargs):
        super().__init__(title="Volume Information", **kwargs)

    def show(self, volume: dict | None) -> None:
        if volume is None:
            self.update_panel_content("Select a volume to view information")
        else:
            self.update_panel_content(volume_details(volume))


class DisksScreen(SotScreen):
    MODE = "disks"

    DEFAULT_CSS = """
    DisksScreen #volume-list {
        width: 40;
        height: 1fr;
    }

    DisksScreen #volume-list > ListItem {
        padding: 1;
    }

    DisksScreen #volume-info {
        width: 1fr;
        height: 1fr;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.volumes: list[dict] = []
        self.volume_index = 0
        self.volume_filter = ""
        self._poll: Timer | None = None

    def compose_view(self) -> ComposeResult:
        with Horizontal():
            volume_list = VolumeList(id="volume-list", classes="panel")
            volume_list.border_title = panel_title("Volumes")
            yield volume_list
            yield VolumeInfo(id="volume-info")

    def on_mount(self) -> None:
        self.refresh_volumes()
        self._poll = self.set_interval(refresh.VOLUMES, self.refresh_volumes)
        self.query_one("#volume-list").focus()

    def rebuilt(self) -> None:
        self.refresh_volumes()

    def on_screen_suspend(self) -> None:
        if self._poll is not None:
            self._poll.pause()

    def on_screen_resume(self) -> None:
        if self._poll is not None:
            self.refresh_volumes()
            self._poll.resume()

    def refresh_volumes(self) -> None:
        self.volumes = get_volume_info()
        if self.volume_filter:
            text = self.volume_filter.lower()
            self.volumes = [v for v in self.volumes if text in _volume_text(v)]
        volume_list = self.query_one("#volume-list", VolumeList)
        c = theme().colors
        filtered = f"[{c.warn}]/{self.volume_filter}[/]" if self.volume_filter else None
        volume_list.border_title = panel_title("Volumes", filtered)
        index = min(self.volume_index, max(0, len(self.volumes) - 1))
        volume_list.clear()
        volume_list.extend(VolumeItem(volume) for volume in self.volumes)
        if self.volumes:
            volume_list.index = index
        self.show_volume(index)

    def show_volume(self, index: int) -> None:
        volume = self.volumes[index] if 0 <= index < len(self.volumes) else None
        self.query_one("#volume-info", VolumeInfo).show(volume)

    def on_volume_list_filter_changed(self, message: VolumeList.FilterChanged) -> None:
        self.volume_filter = message.text
        self.volume_index = 0
        self.refresh_volumes()

    def reveal(self, target: str, key: str | None) -> None:
        if key is not None:
            if not any(_holds(v, key) for v in self.volumes) and self.volume_filter:
                self.volume_filter = ""
                self.refresh_volumes()
            for index, volume in enumerate(self.volumes):
                if _holds(volume, key):
                    self.volume_index = index
                    self.refresh_volumes()
                    break
        self.query_one("#volume-list").focus()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.index is not None:
            self.volume_index = event.list_view.index
            self.show_volume(self.volume_index)
