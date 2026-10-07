"""
Processes Widget

Displays interactive process list with keyboard navigation, process management, and network usage.
"""

import time
from typing import Optional

import psutil
from rich.table import Table
from rich.text import Text
from textual.binding import Binding

from .._helpers import sizeof_fmt
from .._theme import theme
from ..tui import keymap
from ..tui.process_list import ProcessListActions
from .base_widget import BaseWidget
from .process_sorter import SortManager


def get_process_list(num_procs: int, sort_manager: Optional[SortManager] = None):
    """Get list of running processes with network I/O information.

    Applies sorting from sort_manager if provided, otherwise returns unsorted.
    """
    processes = []

    for proc in psutil.process_iter(
        [
            "pid",
            "name",
            "username",
            "cmdline",
            "cpu_percent",
            "num_threads",
            "memory_info",
            "status",
        ]
    ):
        try:
            proc_info = proc.info.copy()
            try:
                connections = proc.connections(kind="inet")
                proc_info["num_connections"] = len(connections)
                try:
                    io_counters = getattr(proc, "io_counters", lambda: None)()
                    if (
                        io_counters
                        and hasattr(io_counters, "read_bytes")
                        and hasattr(io_counters, "write_bytes")
                    ):
                        proc_info["io_read_bytes"] = io_counters.read_bytes
                        proc_info["io_write_bytes"] = io_counters.write_bytes
                    else:
                        proc_info["io_read_bytes"] = 0
                        proc_info["io_write_bytes"] = 0
                except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                    proc_info["io_read_bytes"] = 0
                    proc_info["io_write_bytes"] = 0

            except (psutil.AccessDenied, psutil.NoSuchProcess):
                proc_info["num_connections"] = 0
                proc_info["io_read_bytes"] = 0
                proc_info["io_write_bytes"] = 0

            processes.append(proc_info)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if processes and processes[0].get("pid") == 0:
        processes = processes[1:]

    if sort_manager:
        processes = sort_manager.apply_sort(processes)

    return processes[:num_procs]


