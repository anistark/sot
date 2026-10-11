"""
Network Connections Widget

Sockets by state, a graph of active connections over time, and the processes
holding the most sockets.
"""

from collections import Counter

from rich.console import Group
from rich.text import Text
from textual import events

from .._collectors import inet_connections
from .._theme import ThemedStream, theme
from ..tui import keymap, refresh
from ..tui.messages import Reveal
from .base_widget import BaseWidget

GRAPH_HEIGHT = 2
# Room for the legend, bar, graph and its caption before any process rows.
GRAPH_MIN_HEIGHT = 9


def _state(status: str) -> str:
    if status == "ESTABLISHED":
        return "active"
    if status == "LISTEN":
        return "listen"
    if status == "NONE":
        return "udp"
    return "other"


def _split(counts: list[int], width: int) -> list[int]:
    """Bar cells per count, giving every non-zero count at least one."""
    total = sum(counts)
    if not total:
        return [0] * len(counts)
    cells = [max(1, n * width // total) if n else 0 for n in counts]
    cells[cells.index(max(cells))] += width - sum(cells)
    return cells


class NetworkConnectionsWidget(BaseWidget):
    """Network connections: how many, in which state, and whose."""

    can_focus = True
    BINDINGS = [keymap.OPEN]
    STATE = ("history", "peak")

    def __init__(self, **kwargs):
        super().__init__(title="Connections", **kwargs)
        self.counts: Counter[str] = Counter()
        self.by_process: Counter[str] = Counter()
        self.complete = True
        self.error: str | None = None

    def on_mount(self):
        if not self.restore_state():
            self.history = ThemedStream(20, GRAPH_HEIGHT, 0.0, 8.0)
            self.peak = 0
        self.update_content()
        self.every(refresh.CONNECTIONS, self.update_content)

    def action_open(self) -> None:
        self.post_message(Reveal("processes", "port-table"))

    def on_click(self, event: events.Click) -> None:
        if event.chain == 2:
            self.action_open()

    def on_resize(self, event: events.Resize) -> None:
        self.history.reset_width(max(1, self.content_size.width))

    def update_content(self):
        try:
            conns, self.complete = inet_connections()
        except Exception as e:
            self.error = str(e)
            self.refresh()
            return

        self.error = None
        self.counts = Counter(_state(c["status"]) for c in conns)
        self.by_process = Counter(c["name"] for c in conns)

        active = self.counts["active"]
        self.peak = max(self.peak, active)
        # Headroom so a steady count sits mid-graph and changes show.
        if active > self.history.maxval * 0.75:
            self.history.maxval = active * 1.5
        self.history.add_value(active)

        total = len(conns)
        self.set_title(
            "Connections", f"{total} yours" if not self.complete else str(total)
        )
        self.border_subtitle = (
            None if self.complete else Text("sudo for all", style=theme().colors.muted)
        )
        self.refresh()

    def render(self):
        t = theme()
        c = t.colors
        width = max(1, self.content_size.width)
        height = self.content_size.height

        if self.error:
            return Text(self.error, style=c.danger, overflow="ellipsis")

        fill = t.design.meter.fill
        states = [
            ("active", c.ok),
            ("listen", c.accent),
            ("udp", c.primary),
            ("other", c.warm),
        ]
        half = width // 2
        digits = len(str(max(self.counts.values(), default=0)))
        # Drop the gap after the swatch when two cells barely fit.
        gap = " " if 2 * (digits + 9) + 1 <= width else ""
        lines = []
        for row in (states[:2], states[2:]):
            line = Text(no_wrap=True, overflow="crop")
            for state, color in row:
                cell = Text()
                cell.append(fill, style=color)
                cell.append(
                    f"{gap}{self.counts[state]:>{digits}} ", style=f"bold {c.text}"
                )
                cell.append(state, style=c.muted)
                cell.pad_right(half - cell.cell_len)
                line.append_text(cell)
            lines.append(line)

        bar = Text(no_wrap=True)
        cells = _split([self.counts[s] for s, _ in states], width)
        for (_, color), n in zip(states, cells):
            bar.append(fill * n, style=color)
        if not sum(cells):
            bar.append(t.design.meter.empty * width, style=c.muted)
        lines.append(bar)

        if height >= GRAPH_MIN_HEIGHT:
            lines.append(Text())
            lines.append(t.graph(self.history.graph, c.ok))
            caption = Text("active", style=c.ok, no_wrap=True, overflow="crop")
            detail = f" over time · peak {self.peak}"
            if caption.cell_len + len(detail) > width:
                detail = f" · peak {self.peak}"
            caption.append(detail, style=c.muted)
            lines.append(caption)

        rows = height - len(lines) - 1
        top = self.by_process.most_common(max(0, rows))
        if top:
            lines.append(Text())
            most = top[0][1]
            meter_width = 6 if width >= 26 else 0
            name_width = max(1, width - meter_width - 5)
            for name, count in top:
                row = Text(no_wrap=True, overflow="crop")
                label = (
                    name if len(name) <= name_width else name[: name_width - 1] + "…"
                )
                row.append(label.ljust(name_width) + " ", style=c.text)
                if meter_width:
                    row.append_text(
                        t.meter(
                            count / most, meter_width - 1, c.info, empty_style=c.muted
                        )
                    )
                    row.append(" ")
                row.append(f"{count:>4}", style=f"bold {c.text}")
                lines.append(row)
        elif not self.by_process and rows > 0:
            lines.append(Text())
            lines.append(Text("No open sockets", style=c.muted))

        return Group(*lines)
