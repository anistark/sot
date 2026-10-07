"""Process TUI - Interactive process viewer."""

from __future__ import annotations

import psutil
from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Footer, Header

from .._helpers import sizeof_fmt
from .._theme import theme
from ..tui import keymap
from ..tui.base import SotBaseApp
from ..tui.messages import ProcessAction
from ..tui.process_list import ProcessListActions
from ..tui.state import KeepsState, ListCursor
from ..widgets.process_sorter import SortManager
from ..widgets.processes import get_process_list


class ProcessListPanel(ProcessListActions):
    """Process list panel on the left."""

    BINDINGS = [*keymap.LIST, *keymap.PROCESS, *keymap.SORT_MODE]
    STATE = ("processes", "selected_index", "scroll_position", "sort_manager")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processes = []
        self.selected_index = 0
        self.scroll_position = 0
        self.visible_rows = 20
        self.sort_manager = SortManager()

    def on_mount(self):
        self.restore_state()
        self.refresh_processes()
        self.set_interval(2.0, self.refresh_processes)

    def refresh_processes(self):
        self.processes = get_process_list(500, self.sort_manager)
        self.clamp_cursor()
        self.refresh()

    def redraw(self) -> None:
        self.refresh()

    def reload(self) -> None:
        self.refresh_processes()

    def render(self):
        t = theme()
        c = t.colors
        sep = t.design.separator
        table = Table(
            row_styles=t.row_styles(),
            show_header=True,
            header_style=f"bold {c.accent}",
            box=None,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("PID", justify="right", width=8)
        table.add_column("Process", style=c.secondary, no_wrap=True, ratio=1)
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
                name = f"{t.design.cursor}{name}"

            mem_info = proc.get("memory_info")
            mem_str = (
                "" if mem_info is None else sizeof_fmt(mem_info.rss, suffix="", sep="")
            )

            cpu = proc.get("cpu_percent", 0) or 0
            cpu_str = f"{cpu:.1f}"

            style = c.selected if is_selected else None
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
            title = f"[{c.alert_tag}] ORDER BY [/]{sep}[bold {c.accent}]{current_col}[/] [bold {c.secondary}]{direction}[/]{sep}{columns_display}"
            border_style = c.border_alert
        else:
            sort_indicator = self.sort_manager.get_sort_indicator_str()
            help_text = "O order | ↑↓ | ⏎ info | K kill | T term | R refresh"
            title = f"{t.title(f'Processes {scroll_info}')}{sep}[{c.accent}]Sort: {sort_indicator}[/]{sep}[{c.muted}]{help_text}[/]"
            border_style = c.accent if self.has_focus else c.muted

        return Panel(
            table, title=title, border_style=border_style, box=t.design.app_box
        )

    def on_resize(self, event):
        self.visible_rows = max(10, self.size.height - 3)
        self.refresh()


class PortListPanel(ListCursor, KeepsState):
    """Port list panel showing open ports and their processes."""

    can_focus = True

    BINDINGS = [
        *keymap.LIST,
        *keymap.PROCESS,
        *keymap.SORT_CYCLE,
    ]
    STATE = ("ports", "selected_index", "scroll_position", "sort_by", "sort_reverse")

    class PortSelected(Message):
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
        self.restore_state()
        self.refresh_ports()
        self.set_interval(3.0, self.refresh_ports)

    def row_count(self) -> int:
        return len(self.ports)

    def redraw(self) -> None:
        self.refresh()

    def _selected(self) -> dict | None:
        if 0 <= self.selected_index < len(self.ports):
            return self.ports[self.selected_index]
        return None

    def action_details(self) -> None:
        if (port := self._selected()) is not None:
            self.post_message(self.PortSelected(port))

    def _act(self, action: str) -> None:
        port = self._selected()
        if port is not None and port.get("pid"):
            self.post_message(
                ProcessAction(action, {"pid": port["pid"], "name": port["name"]})
            )

    def action_kill(self) -> None:
        self._act("kill")

    def action_terminate(self) -> None:
        self._act("terminate")

    def action_refresh(self) -> None:
        self.refresh_ports()

    def action_sort_cycle(self) -> None:
        options = ["port", "address", "name", "pid"]
        self.sort_by = options[(options.index(self.sort_by) + 1) % len(options)]
        self.sort_reverse = False
        self.refresh_ports()

    def action_sort_reverse(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.refresh_ports()

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
        self.clamp_cursor()
        self.refresh()

    def render(self):
        t = theme()
        c = t.colors
        sep = t.design.separator
        if not self.ports:
            content = Align.center(
                Text("No ports detected\n(May require sudo on macOS)", style=c.muted),
                vertical="middle",
            )
            border_style = c.accent if self.has_focus else c.muted
            return Panel(
                content,
                title=t.title("Listening Ports (0)"),
                border_style=border_style,
                box=t.design.app_box,
            )

        table = Table(
            row_styles=t.row_styles(),
            show_header=True,
            header_style=f"bold {c.accent}",
            box=None,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("Port", justify="right", width=7)
        table.add_column("Address", justify="left", width=15)
        table.add_column("Process", style=c.secondary, no_wrap=True, ratio=1)
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
                name = f"{t.design.cursor}{name}"

            pid = str(port_info["pid"]) if port_info["pid"] else "-"

            style = c.selected if is_selected else None
            table.add_row(port, address, name, pid, style=style)

        total = len(self.ports)
        if total > self.visible_rows:
            scroll_info = f"({self.scroll_position + 1}-{end_index} of {total})"
        else:
            scroll_info = f"({total})"

        sort_dir = "↓" if self.sort_reverse else "↑"
        help_text = "O sort | S dir | ↑↓ | ⏎ info | K kill | T term | R refresh"
        title = f"{t.title(f'Ports {scroll_info}')}{sep}[{c.accent}]Sort: {self.sort_by} {sort_dir}[/]{sep}[{c.muted}]{help_text}[/]"
        border_style = c.accent if self.has_focus else c.muted

        return Panel(
            table, title=title, border_style=border_style, box=t.design.app_box
        )

    def on_resize(self, event):
        self.visible_rows = max(5, self.size.height - 3)
        self.refresh()


class DevEnvPanel(ListCursor, KeepsState):
    """Development environment detection panel."""

    can_focus = True

    BINDINGS = [*keymap.LIST, keymap.DETAILS, keymap.REFRESH, *keymap.SORT_CYCLE]
    STATE = (
        "dev_servers",
        "selected_index",
        "scroll_position",
        "sort_by",
        "sort_reverse",
    )

    class DevEnvSelected(Message):
        def __init__(self, dev_env: dict) -> None:
            self.dev_env = dev_env
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dev_servers = []
        self.selected_index = 0
        self.scroll_position = 0
        self.visible_rows = 15
        self.sort_by = "type"
        self.sort_reverse = False

    def on_mount(self):
        self.restore_state()
        self.refresh_dev_env()
        self.set_interval(5.0, self.refresh_dev_env)

    def row_count(self) -> int:
        return len(self.dev_servers)

    def redraw(self) -> None:
        self.refresh()

    def action_details(self) -> None:
        if 0 <= self.selected_index < len(self.dev_servers):
            self.post_message(
                self.DevEnvSelected(self.dev_servers[self.selected_index])
            )

    def action_refresh(self) -> None:
        self.refresh_dev_env()

    def action_sort_cycle(self) -> None:
        options = ["type", "count", "cpu", "memory"]
        self.sort_by = options[(options.index(self.sort_by) + 1) % len(options)]
        self.sort_reverse = False
        self.refresh_dev_env()

    def action_sort_reverse(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.refresh_dev_env()

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
        self.clamp_cursor()
        self.refresh()

    def render(self):
        t = theme()
        c = t.colors
        sep = t.design.separator
        if not self.dev_servers:
            content = Align.center(
                Text("No dev servers detected", style=c.muted), vertical="middle"
            )
            border_style = c.accent if self.has_focus else c.muted
            return Panel(
                content,
                title=t.title("Development Environment"),
                border_style=border_style,
                box=t.design.app_box,
            )

        table = Table(
            row_styles=t.row_styles(),
            show_header=True,
            header_style=f"bold {c.accent}",
            box=None,
            padding=(0, 1),
            expand=True,
        )

        table.add_column("Type", justify="left", width=12)
        table.add_column("Processes", style=c.secondary, no_wrap=True, ratio=1)
        table.add_column("Ports", justify="left", width=15)
        table.add_column("CPU%", justify="right", width=6)
        table.add_column("Mem", justify="right", width=8)

        end_index = self.scroll_position + self.visible_rows
        visible = self.dev_servers[self.scroll_position : end_index]
        for local_idx, server in enumerate(visible):
            idx = self.scroll_position + local_idx
            is_selected = self.has_focus and idx == self.selected_index

            env_type = f"{server['type'].upper()} ({server['count']})"

            processes = server["processes"]
            if len(processes) > 3:
                name = ", ".join(processes[:3]) + "..."
            else:
                name = ", ".join(processes) if processes else "-"

            if is_selected:
                name = f"{t.design.cursor}{name}"

            ports = ", ".join(map(str, server["ports"])) if server["ports"] else "-"
            cpu = f"{server['cpu']:.1f}"
            mem = sizeof_fmt(server["memory_mb"] * 1024 * 1024, suffix="", sep="")

            style = c.selected if is_selected else None
            table.add_row(env_type, name, ports, cpu, mem, style=style)

        total_count = sum((s["count"] for s in self.dev_servers), start=0)
        total_types = len(self.dev_servers)
        sort_dir = "↓" if self.sort_reverse else "↑"
        help_text = "O sort | S dir | ↑↓ | ⏎ info | R refresh"
        title = f"{t.title(f'Dev Env ({total_types} types, {total_count} procs)')}{sep}[{c.accent}]Sort: {self.sort_by} {sort_dir}[/]{sep}[{c.muted}]{help_text}[/]"
        border_style = c.accent if self.has_focus else c.muted

        return Panel(
            table, title=title, border_style=border_style, box=t.design.app_box
        )


class ProcessTUIApp(SotBaseApp):
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

    BINDINGS = [keymap.QUIT, keymap.FOCUS_NEXT]

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

    def on_port_list_panel_port_selected(
        self, message: PortListPanel.PortSelected
    ) -> None:
        port_info = message.port_info
        details = [f"Port {port_info['port']} on {port_info['address']}"]
        details.append(f"Process: {port_info['name']}")
        if port_info["pid"]:
            details.append(f"PID: {port_info['pid']}")
        self.notify("\n".join(details))

    def on_dev_env_panel_dev_env_selected(
        self, message: DevEnvPanel.DevEnvSelected
    ) -> None:
        env = message.dev_env
        details = [f"{env['type'].upper()} environment"]
        details.append(f"Processes: {env['count']}")
        if env["ports"]:
            details.append(f"Ports: {', '.join(map(str, env['ports']))}")
        details.append(f"CPU: {env['cpu']:.1f}%")
        details.append(
            f"Memory: {sizeof_fmt(env['memory_mb'] * 1024 * 1024, suffix='', sep='')}"
        )
        self.notify("\n".join(details))
