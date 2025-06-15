import psutil
from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widget import Widget
from textual.message import Message
from textual import events

from ._helpers import sizeof_fmt


def get_process_list(num_procs: int):
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
        # Remove process with PID 0. On Windows, that's SYSTEM IDLE, and we
        # don't want that to appear at the top of the list.
        # <https://twitter.com/andre_roberge/status/1488885893716975622/photo/1>
        processes = processes[1:]

    processes = [p.info for p in processes]

    processes = sorted(
        processes,
        # The item.info["cpu_percent"] can be `ad_value` (default None).
        # It gets assigned to a dict key in case AccessDenied or
        # ZombieProcess exception is raised when retrieving that particular
        # process information.
        key=lambda p: (p["cpu_percent"] or 0.0),
        reverse=True,
    )
    processes = processes[:num_procs]
    return processes


class ProcsList(Widget):
    """Interactive process list with arrow key navigation and actions."""
    
    # Make the widget focusable
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
        super().__init__(**kwargs)
        self.max_num_procs = 1000  # Increased to get more processes
        self.visible_rows = 10  # Will be calculated based on screen size
        self.selected_process_index = 0
        self.current_scroll_position = 0  # Track scrolling position (renamed to avoid conflict)
        self.process_list_data = []
        self.is_interactive_mode = True

    def on_mount(self):
        self.collect_data()
        self.set_interval(6.0, self.collect_data)
        # Auto-focus this widget when mounted
        self.focus()

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard navigation and actions with scrolling support."""
        if not self.is_interactive_mode or not self.process_list_data:
            return

        key_pressed = event.key
        
        if key_pressed == "up":
            if self.selected_process_index > 0:
                self.selected_process_index -= 1
                # Scroll up if selection moves above visible area
                if self.selected_process_index < self.current_scroll_position:
                    self.current_scroll_position = self.selected_process_index
            self.refresh_display()
            event.prevent_default()
            
        elif key_pressed == "down":
            max_index = len(self.process_list_data) - 1
            if self.selected_process_index < max_index:
                self.selected_process_index += 1
                # Scroll down if selection moves below visible area
                if self.selected_process_index >= self.current_scroll_position + self.visible_rows:
                    self.current_scroll_position = self.selected_process_index - self.visible_rows + 1
            self.refresh_display()
            event.prevent_default()
            
        elif key_pressed == "pageup" or key_pressed == "ctrl+u":
            # Page up - move selection up by visible rows
            self.selected_process_index = max(0, self.selected_process_index - self.visible_rows)
            self.current_scroll_position = max(0, self.current_scroll_position - self.visible_rows)
            self.refresh_display()
            event.prevent_default()
            
        elif key_pressed == "pagedown" or key_pressed == "ctrl+d":
            # Page down - move selection down by visible rows
            max_index = len(self.process_list_data) - 1
            self.selected_process_index = min(max_index, self.selected_process_index + self.visible_rows)
            self.current_scroll_position = min(
                max(0, len(self.process_list_data) - self.visible_rows),
                self.current_scroll_position + self.visible_rows
            )
            self.refresh_display()
            event.prevent_default()
            
        elif key_pressed == "home" or key_pressed == "ctrl+home":
            # Go to first process
            self.selected_process_index = 0
            self.current_scroll_position = 0
            self.refresh_display()
            event.prevent_default()
            
        elif key_pressed == "end" or key_pressed == "ctrl+end":
            # Go to last process
            max_index = len(self.process_list_data) - 1
            self.selected_process_index = max_index
            self.current_scroll_position = max(0, max_index - self.visible_rows + 1)
            self.refresh_display()
            event.prevent_default()
            
        elif key_pressed == "enter":
            if 0 <= self.selected_process_index < len(self.process_list_data):
                selected_process = self.process_list_data[self.selected_process_index]
                self.post_message(self.ProcessSelected(selected_process))
            event.prevent_default()
        elif key_pressed == "k":
            # Kill process
            if 0 <= self.selected_process_index < len(self.process_list_data):
                selected_process = self.process_list_data[self.selected_process_index]
                self.post_message(self.ProcessAction("kill", selected_process))
            event.prevent_default()
        elif key_pressed == "t":
            # Terminate process
            if 0 <= self.selected_process_index < len(self.process_list_data):
                selected_process = self.process_list_data[self.selected_process_index]
                self.post_message(self.ProcessAction("terminate", selected_process))
            event.prevent_default()
        elif key_pressed == "r":
            # Refresh process list
            self.collect_data()
            event.prevent_default()
        elif key_pressed == "i":
            # Toggle interactive mode
            self.is_interactive_mode = not self.is_interactive_mode
            self.refresh_display()
            event.prevent_default()

    def collect_data(self):
        self.process_list_data = get_process_list(self.max_num_procs)
        
        # Ensure selected index is still valid
        if self.selected_process_index >= len(self.process_list_data):
            self.selected_process_index = max(0, len(self.process_list_data) - 1)
        
        # Ensure scroll position is still valid
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
        
        # Set ratio=1 on all columns that should be expanded
        process_table.add_column(Text("PID", justify="left"), no_wrap=True, justify="right")
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

        # Calculate visible processes based on scroll position
        end_index = min(
            len(self.process_list_data), 
            self.current_scroll_position + self.visible_rows
        )
        visible_processes = self.process_list_data[self.current_scroll_position:end_index]

        for local_index, process_info in enumerate(visible_processes):
            # Calculate actual index in the full process list
            actual_index = self.current_scroll_position + local_index
            
            # Determine if this row should be highlighted
            is_selected_row = (
                self.is_interactive_mode and 
                actual_index == self.selected_process_index
            )
            
            # Extract process information
            process_id = process_info["pid"]
            process_id_str = "" if process_id is None else str(process_id)
            
            process_name = process_info["name"]
            if process_name is None:
                process_name = ""
            
            num_threads = process_info["num_threads"]
            num_threads_str = "" if num_threads is None else str(num_threads)
            
            memory_info = process_info["memory_info"]
            memory_info_str = (
                "" if memory_info is None 
                else sizeof_fmt(memory_info.rss, suffix="", sep="")
            )
            
            cpu_percentage = process_info["cpu_percent"]
            cpu_percentage_str = "" if cpu_percentage is None else f"{cpu_percentage:.1f}"
            
            # Apply selection styling
            row_style = None
            if is_selected_row:
                row_style = "black on white"
                # Add selection indicator
                process_name = f"▶ {process_name}"
            
            process_table.add_row(
                process_id_str,
                process_name,
                num_threads_str,
                memory_info_str,
                cpu_percentage_str,
                style=row_style,
            )

        # Calculate summary statistics
        total_num_threads = sum((p["num_threads"] or 0) for p in self.process_list_data)
        num_sleeping_processes = sum(p["status"] == "sleeping" for p in self.process_list_data)
        
        # Calculate scroll indicator
        total_processes = len(self.process_list_data)
        if total_processes > self.visible_rows:
            scroll_info = f"({self.current_scroll_position + 1}-{end_index} of {total_processes})"
        else:
            scroll_info = f"({total_processes})"
        
        # Build title with interactive mode indicator and scroll info
        title_parts = [
            "[b]📋 Processes[/]",
            f"{total_processes} {scroll_info} ({total_num_threads} 🧵)",
            f"{num_sleeping_processes} 😴"
        ]
        
        if self.is_interactive_mode:
            title_parts.append("[dim]↑↓ nav | PgUp/PgDn page | Home/End | Enter select | K kill | T term | R refresh[/]")
        else:
            title_parts.append("[dim]Press I for interactive mode[/]")
            
        panel_title = " - ".join(title_parts)

        # Use different border style if focused
        border_style = "bright_white" if self.has_focus else "bright_black"

        self.panel = Panel(
            process_table,
            title=panel_title,
            title_align="left",
            border_style=border_style,
            box=box.SQUARE,
        )

        self.refresh()

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

    def render(self) -> Panel:
        return getattr(self, 'panel', Panel("Loading processes...", title="📋 Processes"))

    async def on_resize(self, event):
        # Calculate visible rows based on available height
        # Subtract 3 for borders and header
        new_visible_rows = max(5, self.size.height - 3)
        self.visible_rows = new_visible_rows
        
        # Adjust max processes to get more data for scrolling
        # Get at least 3x the visible rows, but cap at reasonable number for performance
        self.max_num_procs = min(3000, max(500, new_visible_rows * 3))
        
        # Ensure scroll position is still valid after resize
        max_scroll = max(0, len(self.process_list_data) - self.visible_rows)
        self.current_scroll_position = min(self.current_scroll_position, max_scroll)
        
        # Refresh data if we need more processes
        if len(self.process_list_data) < self.max_num_procs:
            self.collect_data()
        else:
            self.refresh_display()
