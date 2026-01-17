"""Process TUI - Interactive process viewer."""

from __future__ import annotations

import psutil
from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Footer, Header

from .._helpers import sizeof_fmt
from ..widgets.process_sorter import SortManager
from ..widgets.processes import get_process_list


class ProcessListPanel(Widget):
    """Process list panel on the left."""

    can_focus = True

    class ProcessSelected(Message):
        def __init__(self, process_info: dict) -> None:
            self.process_info = process_info
            super().__init__()

    class ProcessAction(Message):
        def __init__(self, action: str, process_info: dict) -> None:
            self.action = action
            self.process_info = process_info
            super().__init__()

    class KillRequest(Message):
        def __init__(self, process_info: dict) -> None:
            self.process_info = process_info
            super().__init__()

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
            mem_str = (
                "" if mem_info is None else sizeof_fmt(mem_info.rss, suffix="", sep="")
            )

            cpu = proc.get("cpu_percent", 0) or 0
            cpu_str = f"{cpu:.1f}"

            style = "black on white" if is_selected else None
            table.add_row(pid, name, mem_str, cpu_str, style=style)

        total = len(self.processes)
        if total > self.visible_rows:
            scroll_info = f"({self.scroll_position + 1}-{end_index} of {total})"
        else:
            scroll_info = f"({total})"

        if self.sort_manager.sort_mode_active:
            current_col = self.sort_manager.current_column().display_name
            direction = self.sort_manager.sort_direction.icon()
            columns_display = " | ".join(
                col.display_name for col in self.sort_manager.COLUMNS[:4]
            )
            title = f"[bold yellow on black] ORDER BY [/] - [bold cyan]{current_col}[/] [bold magenta]{direction}[/] - {columns_display}"
            border_style = "yellow" if self.has_focus else "bright_yellow"
        else:
            sort_indicator = self.sort_manager.get_sort_indicator_str()
            help_text = "O order | ↑↓ | ⏎ info | K kill | T term | R refresh"
            title = f"[bold]Processes {scroll_info}[/] - [cyan]Sort: {sort_indicator}[/] - [dim]{help_text}[/]"
            border_style = "bright_cyan" if self.has_focus else "dim"

        return Panel(table, title=title, border_style=border_style)

    def handle_navigation_keys(self, key_pressed: str) -> bool:
        if key_pressed == "up":
            if self.selected_index > 0:
                self.selected_index -= 1
                if self.selected_index < self.scroll_position:
                    self.scroll_position = self.selected_index
                self.refresh()
            return True
        elif key_pressed == "down":
            if self.selected_index < len(self.processes) - 1:
                self.selected_index += 1
                if self.selected_index >= self.scroll_position + self.visible_rows:
                    self.scroll_position = self.selected_index - self.visible_rows + 1
                self.refresh()
            return True
        elif key_pressed in ("pageup", "ctrl+u"):
            self.selected_index = max(0, self.selected_index - self.visible_rows)
            self.scroll_position = max(0, self.scroll_position - self.visible_rows)
            self.refresh()
            return True
        elif key_pressed in ("pagedown", "ctrl+d"):
            max_index = len(self.processes) - 1
            self.selected_index = min(
                max_index, self.selected_index + self.visible_rows
            )
            max_scroll = max(0, len(self.processes) - self.visible_rows)
            self.scroll_position = min(
                max_scroll, self.scroll_position + self.visible_rows
            )
            self.refresh()
            return True
        elif key_pressed in ("home", "ctrl+home"):
            self.selected_index = 0
            self.scroll_position = 0
            self.refresh()
            return True
        elif key_pressed in ("end", "ctrl+end"):
            max_index = len(self.processes) - 1
            self.selected_index = max_index
            self.scroll_position = max(0, max_index - self.visible_rows + 1)
            self.refresh()
            return True
        return False

    def handle_sort_mode_keys(self, key_pressed: str) -> bool:
        if key_pressed == "left":
            self.sort_manager.navigate_columns(-1)
            self.refresh()
            return True
        elif key_pressed == "right":
            self.sort_manager.navigate_columns(1)
            self.refresh()
            return True
        elif key_pressed == "enter":
            self.sort_manager.toggle_column(self.sort_manager.active_column_index)
            self.refresh_processes()
            return True
        elif key_pressed in ("escape", "o"):
            self.sort_manager.exit_sort_mode()
            self.refresh()
            return True
        return False

    def handle_action_keys(self, key_pressed: str) -> bool:
        if key_pressed == "o":
            self.sort_manager.enter_sort_mode()
            self.refresh()
            return True
        elif key_pressed == "enter":
            if 0 <= self.selected_index < len(self.processes):
                selected_process = self.processes[self.selected_index]
                self.post_message(self.ProcessSelected(selected_process))
            return True
        elif key_pressed == "k":
            if 0 <= self.selected_index < len(self.processes):
                selected_process = self.processes[self.selected_index]
                self.post_message(self.KillRequest(selected_process))
            return True
        elif key_pressed == "t":
            if 0 <= self.selected_index < len(self.processes):
                selected_process = self.processes[self.selected_index]
                self.post_message(self.ProcessAction("terminate", selected_process))
            return True
        elif key_pressed == "r":
            self.refresh_processes()
            return True
        return False

    def on_key(self, event: events.Key):
        if not self.has_focus:
            return

        if (
            hasattr(self.app, "_waiting_for_kill_confirmation")
            and self.app._waiting_for_kill_confirmation
        ):
            return

        if not self.processes:
            return

        key_pressed = event.key

        if self.sort_manager.sort_mode_active:
            if self.handle_sort_mode_keys(key_pressed):
                event.prevent_default()
                return
        else:
            if self.handle_navigation_keys(key_pressed):
                event.prevent_default()
                return
            if self.handle_action_keys(key_pressed):
                event.prevent_default()
                return

    def on_resize(self, event):
        self.visible_rows = max(10, self.size.height - 3)
        self.refresh()


