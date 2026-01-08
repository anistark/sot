"""Process TUI - Interactive process viewer."""

from __future__ import annotations

import datetime
import platform

import psutil
from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Static

from ..__about__ import __version__
from .._helpers import sizeof_fmt
from ..widgets.processes import get_process_list
from ..widgets.process_sorter import SortManager


class CustomHeader(Static):
    """Custom header with title, time and battery."""

    def on_mount(self):
        self.update_header()
        self.set_interval(1.0, self.update_header)

    def update_header(self):
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")

        battery_str = ""
        try:
            battery = psutil.sensors_battery()
            if battery:
                percent = int(battery.percent)
                if battery.power_plugged:
                    battery_str = f"🔌 {percent}%"
                else:
                    if percent > 80:
                        battery_str = f"🔋 {percent}%"
                    elif percent > 50:
                        battery_str = f"🔋 {percent}%"
                    elif percent > 20:
                        battery_str = f"🪫 {percent}%"
                    else:
                        battery_str = f"🪫 {percent}%"
        except Exception:
            pass

        header_table = Table.grid(expand=True, padding=0)
        header_table.add_column(justify="left", ratio=1)
        header_table.add_column(justify="right", no_wrap=True)

        left_text = Text("SOT Process Viewer", style="bold bright_cyan")

        right_text = Text()
        if battery_str:
            right_text.append(f"{battery_str}  ", style="bright_yellow")
        right_text.append(f"{date_str} {time_str}", style="bright_white")

        header_table.add_row(left_text, right_text)
        self.update(header_table)


class CustomFooter(Static):
    """Custom footer showing version."""

    def on_mount(self):
        self.update_footer()

    def update_footer(self):
        footer_table = Table.grid(expand=True, padding=0)
        footer_table.add_column(justify="center", ratio=1)

        version_text = Text(f"SOT v{__version__}", style="dim bright_white")
        footer_table.add_row(version_text)

        self.update(footer_table)


class ProcessListPanel(Widget):
    """Process list panel on the left."""

    can_focus = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processes = []
        self.selected_index = 0
        self.scroll_position = 0
        self.visible_rows = 20
        self.sort_manager = SortManager()

    def on_mount(self):
        self.refresh_processes()
        self.set_interval(2.0, self.refresh_processes)

    def refresh_processes(self):
        self.processes = get_process_list(500, self.sort_manager)
        if self.selected_index >= len(self.processes):
            self.selected_index = max(0, len(self.processes) - 1)
        max_scroll = max(0, len(self.processes) - self.visible_rows)
        self.scroll_position = min(self.scroll_position, max_scroll)
        self.refresh()

    def render(self):
        table = Table(
            show_header=True,
            header_style="bold cyan",
            box=None,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("PID", justify="right", width=8)
        table.add_column("Process", style="aquamarine3", no_wrap=True, ratio=1)
        table.add_column("Memory", justify="right", width=8)
        table.add_column("CPU %", justify="right", width=7)

        end_index = min(len(self.processes), self.scroll_position + self.visible_rows)
        visible = self.processes[self.scroll_position : end_index]

        for local_idx, proc in enumerate(visible):
            actual_idx = self.scroll_position + local_idx
            is_selected = self.has_focus and actual_idx == self.selected_index

            pid = str(proc.get("pid", ""))
            name = proc.get("name", "")
            if is_selected:
                name = f"▶ {name}"

            mem_info = proc.get("memory_info")
            mem_str = "" if mem_info is None else sizeof_fmt(mem_info.rss, suffix="", sep="")

            cpu = proc.get("cpu_percent", 0) or 0
            cpu_str = f"{cpu:.1f}"

            style = "black on white" if is_selected else None
            table.add_row(pid, name, mem_str, cpu_str, style=style)

        total = len(self.processes)
        if total > self.visible_rows:
            scroll_info = f"({self.scroll_position + 1}-{end_index} of {total})"
        else:
            scroll_info = f"({total})"

        title = f"[bold]Processes {scroll_info}[/]"
        border_style = "bright_cyan" if self.has_focus else "dim"

        return Panel(table, title=title, border_style=border_style)

    def on_key(self, event: events.Key):
        if not self.has_focus:
            return

        key = event.key
        if key == "up":
            if self.selected_index > 0:
                self.selected_index -= 1
                if self.selected_index < self.scroll_position:
                    self.scroll_position = self.selected_index
                self.refresh()
            event.prevent_default()
        elif key == "down":
            if self.selected_index < len(self.processes) - 1:
                self.selected_index += 1
                if self.selected_index >= self.scroll_position + self.visible_rows:
                    self.scroll_position = self.selected_index - self.visible_rows + 1
                self.refresh()
            event.prevent_default()

    def on_resize(self, event):
        self.visible_rows = max(10, self.size.height - 3)
        self.refresh()


class ComingSoonPanel(Widget):
    """Coming soon panel."""

    can_focus = True

    def __init__(self, section_name: str, **kwargs):
        super().__init__(**kwargs)
        self.section_name = section_name

    def render(self):
        content = Align.center(
            Text("Coming Soon", style="bold bright_yellow"), vertical="middle"
        )
        border_style = "bright_cyan" if self.has_focus else "dim"
        return Panel(
            content,
            title=f"[bold]{self.section_name}[/]",
            border_style=border_style,
        )


class ProcessTUIApp(App):
    """SOT Process TUI Application."""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #left-panel {
        width: 50%;
        height: 1fr;
    }

    #right-container {
        width: 50%;
        layout: vertical;
    }

    #right-top {
        height: 50%;
    }

    #right-bottom {
        height: 50%;
    }

    CustomHeader {
        height: 3;
        dock: top;
        background: $panel;
        border-bottom: solid $primary;
        padding: 1;
    }

    CustomFooter {
        height: 1;
        dock: bottom;
        background: $panel;
        border-top: solid $primary;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("tab", "focus_next", "Next Section"),
    ]

    def compose(self) -> ComposeResult:
        yield CustomHeader()

        with Horizontal():
            yield ProcessListPanel(id="left-panel")

            with Vertical(id="right-container"):
                yield ComingSoonPanel("Top Right", id="right-top")
                yield ComingSoonPanel("Bottom Right", id="right-bottom")

        yield CustomFooter()

    def on_mount(self):
        self.title = "SOT Process Viewer"
        self.sub_title = f"v{__version__}"
        self.query_one("#left-panel").focus()

    def action_focus_next(self):
        """Cycle focus between the three panels."""
        focusable = [
            self.query_one("#left-panel"),
            self.query_one("#right-top"),
            self.query_one("#right-bottom"),
        ]

        try:
            current_idx = focusable.index(self.focused)
            next_idx = (current_idx + 1) % len(focusable)
            focusable[next_idx].focus()
        except (ValueError, AttributeError):
            focusable[0].focus()
