"""Processes: full process table, listening ports and dev environments."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical

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
    STATE = ("sort_by", "sort_reverse", "selected_row", "filter_text")

    def __init__(self, title: str, **kwargs):
        super().__init__(title, **kwargs)
        self.sort_by = self.SORT_FIELDS[0]
        self.sort_reverse = False
        self.items: list[dict] = []

    def item_text(self, item: dict) -> str:
        return " ".join(str(value) for value in item.values())

    def sorted_items(self, items: list[dict]) -> list[dict]:
        if self.filter_text:
            text = self.filter_text.lower()
            items = [i for i in items if text in self.item_text(i).lower()]

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

    def action_refresh(self) -> None:
        self.reload()

    def sort_by_column(self, key: str) -> None:
        if key not in self.SORT_FIELDS:
            return
        if key == self.sort_by:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_by, self.sort_reverse = key, False
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
    DETAIL_KIND = "port"
    BINDINGS = [*keymap.LIST, *keymap.PROCESS, *keymap.SORT_CYCLE]
    SORT_FIELDS = ("port", "address", "name", "pid")

    def __init__(self, **kwargs):
        super().__init__("Listening Ports", **kwargs)

    def on_mount(self) -> None:
        self.restore_state()
        for key, label in zip(self.SORT_FIELDS, ("Port", "Address", "Process", "PID")):
            self.add_column(label, key=key)
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
    DETAIL_KIND = "devenv"
    BINDINGS = [*keymap.LIST, keymap.DETAILS, keymap.REFRESH, *keymap.SORT_CYCLE]
    SORT_FIELDS = ("type", "count", "cpu", "memory_mb")

    def __init__(self, **kwargs):
        super().__init__("Development Environment", **kwargs)

    def on_mount(self) -> None:
        self.restore_state()
        for key, label in (
            ("type", "Type"),
            ("processes", "Processes"),
            ("ports", "Ports"),
            ("cpu", "CPU %"),
            ("memory_mb", "Mem"),
        ):
            self.add_column(label, key=key)
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