class PortListPanel(Widget):
    """Port list panel showing open ports and their processes."""

    can_focus = True

    class ProcessSelected(Message):
        def __init__(self, port_info: dict) -> None:
            self.port_info = port_info
            super().__init__()

    class ProcessAction(Message):
        def __init__(self, action: str, port_info: dict) -> None:
            self.action = action
            self.port_info = port_info
            super().__init__()

    class KillRequest(Message):
        def __init__(self, port_info: dict) -> None:
            self.port_info = port_info
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ports = []
        self.selected_index = 0
        self.scroll_position = 0
        self.visible_rows = 10
        self.sort_by = "port"
        self.sort_reverse = False

    def on_mount(self):
        self.refresh_ports()
        self.set_interval(3.0, self.refresh_ports)

    def refresh_ports(self):
        """Get all listening ports and their processes."""
        port_map = {}

        try:
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "LISTEN" and conn.laddr:
                    port = conn.laddr.port
                    if port not in port_map:
                        try:
                            if conn.pid:
                                proc = psutil.Process(conn.pid)
                                port_map[port] = {
                                    "port": port,
                                    "pid": conn.pid,
                                    "name": proc.name(),
                                    "address": conn.laddr.ip,
                                }
                            else:
                                port_map[port] = {
                                    "port": port,
                                    "pid": None,
                                    "name": "System",
                                    "address": conn.laddr.ip,
                                }
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            port_map[port] = {
                                "port": port,
                                "pid": None,
                                "name": "Unknown",
                                "address": conn.laddr.ip,
                            }
        except (psutil.AccessDenied, PermissionError):
            # On macOS, net_connections requires root privileges
            # Fall back to empty list
            pass

        ports_list = list(port_map.values())

        if self.sort_by == "port":
            ports_list.sort(key=lambda x: x["port"], reverse=self.sort_reverse)
        elif self.sort_by == "address":
            ports_list.sort(key=lambda x: x["address"], reverse=self.sort_reverse)
        elif self.sort_by == "name":
            ports_list.sort(
                key=lambda x: (x["name"] or "").lower(), reverse=self.sort_reverse
            )
        elif self.sort_by == "pid":
            ports_list.sort(key=lambda x: x["pid"] or 0, reverse=self.sort_reverse)

        self.ports = ports_list

        if self.selected_index >= len(self.ports):
            self.selected_index = max(0, len(self.ports) - 1)
        max_scroll = max(0, len(self.ports) - self.visible_rows)
        self.scroll_position = min(self.scroll_position, max_scroll)
        self.refresh()

    def render(self):
        if not self.ports:
            content = Align.center(
                Text("No ports detected\n(May require sudo on macOS)", style="dim"),
                vertical="middle",
            )
            border_style = "bright_cyan" if self.has_focus else "dim"
            return Panel(
                content,
                title="[bold]Listening Ports (0)[/]",
                border_style=border_style,
            )

        table = Table(
            show_header=True,
            header_style="bold cyan",
            box=None,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("Port", justify="right", width=7)
        table.add_column("Address", justify="left", width=15)
        table.add_column("Process", style="aquamarine3", no_wrap=True, ratio=1)
        table.add_column("PID", justify="right", width=8)

        end_index = min(len(self.ports), self.scroll_position + self.visible_rows)
        visible = self.ports[self.scroll_position : end_index]

        for local_idx, port_info in enumerate(visible):
            actual_idx = self.scroll_position + local_idx
            is_selected = self.has_focus and actual_idx == self.selected_index

            port = str(port_info["port"])
            address = port_info["address"]
            name = port_info["name"]
            if is_selected:
                name = f"▶ {name}"

            pid = str(port_info["pid"]) if port_info["pid"] else "-"

            style = "black on white" if is_selected else None
            table.add_row(port, address, name, pid, style=style)

        total = len(self.ports)
        if total > self.visible_rows:
            scroll_info = f"({self.scroll_position + 1}-{end_index} of {total})"
        else:
            scroll_info = f"({total})"

        sort_dir = "↓" if self.sort_reverse else "↑"
        help_text = "O sort | S dir | ↑↓ | ⏎ info | K kill | T term | R refresh"
        title = f"[bold]Ports {scroll_info}[/] - [cyan]Sort: {self.sort_by} {sort_dir}[/] - [dim]{help_text}[/]"
        border_style = "bright_cyan" if self.has_focus else "dim"

        return Panel(table, title=title, border_style=border_style)

    def handle_navigation_keys(self, key_pressed: str) -> bool:
        if key_pressed == "up":
            if self.selected_index > 0:
                self.selected_index -= 1
                if self.selected_index < self.scroll_position:
                    self.scroll_position = self.selected_index
                self.refresh()
            return True
        elif key_pressed == "down":
            if self.selected_index < len(self.ports) - 1:
                self.selected_index += 1
                if self.selected_index >= self.scroll_position + self.visible_rows:
                    self.scroll_position = self.selected_index - self.visible_rows + 1
                self.refresh()
            return True
        elif key_pressed in ("pageup", "ctrl+u"):
            self.selected_index = max(0, self.selected_index - self.visible_rows)
            self.scroll_position = max(0, self.scroll_position - self.visible_rows)
            self.refresh()
            return True
        elif key_pressed in ("pagedown", "ctrl+d"):
            max_index = len(self.ports) - 1
            self.selected_index = min(
                max_index, self.selected_index + self.visible_rows
            )
            max_scroll = max(0, len(self.ports) - self.visible_rows)
            self.scroll_position = min(
                max_scroll, self.scroll_position + self.visible_rows
            )
            self.refresh()
            return True
        elif key_pressed in ("home", "ctrl+home"):
            self.selected_index = 0
            self.scroll_position = 0
            self.refresh()
            return True
        elif key_pressed in ("end", "ctrl+end"):
            max_index = len(self.ports) - 1
            self.selected_index = max_index
            self.scroll_position = max(0, max_index - self.visible_rows + 1)
            self.refresh()
            return True
        return False

    def handle_action_keys(self, key_pressed: str) -> bool:
        if key_pressed == "o":
            sort_options = ["port", "address", "name", "pid"]
            current_idx = sort_options.index(self.sort_by)
            next_idx = (current_idx + 1) % len(sort_options)
            self.sort_by = sort_options[next_idx]
            self.sort_reverse = False
            self.refresh_ports()
            return True
        elif key_pressed == "s":
            self.sort_reverse = not self.sort_reverse
            self.refresh_ports()
            return True
        elif key_pressed == "enter":
            if 0 <= self.selected_index < len(self.ports):
                selected_port = self.ports[self.selected_index]
                self.post_message(self.ProcessSelected(selected_port))
            return True
        elif key_pressed == "k":
            if 0 <= self.selected_index < len(self.ports):
                selected_port = self.ports[self.selected_index]
                if selected_port.get("pid"):
                    self.post_message(self.KillRequest(selected_port))
            return True
        elif key_pressed == "t":
            if 0 <= self.selected_index < len(self.ports):
                selected_port = self.ports[self.selected_index]
                if selected_port.get("pid"):
                    self.post_message(self.ProcessAction("terminate", selected_port))
            return True
        elif key_pressed == "r":
            self.refresh_ports()
            return True
        return False

    def on_key(self, event: events.Key):
        if not self.has_focus:
            return

        if (
            hasattr(self.app, "_waiting_for_kill_confirmation")
            and self.app._waiting_for_kill_confirmation
        ):
            return

        if not self.ports:
            return

        key_pressed = event.key

        if self.handle_navigation_keys(key_pressed):
            event.prevent_default()
            return
        if self.handle_action_keys(key_pressed):
            event.prevent_default()
            return

    def on_resize(self, event):
        self.visible_rows = max(5, self.size.height - 3)
        self.refresh()


class DevEnvPanel(Widget):
    """Development environment detection panel."""

    can_focus = True

    class DevEnvSelected(Message):
        def __init__(self, dev_env: dict) -> None:
            self.dev_env = dev_env
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dev_servers = []
        self.selected_index = 0
        self.sort_by = "type"
        self.sort_reverse = False

    def on_mount(self):
        self.refresh_dev_env()
        self.set_interval(5.0, self.refresh_dev_env)

    def refresh_dev_env(self):  # noqa: C901
        """Detect development servers and collect metrics."""
        dev_servers_by_type = {}

        # Common dev server patterns
        dev_patterns = {
            "node": ["node", "npm", "yarn", "pnpm", "next", "vite", "webpack"],
            "python": ["python", "uvicorn", "gunicorn", "flask", "django", "fastapi"],
            "docker": ["docker", "containerd", "dockerd"],
            "ruby": ["ruby", "rails", "puma"],
            "go": ["go", "air"],
            "rust": ["cargo"],
        }

        for proc in psutil.process_iter(
            ["pid", "name", "cmdline", "cpu_percent", "memory_info"]
        ):
            try:
                proc_info = proc.info
                name = proc_info.get("name", "").lower()
                cmdline = proc_info.get("cmdline", [])
                cmdline_str = " ".join(cmdline).lower() if cmdline else ""

                # Check if this is a dev server
                env_type = None
                for env, patterns in dev_patterns.items():
                    for pattern in patterns:
                        if pattern in name or pattern in cmdline_str:
                            env_type = env
                            break
                    if env_type:
                        break

                if env_type:
                    # Get listening ports for this process
                    ports = []
                    try:
                        connections = proc.connections(kind="inet")
                        for conn in connections:
                            if conn.status == "LISTEN" and conn.laddr:
                                ports.append(conn.laddr.port)
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass

                    mem_info = proc_info.get("memory_info")
                    mem_mb = mem_info.rss / (1024 * 1024) if mem_info else 0
                    cpu = proc_info.get("cpu_percent", 0) or 0

                    # Group by type
                    if env_type not in dev_servers_by_type:
                        dev_servers_by_type[env_type] = {
                            "type": env_type,
                            "count": 0,
                            "ports": set(),
                            "cpu": 0,
                            "memory_mb": 0,
                            "processes": [],
                        }

                    dev_servers_by_type[env_type]["count"] += 1
                    dev_servers_by_type[env_type]["ports"].update(ports)
                    dev_servers_by_type[env_type]["cpu"] += cpu
                    dev_servers_by_type[env_type]["memory_mb"] += mem_mb
                    dev_servers_by_type[env_type]["processes"].append(
                        proc_info.get("name")
                    )

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Convert to list and sort
        dev_servers_list = [
            {
                "type": data["type"],
                "count": data["count"],
                "ports": sorted(data["ports"]),
                "cpu": data["cpu"],
                "memory_mb": data["memory_mb"],
                "processes": data["processes"][:3],  # Keep first 3 process names
            }
            for data in dev_servers_by_type.values()
        ]

        if self.sort_by == "type":
            dev_servers_list.sort(key=lambda x: x["type"], reverse=self.sort_reverse)
        elif self.sort_by == "count":
            dev_servers_list.sort(key=lambda x: x["count"], reverse=self.sort_reverse)
        elif self.sort_by == "cpu":
            dev_servers_list.sort(key=lambda x: x["cpu"], reverse=self.sort_reverse)
        elif self.sort_by == "memory":
            dev_servers_list.sort(
                key=lambda x: x["memory_mb"], reverse=self.sort_reverse
            )

        self.dev_servers = dev_servers_list

        if self.selected_index >= len(self.dev_servers):
            self.selected_index = max(0, len(self.dev_servers) - 1)

        self.refresh()

    def render(self):
        if not self.dev_servers:
            content = Align.center(
                Text("No dev servers detected", style="dim"), vertical="middle"
            )
            border_style = "bright_cyan" if self.has_focus else "dim"
            return Panel(
                content,
                title="[bold]Development Environment[/]",
                border_style=border_style,
            )

        table = Table(
            show_header=True,
            header_style="bold cyan",
            box=None,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("Type", justify="left", width=12)
        table.add_column("Processes", style="aquamarine3", no_wrap=True, ratio=1)
        table.add_column("Ports", justify="left", width=15)
        table.add_column("CPU%", justify="right", width=6)
        table.add_column("Mem", justify="right", width=8)

        for idx, server in enumerate(self.dev_servers[:15]):  # Show max 15
            is_selected = self.has_focus and idx == self.selected_index

            env_type = f"{server['type'].upper()} ({server['count']})"

            processes = server["processes"]
            if len(processes) > 3:
                name = ", ".join(processes[:3]) + "..."
            else:
                name = ", ".join(processes) if processes else "-"

            if is_selected:
                name = f"▶ {name}"

            ports = ", ".join(map(str, server["ports"])) if server["ports"] else "-"
            cpu = f"{server['cpu']:.1f}"
            mem = sizeof_fmt(server["memory_mb"] * 1024 * 1024, suffix="", sep="")

            style = "black on white" if is_selected else None
            table.add_row(env_type, name, ports, cpu, mem, style=style)

        total_count = sum((s["count"] for s in self.dev_servers), start=0)
        total_types = len(self.dev_servers)
        sort_dir = "↓" if self.sort_reverse else "↑"
        help_text = "O sort | S dir | ↑↓ | ⏎ info | R refresh"
        title = f"[bold]Dev Env ({total_types} types, {total_count} procs)[/] - [cyan]Sort: {self.sort_by} {sort_dir}[/] - [dim]{help_text}[/]"
        border_style = "bright_cyan" if self.has_focus else "dim"

        return Panel(table, title=title, border_style=border_style)

    def handle_navigation_keys(self, key_pressed: str) -> bool:
        if key_pressed == "up":
            if self.selected_index > 0:
                self.selected_index -= 1
                self.refresh()
            return True
        elif key_pressed == "down":
            if self.selected_index < len(self.dev_servers) - 1:
                self.selected_index += 1
                self.refresh()
            return True
        elif key_pressed in ("home", "ctrl+home"):
            self.selected_index = 0
            self.refresh()
            return True
        elif key_pressed in ("end", "ctrl+end"):
            self.selected_index = max(0, len(self.dev_servers) - 1)
            self.refresh()
            return True
        return False

    def handle_action_keys(self, key_pressed: str) -> bool:
        if key_pressed == "o":
            sort_options = ["type", "count", "cpu", "memory"]
            current_idx = sort_options.index(self.sort_by)
            next_idx = (current_idx + 1) % len(sort_options)
            self.sort_by = sort_options[next_idx]
            self.sort_reverse = False
            self.refresh_dev_env()
            return True
        elif key_pressed == "s":
            self.sort_reverse = not self.sort_reverse
            self.refresh_dev_env()
            return True
        elif key_pressed == "enter":
            if 0 <= self.selected_index < len(self.dev_servers):
                selected_env = self.dev_servers[self.selected_index]
                self.post_message(self.DevEnvSelected(selected_env))
            return True
        elif key_pressed == "r":
            self.refresh_dev_env()
            return True
        return False

    def on_key(self, event: events.Key):
        if not self.has_focus:
            return

        if not self.dev_servers:
            return

        key_pressed = event.key

        if self.handle_navigation_keys(key_pressed):
            event.prevent_default()
            return
        if self.handle_action_keys(key_pressed):
            event.prevent_default()
            return


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
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("tab", "focus_next", "Next Section"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            yield ProcessListPanel(id="left-panel")

            with Vertical(id="right-container"):
                yield PortListPanel(id="right-top")
                yield DevEnvPanel(id="right-bottom")

        yield Footer()

    def on_mount(self):
        self.title = "SOT PS"
        self.sub_title = "Interactive Process Viewer"
        self.query_one("#left-panel").focus()
        self._waiting_for_kill_confirmation = False
        self.pending_kill = None

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

    def on_key(self, event: events.Key) -> None:
        if self._waiting_for_kill_confirmation and self.pending_kill:
            if event.key == "y":
                self._waiting_for_kill_confirmation = False
                self._kill_process(self.pending_kill)
            else:
                self._waiting_for_kill_confirmation = False
                self.notify("❌ Kill cancelled", timeout=2)
            event.prevent_default()

    def on_process_list_panel_process_selected(
        self, message: ProcessListPanel.ProcessSelected
    ) -> None:
        from .._process_utils import format_process_details

        details = format_process_details(message.process_info)
        self.notify("\n".join(details), timeout=5)

    def on_process_list_panel_kill_request(
        self, message: ProcessListPanel.KillRequest
    ) -> None:
        proc = message.process_info
        self.pending_kill = proc
        self.notify(
            f"⚠️  KILL {proc.get('name', 'Unknown')}? Press 'y' to confirm, any key to cancel",
            severity="error",
            timeout=10,
        )
        self._waiting_for_kill_confirmation = True
        self.set_timer(10.0, self._reset_confirmation)

    def on_process_list_panel_process_action(
        self, message: ProcessListPanel.ProcessAction
    ) -> None:
        from .._process_utils import kill_process, terminate_process

        proc = message.process_info
        action = message.action
        pid = proc.get("pid")
        name = proc.get("name", "Unknown")

        if not isinstance(pid, int):
            self.notify("❌ Invalid process ID", severity="error", timeout=3)
            return

        if action == "kill":
            result = kill_process(pid, name)
        elif action == "terminate":
            result = terminate_process(pid, name)
        else:
            self.notify(f"❓ Unknown action: {action}", severity="error", timeout=3)
            return

        self.notify(result.message, severity=result.severity, timeout=4)

    def on_port_list_panel_process_selected(
        self, message: PortListPanel.ProcessSelected
    ) -> None:
        port_info = message.port_info
        details = [f"🔌 Port {port_info['port']} on {port_info['address']}"]
        details.append(f"📋 Process: {port_info['name']}")
        if port_info["pid"]:
            details.append(f"PID: {port_info['pid']}")
        self.notify("\n".join(details), timeout=5)

    def on_port_list_panel_kill_request(
        self, message: PortListPanel.KillRequest
    ) -> None:
        port_info = message.port_info
        if not port_info.get("pid"):
            self.notify(
                "❌ No process associated with this port", severity="error", timeout=3
            )
            return
        proc = {"pid": port_info["pid"], "name": port_info["name"]}
        self.pending_kill = proc
        self.notify(
            f"⚠️  KILL {port_info['name']} (Port {port_info['port']})? Press 'y' to confirm, any key to cancel",
            severity="error",
            timeout=10,
        )
        self._waiting_for_kill_confirmation = True
        self.set_timer(10.0, self._reset_confirmation)

    def on_port_list_panel_process_action(
        self, message: PortListPanel.ProcessAction
    ) -> None:
        from .._process_utils import kill_process, terminate_process

        port_info = message.port_info
        action = message.action
        pid = port_info.get("pid")
        name = port_info["name"]

        if not isinstance(pid, int):
            self.notify(
                "❌ No process associated with this port", severity="error", timeout=3
            )
            return

        if action == "kill":
            result = kill_process(pid, name)
        elif action == "terminate":
            result = terminate_process(pid, name)
        else:
            self.notify(f"❓ Unknown action: {action}", severity="error", timeout=3)
            return

        self.notify(result.message, severity=result.severity, timeout=4)

    def on_dev_env_panel_dev_env_selected(
        self, message: DevEnvPanel.DevEnvSelected
    ) -> None:
        env = message.dev_env
        details = [f"🔧 {env['type'].upper()} Environment"]
        details.append(f"Processes: {env['count']}")
        if env["ports"]:
            details.append(f"Ports: {', '.join(map(str, env['ports']))}")
        details.append(f"CPU: {env['cpu']:.1f}%")
        details.append(
            f"Memory: {sizeof_fmt(env['memory_mb'] * 1024 * 1024, suffix='', sep='')}"
        )
        self.notify("\n".join(details), timeout=5)

    def _kill_process(self, proc: dict) -> None:
        from .._process_utils import kill_process

        pid = proc.get("pid")
        name = proc.get("name", "Unknown")

        if not isinstance(pid, int):
            self.notify("❌ Invalid process ID", severity="error", timeout=3)
            return

        result = kill_process(pid, name)
        self.notify(result.message, severity=result.severity, timeout=4)

    def _reset_confirmation(self):
        if self._waiting_for_kill_confirmation:
            self._waiting_for_kill_confirmation = False
            self.notify("❌ Kill action expired", severity="error", timeout=2)
