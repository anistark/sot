"""Plain-text disk listing: ``sot disk --list``."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .._helpers import sizeof_fmt
from .._theme import theme
from .volumes import get_volume_info, usage_style

BAR_WIDTH = 20
COMPACT_BAR_WIDTH = 10
# Below this many columns the FS column is dropped and the bar shrinks
COMPACT_BELOW = 110


def _usage_bar(percent: float, width: int = BAR_WIDTH) -> Text:
    """Inline block bar coloured by how full the volume is."""
    used_blocks = int(percent / 100 * width)
    bar = Text()
    bar.append("█" * used_blocks, style=usage_style(percent))
    bar.append("░" * (width - used_blocks), style=theme().colors.muted)
    return bar


def _percent(percent: float) -> Text:
    return Text(f"{percent:.1f}%", style=f"bold {usage_style(percent)}")


def build_disk_table(volumes: list[dict], width: int = COMPACT_BELOW) -> Table:
    """One row per physical disk, with its partitions nested underneath.

    ``width`` is the terminal width; narrow terminals get a compact layout so
    the mountpoints stay readable instead of being truncated.
    """
    c = theme().colors
    compact = width < COMPACT_BELOW
    bar_width = COMPACT_BAR_WIDTH if compact else BAR_WIDTH
    table = Table(
        show_header=True,
        header_style=f"bold {c.accent}",
        box=None,
        padding=(0, 1 if compact else 2),
        pad_edge=False,
    )
    table.add_column("Device", style="bold", no_wrap=True)
    table.add_column("Mount", overflow="fold")
    if not compact:
        table.add_column("FS", style=c.muted, no_wrap=True)
    table.add_column("Size", justify="right", no_wrap=True)
    table.add_column("Used", justify="right", no_wrap=True)
    table.add_column("Free", justify="right", no_wrap=True)
    table.add_column("Usage", no_wrap=True, min_width=bar_width)
    table.add_column("", justify="right", no_wrap=True)

    for i, volume in enumerate(volumes):
        usage = volume["usage"]
        table.add_row(
            Text(volume["disk_id"], style=f"bold {c.accent}"),
            Text(volume["volume_name"], style="bold"),
            *([] if compact else [""]),
            sizeof_fmt(usage.total, fmt=".1f"),
            sizeof_fmt(usage.used, fmt=".1f"),
            sizeof_fmt(usage.free, fmt=".1f"),
            _usage_bar(usage.percent, bar_width),
            _percent(usage.percent),
        )

        partitions = volume["partitions"]
        for j, part in enumerate(partitions):
            branch = "└─" if j == len(partitions) - 1 else "├─"
            pu = part["usage"]
            table.add_row(
                Text(f" {branch} {part['partition_id']}", style=c.muted),
                part["mountpoint"],
                *([] if compact else [part["fstype"]]),
                sizeof_fmt(pu.total, fmt=".1f"),
                sizeof_fmt(pu.used, fmt=".1f"),
                sizeof_fmt(pu.free, fmt=".1f"),
                _usage_bar(pu.percent, bar_width),
                _percent(pu.percent),
            )

        if i < len(volumes) - 1:
            table.add_row()

    return table


def print_disk_list(console: Console | None = None) -> int:
    """Print every disk and partition as a static table. Returns an exit code."""
    console = console or Console()
    c = theme().colors
    volumes = get_volume_info()

    if not volumes:
        console.print(f"[{c.warn}]No disks found.[/]")
        return 1

    console.print()
    console.print(f"💾 [bold]{len(volumes)} disk(s)[/]")
    console.print()
    console.print(build_disk_table(volumes, console.width))

    total = sum(v["usage"].total for v in volumes)
    used = sum(v["usage"].used for v in volumes)
    free = sum(v["usage"].free for v in volumes)
    percent = (used / total * 100) if total else 0.0

    summary = Text()
    summary.append("Total ", style=c.muted)
    summary.append(sizeof_fmt(total, fmt=".1f"), style="bold")
    summary.append("  ·  Used ", style=c.muted)
    summary.append(sizeof_fmt(used, fmt=".1f"), style="bold")
    summary.append("  ·  Free ", style=c.muted)
    summary.append(sizeof_fmt(free, fmt=".1f"), style="bold")
    summary.append("  ·  ", style=c.muted)
    summary.append_text(_percent(percent))
    console.print()
    console.print(summary)
    console.print()
    return 0
