"""Processes: full process table, listening ports and dev environments."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message

from ..._collectors import dev_environments, listening_ports, process_sampler
from ..._helpers import sizeof_fmt
from ..._theme import theme
from .. import keymap, refresh
from ..components.process_table import FULL, ProcessTable
from ..components.table import SotTable, cell
from ..messages import ProcessAction
from ..screen import SotScreen


class SortCycleTable(SotTable):
    """Table sorted by one field at a time: `o` cycles it, `s` reverses."""

    SORT_FIELDS: tuple[str, ...] = ()
    STATE = ("sort_by", "sort_reverse", "selected_row")

    def __init__(self, title: str, **kwargs):
        super().__init__(title, **kwargs)
        self.sort_by = self.SORT_FIELDS[0]
        self.sort_reverse = False
        self.items: list[dict] = []

    def sorted_items(self, items: list[dict]) -> list[dict]:
        def key(item: dict):
            value = item.get(self.sort_by)
            return (
                value is None,
                value if not isinstance(value, str) else value.lower(),
            )

        return sorted(items, key=key, reverse=self.sort_reverse)

    def selected_item(self) -> dict | None:
        for item in self.items:
            if self.item_key(item) == self.selected_row:
                return item
        return None

    def item_key(self, item: dict) -> str:
        raise NotImplementedError

    def reload(self) -> None:
        raise NotImplementedError

    def action_refresh(self) -> None:
        self.reload()

    def action_sort_cycle(self) -> None:
        fields = self.SORT_FIELDS
        self.sort_by = fields[(fields.index(self.sort_by) + 1) % len(fields)]
        self.sort_reverse = False
        self.reload()

    def action_sort_reverse(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.reload()

    def sort_label(self) -> str:
        arrow = "↓" if self.sort_reverse else "↑"
        return f"[{theme().colors.accent}]Sort: {self.sort_by} {arrow}[/]"


class PortTable(SortCycleTable):
    BINDINGS = [*keymap.LIST, *keymap.PROCESS, *keymap.SORT_CYCLE]
    SORT_FIELDS = ("port", "address", "name", "pid")

    class PortSelected(Message):
        def __init__(self, port_info: dict) -> None:
            self.port_info = port_info
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__("Listening Ports", **kwargs)

    def on_mount(self) -> None:
        self.restore_state()
        self.add_columns("Port", "Address", "Process", "PID")
        self.reload()
        self.every(refresh.PORTS, self.reload)

    def item_key(self, item: dict) -> str:
        return str(item["port"])

    def reload(self) -> None:
        c = theme().colors
        self.items = self.sorted_items(listening_ports())
        self.set_rows(
            [
                (
                    self.item_key(p),
                    (
                        cell(p["port"], justify="right"),
                        cell(p["address"]),
                        cell(p["name"], c.secondary),
                        cell(p["pid"] or "-", justify="right"),
                    ),
                )
                for p in self.items
            ]
        )
        detail = f"{len(self.items)} · {self.sort_label()}"
        if not self.items:
            detail += f" · [{c.muted}]may need sudo on macOS[/]"
        self.set_title(self.label, detail)

    def action_details(self) -> None:
        if (port := self.selected_item()) is not None:
            self.post_message(self.PortSelected(port))

    def _act(self, action: str) -> None:
        port = self.selected_item()
        if port is not None and port.get("pid"):
            self.post_message(
                ProcessAction(action, {"pid": port["pid"], "name": port["name"]})
            )

    def action_kill(self) -> None:
        self._act("kill")

    def action_terminate(self) -> None:
        self._act("terminate")


class DevEnvTable(SortCycleTable):
    BINDINGS = [*keymap.LIST, keymap.DETAILS, keymap.REFRESH, *keymap.SORT_CYCLE]
    SORT_FIELDS = ("type", "count", "cpu", "memory_mb")

    class DevEnvSelected(Message):
        def __init__(self, dev_env: dict) -> None:
            self.dev_env = dev_env
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__("Development Environment", **kwargs)

    def on_mount(self) -> None:
        self.restore_state()
        self.add_columns("Type", "Processes", "Ports", "CPU %", "Mem")
        self.reload()
        self.every(refresh.DEV_ENV, self.reload)

    def item_key(self, item: dict) -> str:
        return item["type"]

    def reload(self) -> None:
        c = theme().colors
        self.items = self.sorted_items(dev_environments(process_sampler.sample()))
        rows = []
        for env in self.items:
            memory = sizeof_fmt(env["memory_mb"] * 1024 * 1024, suffix="", sep="")
            rows.append(
                (
                    self.item_key(env),
                    (
                        cell(f"{env['type'].upper()} ({env['count']})"),
                        cell(", ".join(env["processes"]) or "-", c.secondary),
                        cell(", ".join(map(str, env["ports"])) or "-"),
                        cell(f"{env['cpu']:.1f}", justify="right"),
                        cell(memory, justify="right"),
                    ),
                )
            )
        self.set_rows(rows)
        total = sum(env["count"] for env in self.items)
        detail = f"{len(self.items)} types, {total} procs · {self.sort_label()}"
        self.set_title(self.label, detail)

    def action_details(self) -> None:
        if (env := self.selected_item()) is not None:
            self.post_message(self.DevEnvSelected(env))


class ProcessesScreen(SotScreen):
    MODE = "processes"

    DEFAULT_CSS = """
    ProcessesScreen #proc-table {
        width: 1fr;
    }

    ProcessesScreen #side {
        width: 1fr;
    }
    """

    def compose_view(self) -> ComposeResult:
        with Horizontal():
            yield ProcessTable(FULL, id="proc-table")
            with Vertical(id="side"):
                yield PortTable(id="port-table")
                yield DevEnvTable(id="devenv-table")

    def on_mount(self) -> None:
        self.query_one("#proc-table").focus()

    def on_port_table_port_selected(self, message: PortTable.PortSelected) -> None:
        port = message.port_info
        details = [f"Port {port['port']} on {port['address']}"]
        details.append(f"Process: {port['name']}")
        if port["pid"]:
            details.append(f"PID: {port['pid']}")
        self.notify("\n".join(details))

    def on_dev_env_table_dev_env_selected(
        self, message: DevEnvTable.DevEnvSelected
    ) -> None:
        env = message.dev_env
        details = [f"{env['type'].upper()} environment"]
        details.append(f"Processes: {env['count']}")
        if env["ports"]:
            details.append(f"Ports: {', '.join(map(str, env['ports']))}")
        details.append(f"CPU: {env['cpu']:.1f}%")
        memory = sizeof_fmt(env["memory_mb"] * 1024 * 1024, suffix="", sep="")
        details.append(f"Memory: {memory}")
        self.notify("\n".join(details))
