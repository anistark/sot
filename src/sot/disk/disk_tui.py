"""Disk TUI - Interactive disk information viewer."""

from __future__ import annotations

import platform
from typing import List, Dict, Optional

import psutil
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, ListItem, ListView, Static

from .._helpers import sizeof_fmt
from ..__about__ import __version__


class VolumeListItem(ListItem):
    """Custom ListItem to store volume information."""

    def __init__(self, volume_info: Dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.volume_info = volume_info


class PartitionBox(Static):
    """A compact box displaying a single partition's information."""

    def __init__(self, partition_info: Dict, partition_num: int, **kwargs):
        super().__init__(**kwargs)
        self.partition_info = partition_info
        self.partition_num = partition_num

    def on_mount(self):
        """Render the partition box content."""
        self.refresh_content()

    def refresh_content(self):
        """Update partition box display."""
        part = self.partition_info
        part_usage = part["usage"]

        # Calculate bar width and blocks
        part_bar_width = 12
        part_used_blocks = int((part_usage.percent / 100) * part_bar_width)
        part_free_blocks = part_bar_width - part_used_blocks

        # Choose color based on usage
        if part_usage.percent > 95:
            bar_style = "red"
        elif part_usage.percent > 80:
            bar_style = "yellow"
        else:
            bar_style = "green"

        # Build partition box content - compact
        part_lines = []
        part_lines.append(Text(f"Device: {part['device']}", style="dim"))
        part_lines.append(Text(f"Mount: {part['mountpoint']}", style="white"))
        part_lines.append(Text(f"FS: {part['fstype']}", style="dim"))
        part_lines.append(Text(f"Size: {sizeof_fmt(part_usage.total, fmt='.1f')}", style="white"))
        part_lines.append(Text(""))

        # Visual usage bar with numbers on sides
        part_used_str = sizeof_fmt(part_usage.used, fmt=".1f")
        part_free_str = sizeof_fmt(part_usage.free, fmt=".1f")
        percent_str = f"{part_usage.percent:.3f}%"

        usage_line = Text()
        usage_line.append(f"{part_used_str} ", style="bold white")
        usage_line.append("█" * part_used_blocks, style=bar_style)
        usage_line.append("░" * part_free_blocks, style="dim")
        usage_line.append(f" {part_free_str}", style="bold white")
        part_lines.append(usage_line)

        percent_line = Text(f"{percent_str}", style=f"bold {bar_style}", justify="center")
        part_lines.append(percent_line)

        # Create partition panel
        partition_content = Group(*part_lines)
        self.update(
            Panel(
                partition_content,
                title=f"[bold]{part['partition_id']}[/bold]",
                border_style=bar_style,
                padding=(0, 1),
            )
        )


class VolumeInfoPanel(Static):
    """Panel displaying detailed volume and disk information."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_volume = None

    def update_volume_info(self, volume_info: Dict):
        """Update the panel with volume information."""
        self.current_volume = volume_info
        self.refresh_content()

    def refresh_content(self):
        """Refresh the volume information display."""
        if not self.current_volume:
            self.update("Select a volume to view information")
            return

        # Build volume information table
        info_table = Table(box=None, show_header=False, expand=True, padding=(0, 1))
        info_table.add_column("Label", style="bold cyan", width=18)
        info_table.add_column("Value", style="white")

        # Volume/Disk identification
        volume_name = self.current_volume["volume_name"]
        disk_id = self.current_volume["disk_id"]
        info_table.add_row("Volume Name", volume_name)
        info_table.add_row("Physical Disk", disk_id)

        # Aggregate volume usage
        usage = self.current_volume["usage"]
        info_table.add_row("Total Capacity", sizeof_fmt(usage.total, fmt=".2f"))
        info_table.add_row("Used Space", sizeof_fmt(usage.used, fmt=".2f"))
        info_table.add_row("Free Space", sizeof_fmt(usage.free, fmt=".2f"))
        info_table.add_row("Usage", f"{usage.percent:.3f}%")

        # Main disk usage bar
        bar_width = 40
        used_blocks = int((usage.percent / 100) * bar_width)
        free_blocks = bar_width - used_blocks

        if usage.percent > 95:
            main_bar_style = "red"
        elif usage.percent > 80:
            main_bar_style = "yellow"
        else:
            main_bar_style = "green"

        used_str = sizeof_fmt(usage.used, fmt=".1f")
        free_str = sizeof_fmt(usage.free, fmt=".1f")

        main_usage_bar = Text()
        main_usage_bar.append(f"{used_str} ", style="bold white")
        main_usage_bar.append("█" * used_blocks, style=main_bar_style)
        main_usage_bar.append("░" * free_blocks, style="dim")
        main_usage_bar.append(f" {free_str}", style="bold white")

        main_percent = Text(f"{usage.percent:.3f}%", style=f"bold {main_bar_style}", justify="center")

        # Get primary mountpoint for subtitle
        partitions = self.current_volume.get("partitions", [])
        primary_mountpoint = "/"
        if partitions and partitions[0].get("mountpoint"):
            primary_mountpoint = partitions[0]["mountpoint"]

        # Build content with partition boxes
        content_parts = [
            Text(f"\n{volume_name}", style="bold bright_cyan"),
            Text(f"{primary_mountpoint}\n", style="dim"),
            info_table,
            Text(""),
            main_usage_bar,
            main_percent,
        ]

        # I/O Statistics (aggregate from all disks)
        io_stats = self.current_volume.get("io_stats")
        if io_stats:
            content_parts.append(Text("\nI/O Statistics", style="bold yellow"))
            io_table = Table(box=None, show_header=False, padding=(0, 1))
            io_table.add_column("Label", style="dim", width=12)
            io_table.add_column("Value", style="white")
            io_table.add_row("Read", f"{io_stats['read_count']:,} ({sizeof_fmt(io_stats['read_bytes'], fmt='.1f')})")
            io_table.add_row("Write", f"{io_stats['write_count']:,} ({sizeof_fmt(io_stats['write_bytes'], fmt='.1f')})")
            content_parts.append(io_table)

        # Partitions as compact visual boxes
        if partitions:
            content_parts.append(Text(f"\n{len(partitions)} Partition(s):", style="bold yellow"))

            # Create rows of 2 partitions each for compact layout
            for i in range(0, len(partitions), 2):
                row_parts = []

                for j in range(2):
                    if i + j >= len(partitions):
                        break

                    part = partitions[i + j]
                    part_usage = part["usage"]

                    # Choose color based on usage
                    if part_usage.percent > 95:
                        bar_style = "red"
                    elif part_usage.percent > 80:
                        bar_style = "yellow"
                    else:
                        bar_style = "green"

                    # Build compact partition info
                    part_bar_width = 10
                    part_used_blocks = int((part_usage.percent / 100) * part_bar_width)
                    part_free_blocks = part_bar_width - part_used_blocks

                    part_used_str = sizeof_fmt(part_usage.used, fmt=".1f")
                    part_free_str = sizeof_fmt(part_usage.free, fmt=".1f")

                    usage_bar = Text()
                    usage_bar.append("█" * part_used_blocks, style=bar_style)
                    usage_bar.append("░" * part_free_blocks, style="dim")

                    # Create a compact table for this partition
                    part_display = Table.grid(padding=(0, 1))
                    part_display.add_column(style="bold cyan", justify="left")
                    part_display.add_row(f"[bold]{part['partition_id']}[/bold]")
                    part_display.add_row(f"[dim]{part['mountpoint']}[/dim]")
                    part_display.add_row(f"{part_used_str} / {sizeof_fmt(part_usage.total, fmt='.1f')}")
                    part_display.add_row(usage_bar)
                    part_display.add_row(f"[{bar_style}]{part_usage.percent:.3f}%[/{bar_style}]")

                    row_parts.append(part_display)

                # Create a row with the partitions side by side
                if len(row_parts) == 2:
                    row_table = Table.grid(expand=True)
                    row_table.add_column(ratio=1)
                    row_table.add_column(ratio=1)
                    row_table.add_row(
                        Panel(row_parts[0], border_style="cyan", padding=(0, 1)),
                        Panel(row_parts[1], border_style="cyan", padding=(0, 1))
                    )
                    content_parts.append(row_table)
                elif len(row_parts) == 1:
                    content_parts.append(Panel(row_parts[0], border_style="cyan", padding=(0, 1)))

        content = Group(*content_parts)
        self.update(Panel(content, title="Volume Information", border_style="cyan"))

    def on_mount(self):
        """Set interval to refresh volume info."""
        self.set_interval(2.0, self.refresh_content)


class DiskTUIApp(App):
    """SOT Disk TUI Application."""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 40;
        background: $panel;
        border-right: solid $primary;
        padding: 1;
    }

    #main-panel {
        width: 1fr;
        padding: 1;
    }

    ListView {
        height: 1fr;
        border: solid $primary;
    }

    ListView > ListItem {
        padding: 1;
    }

    ListView > ListItem.--highlight {
        background: $accent;
    }

    VolumeInfoPanel {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("up,k", "cursor_up", "Move Up"),
        ("down,j", "cursor_down", "Move Down"),
    ]

    def __init__(self):
        super().__init__()
        self.volumes = []

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()

        with Horizontal():
            # Left sidebar - volume list
            with Vertical(id="sidebar"):
                yield ListView(id="volume-list")

            # Main panel - volume info
            yield VolumeInfoPanel(id="main-panel")

        yield Footer()

    def on_mount(self):
        """Initialize the app when mounted."""
        self.title = "SOT Disk Viewer"
        self.sub_title = f"v{__version__}"

        # Populate volume list
        self.refresh_volume_list()

        # Set interval to refresh volume list
        self.set_interval(5.0, self.refresh_volume_list)

    def get_volume_info(self) -> List[Dict]:
        """Get information about all volumes, grouping by physical disk."""
        import re

        # First, collect all partitions by physical disk
        disks_dict = {}
        partitions_list = [
            p for p in psutil.disk_partitions() if not p.device.startswith("/dev/loop")
        ]

        for partition in partitions_list:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_id = self._extract_disk_id(partition.device)

                partition_info = {
                    "partition_id": self._extract_partition_id(partition.device),
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "opts": partition.opts,
                    "usage": usage,
                }

                if disk_id not in disks_dict:
                    disks_dict[disk_id] = {
                        "disk_id": disk_id,
                        "partitions": [],
                        "total_size": 0,
                        "total_used": 0,
                        "total_free": 0,
                    }

                disks_dict[disk_id]["partitions"].append(partition_info)
                # For APFS containers, volumes share total/free but have individual used space
                # Track the largest total (all volumes report same total in APFS)
                if usage.total > disks_dict[disk_id]["total_size"]:
                    disks_dict[disk_id]["total_size"] = usage.total
                # Sum all volumes' used space (each volume has unique data)
                disks_dict[disk_id]["total_used"] += usage.used
                # Track free space (shared across all volumes in APFS, so just keep the latest)
                disks_dict[disk_id]["total_free"] = usage.free

            except (PermissionError, FileNotFoundError):
                continue

        # Now create volumes from disks
        volumes = []
        for disk_id, disk_data in disks_dict.items():
            # Find the primary partition (usually root or first partition)
            primary_partition = None
            for part in disk_data["partitions"]:
                if part["mountpoint"] == "/":
                    primary_partition = part
                    break
            if not primary_partition and disk_data["partitions"]:
                primary_partition = disk_data["partitions"][0]

            # Determine volume name from primary partition
            if primary_partition:
                if primary_partition["mountpoint"] == "/":
                    volume_name = "System"
                else:
                    volume_name = primary_partition["mountpoint"].split("/")[-1] or disk_id

                # Calculate aggregate usage percentage
                total_size = disk_data["total_size"]
                total_used = disk_data["total_used"]
                usage_percent = (total_used / total_size * 100) if total_size > 0 else 0

                # Create a pseudo usage object for display
                class UsageInfo:
                    def __init__(self, total, used, free, percent):
                        self.total = total
                        self.used = used
                        self.free = free
                        self.percent = percent

                volume = {
                    "volume_name": volume_name,
                    "disk_id": disk_id,
                    "partitions": disk_data["partitions"],
                    "usage": UsageInfo(
                        total_size, total_used, disk_data["total_free"], usage_percent
                    ),
                }

                # Get I/O statistics for this disk
                try:
                    io_counters = psutil.disk_io_counters(perdisk=True)
                    disk_name = self._get_disk_name_for_io(primary_partition["device"])
                    if disk_name and disk_name in io_counters:
                        io_stat = io_counters[disk_name]
                        volume["io_stats"] = {
                            "read_count": io_stat.read_count,
                            "write_count": io_stat.write_count,
                            "read_bytes": io_stat.read_bytes,
                            "write_bytes": io_stat.write_bytes,
                            "read_time": io_stat.read_time,
                            "write_time": io_stat.write_time,
                        }
                except Exception:
                    pass

                volumes.append(volume)

        return volumes

    def _extract_disk_id(self, device: str) -> str:
        """Extract disk identifier from device path."""
        import re

        # macOS: /dev/disk3s1 -> disk3
        # Linux: /dev/sda1 -> sda
        match = re.search(r"disk\d+", device)
        if match:
            return match.group(0)
        # Linux: extract base device name (sda from sda1)
        match = re.search(r"([sh]d[a-z]+)", device)
        if match:
            return match.group(1)
        return device

    def _extract_partition_id(self, device: str) -> str:
        """Extract full partition identifier from device path."""
        import re

        # macOS: /dev/disk3s1 -> disk3s1 or /dev/disk3s1s1 -> disk3s1s1
        # Linux: /dev/sda1 -> sda1
        match = re.search(r"(disk\d+s\d+(?:s\d+)?|[a-z]+\d+)", device)
        if match:
            return match.group(1)
        return device.split("/")[-1]  # Fallback to just the device name

    def _get_disk_name_for_io(self, device: str) -> Optional[str]:
        """Get disk name for I/O statistics lookup."""
        system = platform.system()

        if system == "Darwin":
            # macOS: /dev/disk3s1 -> disk3
            import re

            match = re.search(r"disk\d+", device)
            return match.group(0) if match else None
        elif system == "Linux":
            # Linux: /dev/sda1 -> sda
            import re

            match = re.search(r"([a-z]+)\d*$", device)
            return match.group(1) if match else None

        return None

    def refresh_volume_list(self):
        """Refresh the list of volumes."""
        self.volumes = self.get_volume_info()

        list_view = self.query_one("#volume-list", ListView)

        # Store current selection
        current_index = list_view.index if list_view.index is not None else 0

        # Clear and repopulate
        list_view.clear()

        for volume in self.volumes:
            usage = volume["usage"]
            volume_name = volume["volume_name"]

            # Add usage info
            used = sizeof_fmt(usage.used, fmt=".1f", sep="")
            total = sizeof_fmt(usage.total, fmt=".1f", sep="")
            percent = usage.percent

            # Color code based on usage
            if percent > 95:
                style = "red"
            elif percent > 80:
                style = "yellow"
            else:
                style = "green"

            label = Text()
            label.append(f"{volume_name} ", style="bold white")
            label.append(f"\n  {used}/{total} ", style="dim")
            label.append(f"({percent:.3f}%)", style=style)

            list_item = VolumeListItem(volume, Static(label))
            list_view.append(list_item)

        # Restore selection
        if self.volumes and current_index < len(self.volumes):
            list_view.index = current_index
            # Update main panel with current volume
            info_panel = self.query_one("#main-panel", VolumeInfoPanel)
            info_panel.update_volume_info(self.volumes[current_index])

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle volume selection."""
        if isinstance(event.item, VolumeListItem):
            volume_info = event.item.volume_info
            info_panel = self.query_one("#main-panel", VolumeInfoPanel)
            info_panel.update_volume_info(volume_info)

    def action_cursor_up(self):
        """Move cursor up in volume list."""
        list_view = self.query_one("#volume-list", ListView)
        list_view.action_cursor_up()

    def action_cursor_down(self):
        """Move cursor down in volume list."""
        list_view = self.query_one("#volume-list", ListView)
        list_view.action_cursor_down()
