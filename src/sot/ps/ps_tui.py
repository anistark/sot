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


class PortListPanel(Widget):
    """Port list panel showing open ports and their processes."""

    can_focus = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ports = []
        self.selected_index = 0
        self.scroll_position = 0
        self.visible_rows = 10

    def on_mount(self):
        self.refresh_ports()
        self.set_interval(3.0, self.refresh_ports)

    def refresh_ports(self):
        """Get all listening ports and their processes."""
        port_map = {}

        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'LISTEN' and conn.laddr:
                    port = conn.laddr.port
                    if port not in port_map:
                        try:
                            if conn.pid:
                                proc = psutil.Process(conn.pid)
                                port_map[port] = {
                                    'port': port,
                                    'pid': conn.pid,
                                    'name': proc.name(),
                                    'address': conn.laddr.ip,
                                }
                            else:
                                port_map[port] = {
                                    'port': port,
                                    'pid': None,
                                    'name': 'System',
                                    'address': conn.laddr.ip,
                                }
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            port_map[port] = {
                                'port': port,
                                'pid': None,
                                'name': 'Unknown',
                                'address': conn.laddr.ip,
                            }
        except (psutil.AccessDenied, PermissionError):
            # On macOS, net_connections requires root privileges
            # Fall back to empty list
            pass

        self.ports = sorted(port_map.values(), key=lambda x: x['port'])

        if self.selected_index >= len(self.ports):
            self.selected_index = max(0, len(self.ports) - 1)
        max_scroll = max(0, len(self.ports) - self.visible_rows)
        self.scroll_position = min(self.scroll_position, max_scroll)
        self.refresh()

    def render(self):
        if not self.ports:
            content = Align.center(
                Text("No ports detected\n(May require sudo on macOS)", style="dim"),
                vertical="middle"
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

            port = str(port_info['port'])
            address = port_info['address']
            name = port_info['name']
            if is_selected:
                name = f"▶ {name}"

            pid = str(port_info['pid']) if port_info['pid'] else "-"

            style = "black on white" if is_selected else None
            table.add_row(port, address, name, pid, style=style)

        total = len(self.ports)
        if total > self.visible_rows:
            scroll_info = f"({self.scroll_position + 1}-{end_index} of {total})"
        else:
            scroll_info = f"({total})"

        title = f"[bold]Listening Ports {scroll_info}[/]"
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
            if self.selected_index < len(self.ports) - 1:
                self.selected_index += 1
                if self.selected_index >= self.scroll_position + self.visible_rows:
                    self.scroll_position = self.selected_index - self.visible_rows + 1
                self.refresh()
            event.prevent_default()

    def on_resize(self, event):
        self.visible_rows = max(5, self.size.height - 3)
        self.refresh()


class DevEnvPanel(Widget):
    """Development environment detection panel."""

    can_focus = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dev_servers = []

    def on_mount(self):
        self.refresh_dev_env()
        self.set_interval(5.0, self.refresh_dev_env)

    def refresh_dev_env(self):
        """Detect development servers and collect metrics."""
        dev_servers_by_type = {}

        # Common dev server patterns
        dev_patterns = {
            'node': ['node', 'npm', 'yarn', 'pnpm', 'next', 'vite', 'webpack'],
            'python': ['python', 'uvicorn', 'gunicorn', 'flask', 'django', 'fastapi'],
            'docker': ['docker', 'containerd', 'dockerd'],
            'ruby': ['ruby', 'rails', 'puma'],
            'go': ['go', 'air'],
            'rust': ['cargo'],
        }

        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
            try:
                proc_info = proc.info
                name = proc_info.get('name', '').lower()
                cmdline = proc_info.get('cmdline', [])
                cmdline_str = ' '.join(cmdline).lower() if cmdline else ''

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
                        connections = proc.connections(kind='inet')
                        for conn in connections:
                            if conn.status == 'LISTEN' and conn.laddr:
                                ports.append(conn.laddr.port)
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass

                    mem_info = proc_info.get('memory_info')
                    mem_mb = mem_info.rss / (1024 * 1024) if mem_info else 0
                    cpu = proc_info.get('cpu_percent', 0) or 0

                    # Group by type
                    if env_type not in dev_servers_by_type:
                        dev_servers_by_type[env_type] = {
                            'type': env_type,
                            'count': 0,
                            'ports': set(),
                            'cpu': 0,
                            'memory_mb': 0,
                            'processes': []
                        }

                    dev_servers_by_type[env_type]['count'] += 1
                    dev_servers_by_type[env_type]['ports'].update(ports)
                    dev_servers_by_type[env_type]['cpu'] += cpu
                    dev_servers_by_type[env_type]['memory_mb'] += mem_mb
                    dev_servers_by_type[env_type]['processes'].append(proc_info.get('name'))

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Convert to list and sort ports
        self.dev_servers = [
            {
                'type': data['type'],
                'count': data['count'],
                'ports': sorted(data['ports']),
                'cpu': data['cpu'],
                'memory_mb': data['memory_mb'],
                'processes': data['processes'][:3]  # Keep first 3 process names
            }
            for data in dev_servers_by_type.values()
        ]
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

        for server in self.dev_servers[:15]:  # Show max 15
            env_type = f"{server['type'].upper()} ({server['count']})"

            # Show first 3 process names
            processes = server['processes']
            if len(processes) > 3:
                name = ', '.join(processes[:3]) + '...'
            else:
                name = ', '.join(processes) if processes else '-'

            ports = ', '.join(map(str, server['ports'])) if server['ports'] else '-'
            cpu = f"{server['cpu']:.1f}"
            mem = sizeof_fmt(server['memory_mb'] * 1024 * 1024, suffix="", sep="")

            table.add_row(env_type, name, ports, cpu, mem)

        total_count = sum(s['count'] for s in self.dev_servers)
        total_types = len(self.dev_servers)
        title = f"[bold]Development Environment ({total_types} types, {total_count} procs)[/]"
        border_style = "bright_cyan" if self.has_focus else "dim"

        return Panel(table, title=title, border_style=border_style)


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
                yield PortListPanel(id="right-top")
                yield DevEnvPanel(id="right-bottom")

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