class ProcessesWidget(ProcessListActions, BaseWidget):
    """Interactive process list with arrow key navigation, actions, and network monitoring."""

    BINDINGS = [
        *keymap.LIST,
        *keymap.PROCESS,
        *keymap.SORT_MODE,
        Binding("i", "toggle_interactive", "Interactive", id="sot.process.interactive"),
        Binding("n", "toggle_network", "Net columns", id="sot.process.network"),
    ]

    STATE = (
        "processes",
        "selected_index",
        "scroll_position",
        "sort_manager",
        "previous_process_data",
        "previous_sample_time",
        "is_interactive_mode",
        "show_network_details",
    )

    def __init__(self, **kwargs):
        super().__init__(title="Processes", **kwargs)
        self.max_num_procs = 1000
        self.visible_rows = 10
        self.selected_index = 0
        self.scroll_position = 0
        self.processes = []
        self.previous_process_data = {}
        self.previous_sample_time = 0.0
        self.is_interactive_mode = True
        self.show_network_details = True
        self.sort_manager = SortManager()

    def on_mount(self):
        self.restore_state()
        self.collect_data()
        self.set_interval(6.0, self.collect_data)
        self.focus()

    def redraw(self) -> None:
        self.refresh_display()

    def reload(self) -> None:
        self.collect_data()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "toggle_interactive":
            return not self.sort_manager.sort_mode_active
        if not self.is_interactive_mode:
            return False
        return super().check_action(action, parameters)

    def action_toggle_interactive(self) -> None:
        self.is_interactive_mode = not self.is_interactive_mode
        self.refresh_display()

    def action_toggle_network(self) -> None:
        self.show_network_details = not self.show_network_details
        self.refresh_display()

    def calculate_io_rates(self, current_processes):
        """Calculate I/O rates by comparing with previous data."""
        now = time.monotonic()
        interval_seconds = now - self.previous_sample_time
        self.previous_sample_time = now
        for proc in current_processes:
            pid = proc.get("pid")
            if not pid:
                continue

            current_read = proc.get("io_read_bytes", 0)
            current_write = proc.get("io_write_bytes", 0)

            if pid in self.previous_process_data and interval_seconds > 0:
                prev_read = self.previous_process_data[pid].get("io_read_bytes", 0)
                prev_write = self.previous_process_data[pid].get("io_write_bytes", 0)

                read_rate = max(0, (current_read - prev_read) / interval_seconds)
                write_rate = max(0, (current_write - prev_write) / interval_seconds)

                proc["io_read_rate"] = read_rate
                proc["io_write_rate"] = write_rate
                proc["total_io_rate"] = read_rate + write_rate
            else:
                proc["io_read_rate"] = 0
                proc["io_write_rate"] = 0
                proc["total_io_rate"] = 0

        self.previous_process_data = {
            proc.get("pid"): {
                "io_read_bytes": proc.get("io_read_bytes", 0),
                "io_write_bytes": proc.get("io_write_bytes", 0),
            }
            for proc in current_processes
            if proc.get("pid")
        }

    def collect_data(self):
        new_process_data = get_process_list(self.max_num_procs, self.sort_manager)
        self.calculate_io_rates(new_process_data)
        self.processes = new_process_data
        self.clamp_cursor()
        self.refresh_display()

    def refresh_display(self):
        """Refresh the process list display with current selection and scrolling."""
        t = theme()
        c = t.colors
        process_table = Table(
            row_styles=t.row_styles(),
            show_header=True,
            header_style=c.label,
            box=None,
            padding=(0, 1),
            expand=True,
        )

        process_table.add_column(
            Text("PID", justify="left"), no_wrap=True, justify="right", width=8
        )
        process_table.add_column("Process", style=c.secondary, no_wrap=True, ratio=1)
        process_table.add_column(
            Text("🧵", justify="left"),
            style=c.secondary,
            no_wrap=True,
            justify="right",
            width=4,
        )
        process_table.add_column(
            Text("Memory", justify="left"),
            style=c.secondary,
            no_wrap=True,
            justify="right",
            width=8,
        )

        if self.show_network_details:
            process_table.add_column(
                Text("Net I/O", justify="left"),
                style=c.primary,
                no_wrap=True,
                justify="right",
                width=9,
            )
            process_table.add_column(
                Text("Conn", justify="left"),
                style=c.info,
                no_wrap=True,
                justify="right",
                width=4,
            )

        process_table.add_column(
            Text("CPU %", style="u", justify="left"),
            no_wrap=True,
            justify="right",
            width=7,
        )

        end_index = min(
            len(self.processes),
            self.scroll_position + self.visible_rows,
        )
        visible_processes = self.processes[self.scroll_position : end_index]

        for local_index, process_info in enumerate(visible_processes):
            actual_index = self.scroll_position + local_index

            is_selected_row = (
                self.is_interactive_mode and actual_index == self.selected_index
            )

            process_id = process_info.get("pid")
            process_id_str = "" if process_id is None else str(process_id)

            process_name = process_info.get("name", "")
            if process_name is None:
                process_name = ""

            num_threads = process_info.get("num_threads")
            num_threads_str = "" if num_threads is None else str(num_threads)

            memory_info = process_info.get("memory_info")
            memory_info_str = (
                ""
                if memory_info is None
                else sizeof_fmt(memory_info.rss, suffix="", sep="")
            )

            cpu_percentage = process_info.get("cpu_percent")
            cpu_percentage_str = (
                "" if cpu_percentage is None else f"{cpu_percentage:.1f}"
            )

            # Initialize network variables
            net_io_str = "-"
            connections_str = "-"

            if self.show_network_details:
                total_io_rate = process_info.get("total_io_rate", 0)
                if total_io_rate > 0:
                    net_io_str = (
                        sizeof_fmt(total_io_rate, fmt=".1f", suffix="", sep="") + "/s"
                    )
                else:
                    net_io_str = "-"

                num_connections = process_info.get("num_connections", 0)
                connections_str = str(num_connections) if num_connections > 0 else "-"

            row_style = None
            if is_selected_row:
                row_style = c.selected
                process_name = f"{t.design.cursor}{process_name}"

            row_data = [
                process_id_str,
                process_name,
                num_threads_str,
                memory_info_str,
            ]

            if self.show_network_details:
                row_data.extend([net_io_str, connections_str])

            row_data.append(cpu_percentage_str)

            process_table.add_row(*row_data, style=row_style)

        total_num_threads = sum((p.get("num_threads") or 0) for p in self.processes)
        num_sleeping_processes = sum(
            p.get("status") == "sleeping" for p in self.processes
        )
        total_connections = sum((p.get("num_connections") or 0) for p in self.processes)

        total_processes = len(self.processes)
        if total_processes > self.visible_rows:
            scroll_info = (
                f"({self.scroll_position + 1}-{end_index} of {total_processes})"
            )
        else:
            scroll_info = f"({total_processes})"

        title_parts = [
            t.title("📋 Processes"),
            f"{total_processes} {scroll_info} ({total_num_threads} 🧵)",
            f"{num_sleeping_processes} 😴",
        ]

        if self.show_network_details:
            title_parts.append(f"{total_connections} 🌐")

        sort_indicator = self.sort_manager.get_sort_indicator_str()
        title_parts.append(f"[{c.accent}]Sort: {sort_indicator}[/]")

        focus_indicator = "🔍" if self.has_focus else "○"
        if self.sort_manager.sort_mode_active:
            current_col = self.sort_manager.current_column().display_name
            direction = self.sort_manager.sort_direction.icon()
            columns_display = " | ".join(
                col.display_name for col in self.sort_manager.COLUMNS
            )

            sep = t.design.separator
            panel_title = f"[{c.alert_tag}] ORDER BY [/]{sep}[bold {c.accent}]{current_col}[/] [bold {c.secondary}]{direction}[/]{sep}{columns_display}"
            self.panel.title = panel_title
            self.panel.border_style = c.border_alert
        else:
            if self.is_interactive_mode:
                help_text = "O order | ↑↓ | ⏎ info | K kill | T terminate | R refresh"
                if self.show_network_details:
                    help_text += " | N hide net"
                else:
                    help_text += " | N show net"
                title_parts.append(f"[{c.muted}]{focus_indicator} {help_text}[/]")
            else:
                title_parts.append(
                    f"[{c.muted}]{focus_indicator} Press I for interactive mode[/]"
                )

            panel_title = t.design.separator.join(title_parts)
            self.panel.title = panel_title

            self.panel.border_style = c.border_focus if self.has_focus else c.border

        self.update_panel_content(process_table)

    def on_click(self, event) -> None:
        """Handle mouse clicks to focus the widget."""
        self.focus()
        event.prevent_default()

    def on_focus(self) -> None:
        """Handle widget gaining focus."""
        self.refresh_display()

    def on_blur(self) -> None:
        """Handle widget losing focus."""
        self.refresh_display()

    async def on_resize(self, event):
        new_visible_rows = max(5, self.size.height - 3)
        self.visible_rows = new_visible_rows
        self.max_num_procs = min(3000, max(500, new_visible_rows * 3))
        max_scroll = max(0, len(self.processes) - self.visible_rows)
        self.scroll_position = min(self.scroll_position, max_scroll)
        if len(self.processes) < self.max_num_procs:
            self.collect_data()
        else:
            self.refresh_display()
