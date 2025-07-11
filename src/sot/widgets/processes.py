"""
Processes Widget

Displays interactive process list with keyboard navigation, process management, and network usage.
"""

import psutil
from rich.table import Table
from rich.text import Text
from textual import events
from textual.message import Message

from .._helpers import sizeof_fmt
from .base_widget import BaseWidget


def get_process_list(num_procs: int):
    """Get list of running processes sorted by CPU usage with network I/O information."""
    processes = []
    
    for proc in psutil.process_iter([
        "pid",
        "name", 
        "username",
        "cmdline",
        "cpu_percent",
        "num_threads",
        "memory_info",
        "status",
    ]):
        try:
            proc_info = proc.info.copy()
            
            # Get network connections for this process
            try:
                connections = proc.connections(kind='inet')
                proc_info['num_connections'] = len(connections)
                
                # Try to get network I/O counters (Linux only)
                try:
                    io_counters = proc.io_counters()
                    if hasattr(io_counters, 'read_bytes') and hasattr(io_counters, 'write_bytes'):
                        # Note: these are total I/O bytes (file + network), not just network
                        # but it's the best approximation we can get per-process
                        proc_info['io_read_bytes'] = io_counters.read_bytes
                        proc_info['io_write_bytes'] = io_counters.write_bytes
                    else:
                        proc_info['io_read_bytes'] = 0
                        proc_info['io_write_bytes'] = 0
                except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                    proc_info['io_read_bytes'] = 0
                    proc_info['io_write_bytes'] = 0
                    
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                proc_info['num_connections'] = 0
                proc_info['io_read_bytes'] = 0
                proc_info['io_write_bytes'] = 0
                
            processes.append(proc_info)
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Filter out kernel thread with PID 0 if present
    if processes and processes[0].get('pid') == 0:
        processes = processes[1:]

    # Sort by CPU usage
    processes = sorted(
        processes,
        key=lambda p: (p.get("cpu_percent") or 0.0),
        reverse=True,
    )
    
    return processes[:num_procs]


