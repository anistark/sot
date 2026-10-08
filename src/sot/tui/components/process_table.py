"""Process table used by the overview and the processes view."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from rich.console import JustifyMethod
from rich.text import Text

from ..._collectors import process_sampler
from ..._helpers import sizeof_fmt
from ..._theme import Colors, theme
from ...widgets.process_sorter import SortManager
from .. import keymap, refresh
from ..messages import ProcessAction, Reveal
from .table import SotTable, cell


@dataclass(frozen=True)
class Column:
    label: str
    width: int | None  # None fills the remaining width
    justify: JustifyMethod
    value: Callable[[dict], str]
    style: Callable[[Colors], str] = lambda c: ""


def _memory(p: dict) -> str:
    mem = p.get("memory_info")
    return "" if mem is None else sizeof_fmt(mem.rss, suffix="", sep="")


def _io(p: dict) -> str:
    rate = p.get("total_io_rate") or 0
    return sizeof_fmt(rate, fmt=".1f", suffix="", sep="") + "/s" if rate > 0 else "-"


COLUMNS = {
    "pid": Column("PID", 7, "right", lambda p: str(p["pid"])),
    "name": Column(
        "Process", None, "left", lambda p: p.get("name") or "", lambda c: c.secondary
    ),
    "user": Column(
        "User", 10, "left", lambda p: p.get("username") or "", lambda c: c.muted
    ),
    "status": Column(
        "Status", 8, "left", lambda p: p.get("status") or "", lambda c: c.muted
    ),
    "threads": Column("Thr", 4, "right", lambda p: str(p.get("num_threads") or "")),
    "memory": Column("Memory", 7, "right", _memory),
    "io": Column("I/O", 9, "right", _io, lambda c: c.primary),
    "conn": Column(
        "Conn",
        4,
        "right",
        lambda p: str(p.get("num_connections") or "-"),
        lambda c: c.info,
    ),
    "cpu": Column("CPU %", 6, "right", lambda p: f"{p.get('cpu_percent') or 0:.1f}"),
}

COMPACT = ("pid", "name", "threads", "memory", "io", "conn", "cpu")
FULL = ("pid", "name", "user", "status", "threads", "memory", "io", "conn", "cpu")
NETWORK = {"io", "conn"}
# Dropped in this order when the table is too narrow for a readable name.
NARROW_DROP = ("io", "conn", "user", "threads", "status", "memory")
MIN_NAME_WIDTH = 14
SORTING = {"sort_prev", "sort_next", "sort_toggle", "sort_done"}
# Table column -> SortManager column, for header clicks.
SORT_KEYS = {
    "pid": "pid",
    "name": "name",
    "threads": "num_threads",
    "memory": "memory_rss",
    "io": "total_io_rate",
    "conn": "num_connections",
    "cpu": "cpu_percent",
}


def _matches(proc: dict, text: str) -> bool:
    haystack = " ".join(
        [
            str(proc["pid"]),
            proc.get("name") or "",
            proc.get("username") or "",
            " ".join(proc.get("cmdline") or []),
        ]
    )
    return text.lower() in haystack.lower()


class ProcessTable(SotTable):
    DETAIL_KIND = "process"
    BINDINGS = [
        *keymap.LIST,
        *keymap.PROCESS,
        *keymap.SORT_MODE,
        keymap.NETWORK_COLUMNS,
    ]
    STATE = ("sort_manager", "show_network", "selected_row", "filter_text")

    def __init__(self, columns: tuple[str, ...] = COMPACT, **kwargs):
        super().__init__("Processes", **kwargs)
        self.column_keys = columns
        self.sort_manager = SortManager()
        self.show_network = True
        self.processes: list[dict] = []
        self._by_pid: dict[str, dict] = {}
        self._layout: tuple = ()

    def on_mount(self) -> None:
        self.restore_state()
        self.reload()
        self.every(refresh.PROCESSES, self.reload)

    def on_resize(self) -> None:
        if self._build_columns():
            self._fill()

    def _visible(self) -> list[str]:
        return [k for k in self.column_keys if self.show_network or k not in NETWORK]

    def _name_width(self, keys: list[str]) -> int:
        fixed = sum(COLUMNS[k].width or 0 for k in keys)
        padding = 2 * self.cell_padding * len(keys)
        # Border and vertical scrollbar take two columns each.
        return self.size.width - fixed - padding - 4

    def _fit(self, keys: list[str]) -> list[str]:
        for key in NARROW_DROP:
            if self._name_width(keys) >= MIN_NAME_WIDTH:
                break
            keys = [k for k in keys if k != key]
        return keys

    def _build_columns(self) -> bool:
        keys = self._fit(self._visible())
        name_width = max(MIN_NAME_WIDTH, self._name_width(keys))
        if self._layout == (keys, name_width):
            return False
        self._layout = (keys, name_width)
        self.clear(columns=True)
        for key in keys:
            column = COLUMNS[key]
            self.add_column(
                Text(column.label, justify=column.justify),
                key=key,
                width=column.width or name_width,
            )
        return True

    def reload(self) -> None:
        processes = process_sampler.sample()
        if self.filter_text:
            processes = [p for p in processes if _matches(p, self.filter_text)]
        self.processes = self.sort_manager.apply_sort(processes)
        self._by_pid = {str(p["pid"]): p for p in self.processes}
        self._fill()

    def _fill(self) -> None:
        self._build_columns()
        colors = theme().colors
        keys = self._layout[0]
        rows = []
        for p in self.processes:
            cells = []
            for key in keys:
                column = COLUMNS[key]
                cells.append(
                    cell(column.value(p), column.style(colors), column.justify)
                )
            rows.append((str(p["pid"]), tuple(cells)))
        self.set_rows(rows)
        self._update_title()

    def _update_title(self) -> None:
        c = theme().colors
        sort = self.sort_manager
        if sort.sort_mode_active:
            columns = " | ".join(col.display_name for col in sort.COLUMNS)
            detail = (
                f"[{c.alert_tag}] ORDER BY [/] "
                f"[bold {c.accent}]{sort.current_column().display_name}[/] "
                f"[bold {c.secondary}]{sort.sort_direction.icon()}[/] {columns}"
            )
        else:
            threads = sum(p.get("num_threads") or 0 for p in self.processes)
            sleeping = sum(p.get("status") == "sleeping" for p in self.processes)
            detail = (
                f"{len(self.processes)} · {threads} threads · {sleeping} sleeping · "
                f"[{c.accent}]Sort: {sort.get_sort_indicator_str()}[/]"
            )
        self.set_class(sort.sort_mode_active, "-alert")
        self.set_title(self.label, detail)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        # While picking a sort column only the sort keys apply.
        return (action in SORTING) == self.sort_manager.sort_mode_active

    def selected_process(self) -> dict | None:
        return self._by_pid.get(self.selected_row or "")

    def action_kill(self) -> None:
        if (proc := self.selected_process()) is not None:
            self.post_message(ProcessAction("kill", proc))

    def action_terminate(self) -> None:
        if (proc := self.selected_process()) is not None:
            self.post_message(ProcessAction("terminate", proc))

    def action_refresh(self) -> None:
        self.reload()

    def action_toggle_network(self) -> None:
        self.show_network = not self.show_network
        self._fill()

    def action_sort_mode(self) -> None:
        self.sort_manager.enter_sort_mode()
        self._update_title()

    def action_sort_prev(self) -> None:
        self.sort_manager.navigate_columns(-1)
        self._update_title()

    def action_sort_next(self) -> None:
        self.sort_manager.navigate_columns(1)
        self._update_title()

    def action_sort_toggle(self) -> None:
        self.sort_manager.toggle_column(self.sort_manager.active_column_index)
        self.reload()

    def action_sort_done(self) -> None:
        self.sort_manager.exit_sort_mode()
        self._update_title()

    def sort_by_column(self, key: str) -> None:
        keys = [column.key for column in self.sort_manager.COLUMNS]
        if SORT_KEYS.get(key) in keys:
            self.sort_manager.toggle_column(keys.index(SORT_KEYS[key]))
            self.reload()


class OverviewProcessTable(ProcessTable):
    """The overview's list: `enter` opens the process in the processes view."""

    BINDINGS = [
        *keymap.LIST,
        keymap.OPEN,
        *keymap.PROCESS[1:],
        *keymap.SORT_MODE,
        keymap.NETWORK_COLUMNS,
    ]

    def action_open(self) -> None:
        if self.selected_row is not None:
            self.post_message(Reveal("processes", "proc-table", self.selected_row))

    def action_details(self) -> None:
        self.action_open()
