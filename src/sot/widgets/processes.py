"""
Processes Widget

Displays interactive process list with keyboard navigation and process management.
"""

import psutil
from rich.table import Table
from rich.text import Text
from textual import events
from textual.message import Message

from .base_widget import BaseWidget
from .._helpers import sizeof_fmt


def get_process_list(num_procs: int):
    """Get list of running processes sorted by CPU usage."""
    processes = list(
        psutil.process_iter(
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
        )
    )

    if processes and processes[0].pid == 0:
        processes = processes[1:]

    processes = [p.info for p in processes]

    processes = sorted(
        processes,
        key=lambda p: (p["cpu_percent"] or 0.0),
        reverse=True,
    )
    processes = processes[:num_procs]
    return processes


class ProcessesWidget(BaseWidget):
    """Interactive process list with arrow key navigation and actions."""

    can_focus = True

    class ProcessSelected(Message):
        """Message sent when a process is selected."""

        def __init__(self, process_info: dict) -> None:
            self.process_info = process_info
            super().__init__()

    class ProcessAction(Message):
        """Message sent when an action is requested on a process."""

        def __init__(self, action: str, process_info: dict) -> None:
            self.action = action
            self.process_info = process_info
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(title="Processes", **kwargs)
        self.max_num_procs = 1000
        self.visible_rows = 10
        self.selected_process_index = 0
        self.current_scroll_position = 0
        self.process_list_data = []
        self.is_interactive_mode = True

    def on_mount(self):
        self.collect_data()
        self.set_interval(6.0, self.collect_data)
        self.focus()

    def handle_navigation_keys(self, key_pressed: str) -> bool:
        """Handle navigation keys (up, down, page up/down, home, end). Returns True if handled."""
        if key_pressed == "up":
            if self.selected_process_index > 0:
                self.selected_process_index -= 1
                if self.selected_process_index < self.current_scroll_position:
                    self.current_scroll_position = self.selected_process_index
            return True

        elif key_pressed == "down":
            max_index = len(self.process_list_data) - 1
            if self.selected_process_index < max_index:
                self.selected_process_index += 1
                if (
                    self.selected_process_index
                    >= self.current_scroll_position + self.visible_rows
                ):
                    self.current_scroll_position = (
                        self.selected_process_index - self.visible_rows + 1
                    )
            return True

        elif key_pressed == "pageup" or key_pressed == "ctrl+u":
            self.selected_process_index = max(
                0, self.selected_process_index - self.visible_rows
            )
            self.current_scroll_position = max(
                0, self.current_scroll_position - self.visible_rows
            )
            return True

        elif key_pressed == "pagedown" or key_pressed == "ctrl+d":
            max_index = len(self.process_list_data) - 1
            self.selected_process_index = min(
                max_index, self.selected_process_index + self.visible_rows
            )
            self.current_scroll_position = min(
                max(0, len(self.process_list_data) - self.visible_rows),
                self.current_scroll_position + self.visible_rows,
            )
            return True

        elif key_pressed == "home" or key_pressed == "ctrl+home":
            self.selected_process_index = 0
            self.current_scroll_position = 0
            return True

        elif key_pressed == "end" or key_pressed == "ctrl+end":
            max_index = len(self.process_list_data) - 1
            self.selected_process_index = max_index
            self.current_scroll_position = max(0, max_index - self.visible_rows + 1)
            return True

        return False

    def handle_action_keys(self, key_pressed: str) -> bool:
        """Handle action keys (enter, kill, terminate, refresh, toggle). Returns True if handled."""
        if key_pressed == "enter":
            if 0 <= self.selected_process_index < len(self.process_list_data):
                selected_process = self.process_list_data[self.selected_process_index]
                self.post_message(self.ProcessSelected(selected_process))
            return True
        elif key_pressed == "k":
            if 0 <= self.selected_process_index < len(self.process_list_data):
                selected_process = self.process_list_data[self.selected_process_index]
                self.post_message(self.ProcessAction("kill", selected_process))
            return True
        elif key_pressed == "t":
            if 0 <= self.selected_process_index < len(self.process_list_data):
                selected_process = self.process_list_data[self.selected_process_index]
                self.post_message(self.ProcessAction("terminate", selected_process))
            return True
        elif key_pressed == "r":
            self.collect_data()
            return True
        elif key_pressed == "i":
            self.is_interactive_mode = not self.is_interactive_mode
            return True

        return False

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard navigation and actions with scrolling support."""
        if not self.is_interactive_mode or not self.process_list_data:
            return

        key_pressed = event.key

        if self.handle_navigation_keys(key_pressed):
            self.refresh_display()
            event.prevent_default()
            return

        if self.handle_action_keys(key_pressed):
            if key_pressed != "r":
                self.refresh_display()
            event.prevent_default()
            return

    def collect_data(self):
        self.process_list_data = get_process_list(self.max_num_procs)

        if self.selected_process_index >= len(self.process_list_data):
            self.selected_process_index = max(0, len(self.process_list_data) - 1)

        max_scroll = max(0, len(self.process_list_data) - self.visible_rows)
        self.current_scroll_position = min(self.current_scroll_position, max_scroll)

        self.refresh_display()

    def refresh_display(self):
        """Refresh the process list display with current selection and scrolling."""
        process_table = Table(
            show_header=True,
            header_style="bold",
            box=None,
            padding=(0, 1),
            expand=True,
        )

        process_table.add_column(
            Text("PID", justify="left"), no_wrap=True, justify="right"
        )
        process_table.add_column("Process", style="aquamarine3", no_wrap=True, ratio=1)
        process_table.add_column(
            Text("🧵", justify="left"),
            style="aquamarine3",
            no_wrap=True,
            justify="right",
        )
        process_table.add_column(
            Text("Mem", justify="left"),
            style="aquamarine3",
            no_wrap=True,
            justify="right",
        )
        process_table.add_column(
            Text("CPU %", style="u", justify="left"),
            no_wrap=True,
            justify="right",
        )

        end_index = min(
            len(self.process_list_data),
            self.current_scroll_position + self.visible_rows,
        )
        visible_processes = self.process_list_data[
            self.current_scroll_position : end_index
        ]

        for local_index, process_info in enumerate(visible_processes):
            actual_index = self.current_scroll_position + local_index

            is_selected_row = (
                self.is_interactive_mode and actual_index == self.selected_process_index
            )

            process_id = process_info["pid"]
            process_id_str = "" if process_id is None else str(process_id)

            process_name = process_info["name"]
            if process_name is None:
                process_name = ""

            num_threads = process_info["num_threads"]
            num_threads_str = "" if num_threads is None else str(num_threads)

            memory_info = process_info["memory_info"]
            memory_info_str = (
                ""
                if memory_info is None
                else sizeof_fmt(memory_info.rss, suffix="", sep="")
            )

            cpu_percentage = process_info["cpu_percent"]
            cpu_percentage_str = (
                "" if cpu_percentage is None else f"{cpu_percentage:.1f}"
            )

            row_style = None
            if is_selected_row:
                row_style = "black on white"
                process_name = f"▶ {process_name}"

            process_table.add_row(
                process_id_str,
                process_name,
                num_threads_str,
                memory_info_str,
                cpu_percentage_str,
                style=row_style,
            )

        total_num_threads = sum((p["num_threads"] or 0) for p in self.process_list_data)
        num_sleeping_processes = sum(
            p["status"] == "sleeping" for p in self.process_list_data
        )

        total_processes = len(self.process_list_data)
        if total_processes > self.visible_rows:
            scroll_info = (
                f"({self.current_scroll_position + 1}-{end_index} of {total_processes})"
            )
        else:
            scroll_info = f"({total_processes})"

        title_parts = [
            "[b]📋 Processes[/]",
            f"{total_processes} {scroll_info} ({total_num_threads} 🧵)",
            f"{num_sleeping_processes} 😴",
        ]

        focus_indicator = "🔍" if self.has_focus else "○"
        if self.is_interactive_mode:
            title_parts.append(
                f"[dim]{focus_indicator} ↑↓ | K kill | T terminate | R refresh[/]"
            )
        else:
            title_parts.append(f"[dim]{focus_indicator} Press I for interactive mode[/]")

        panel_title = " - ".join(title_parts)
        self.panel.title = panel_title

        border_style = "bright_white" if self.has_focus else "bright_black"
        self.panel.border_style = border_style

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
        max_scroll = max(0, len(self.process_list_data) - self.visible_rows)
        self.current_scroll_position = min(self.current_scroll_position, max_scroll)
        if len(self.process_list_data) < self.max_num_procs:
            self.collect_data()
        else:
            self.refresh_display()