class ProcessesWidget(BaseWidget):
    """Interactive process list with arrow key navigation, actions, and network monitoring."""

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
        self.previous_process_data = {}  # Store previous I/O data for rate calculation
        self.is_interactive_mode = True
        self.show_network_details = True  # Toggle for network column visibility

    def on_mount(self):
        self.collect_data()
        self.set_interval(6.0, self.collect_data)
        self.focus()

    def calculate_io_rates(self, current_processes):
        """Calculate I/O rates by comparing with previous data."""
        interval_seconds = 6.0  # Match the collection interval
        
        for proc in current_processes:
            pid = proc.get('pid')
            if not pid:
                continue
                
            current_read = proc.get('io_read_bytes', 0)
            current_write = proc.get('io_write_bytes', 0)
            
            if pid in self.previous_process_data:
                prev_read = self.previous_process_data[pid].get('io_read_bytes', 0)
                prev_write = self.previous_process_data[pid].get('io_write_bytes', 0)
                
                read_rate = max(0, (current_read - prev_read) / interval_seconds)
                write_rate = max(0, (current_write - prev_write) / interval_seconds)
                
                proc['io_read_rate'] = read_rate
                proc['io_write_rate'] = write_rate
                proc['total_io_rate'] = read_rate + write_rate
            else:
                proc['io_read_rate'] = 0
                proc['io_write_rate'] = 0
                proc['total_io_rate'] = 0
        
        # Update previous data
        self.previous_process_data = {
            proc.get('pid'): {
                'io_read_bytes': proc.get('io_read_bytes', 0),
                'io_write_bytes': proc.get('io_write_bytes', 0)
            }
            for proc in current_processes
            if proc.get('pid')
        }

    def handle_navigation_keys(self, key_pressed: str) -> bool:
        """Handle navigation keys (up, down, page up/down, home, end). Returns True if handled."""
        if key_pressed == "up":
            if self.selected_process_index > 0:
                self.selected_process_index -= 1
                if self.selected_process_index < self.current_scroll_position:
                    self.current_scroll_position = self.selected_process_index
                self.refresh_display()
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
                self.refresh_display()
            return True

        elif key_pressed == "pageup" or key_pressed == "ctrl+u":
            self.selected_process_index = max(
                0, self.selected_process_index - self.visible_rows
            )
            self.current_scroll_position = max(
                0, self.current_scroll_position - self.visible_rows
            )
            self.refresh_display()
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
            self.refresh_display()
            return True

        elif key_pressed == "home" or key_pressed == "ctrl+home":
            self.selected_process_index = 0
            self.current_scroll_position = 0
            self.refresh_display()
            return True

        elif key_pressed == "end" or key_pressed == "ctrl+end":
            max_index = len(self.process_list_data) - 1
            self.selected_process_index = max_index
            self.current_scroll_position = max(0, max_index - self.visible_rows + 1)
            self.refresh_display()
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
            self.refresh_display()
            return True
        elif key_pressed == "n":
            self.show_network_details = not self.show_network_details
            self.refresh_display()
            return True

        return False

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard navigation and actions with scrolling support."""
        if not self.is_interactive_mode or not self.process_list_data:
            return

        key_pressed = event.key

        # Handle navigation keys
        if self.handle_navigation_keys(key_pressed):
            event.prevent_default()
            return

        # Handle action keys
        if self.handle_action_keys(key_pressed):
            event.prevent_default()
            return

    def collect_data(self):
        new_process_data = get_process_list(self.max_num_procs)
        self.calculate_io_rates(new_process_data)
        self.process_list_data = new_process_data

        # Ensure selected index is within bounds
        if self.selected_process_index >= len(self.process_list_data):
            self.selected_process_index = max(0, len(self.process_list_data) - 1)

        # Ensure scroll position is within bounds
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

        # Add columns based on what we want to show
        process_table.add_column(
            Text("PID", justify="left"), no_wrap=True, justify="right", width=8
        )
        process_table.add_column("Process", style="aquamarine3", no_wrap=True, ratio=1)
        process_table.add_column(
            Text("🧵", justify="left"),
            style="aquamarine3", 
            no_wrap=True,
            justify="right",
            width=4
        )
        process_table.add_column(
            Text("Memory", justify="left"),
            style="aquamarine3",
            no_wrap=True,
            justify="right", 
            width=8
        )
        
        if self.show_network_details:
            process_table.add_column(
                Text("Net I/O", justify="left"),
                style="yellow",
                no_wrap=True,
                justify="right",
                width=9
            )
            process_table.add_column(
                Text("Conn", justify="left"),
                style="sky_blue3",
                no_wrap=True,
                justify="right",
                width=4
            )
        
        process_table.add_column(
            Text("CPU %", style="u", justify="left"),
            no_wrap=True,
            justify="right",
            width=7
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

            # Network usage formatting
            if self.show_network_details:
                total_io_rate = process_info.get('total_io_rate', 0)
                if total_io_rate > 0:
                    net_io_str = sizeof_fmt(total_io_rate, fmt=".1f", suffix="", sep="") + "/s"
                else:
                    net_io_str = "-"
                
                num_connections = process_info.get('num_connections', 0)
                connections_str = str(num_connections) if num_connections > 0 else "-"

            row_style = None
            if is_selected_row:
                row_style = "black on white"
                process_name = f"▶ {process_name}"

            # Build row data based on what columns we're showing
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

        # Calculate summary statistics
        total_num_threads = sum((p.get("num_threads") or 0) for p in self.process_list_data)
        num_sleeping_processes = sum(
            p.get("status") == "sleeping" for p in self.process_list_data
        )
        total_connections = sum((p.get("num_connections") or 0) for p in self.process_list_data)

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
        
        if self.show_network_details:
            title_parts.append(f"{total_connections} 🌐")

        focus_indicator = "🔍" if self.has_focus else "○"
        if self.is_interactive_mode:
            help_text = "↑↓ | ⏎ info | K kill | T terminate | R refresh"
            if self.show_network_details:
                help_text += " | N hide net"
            else:
                help_text += " | N show net"
            title_parts.append(f"[dim]{focus_indicator} {help_text}[/]")
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
