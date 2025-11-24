"""
Process sorting module for interactive column-based sorting.
Handles sort state, column definitions, and sorting logic.
"""

from typing import Callable, Optional
from enum import Enum


class SortDirection(Enum):
    """Sort direction states: off -> desc -> asc -> off (cycle)."""
    OFF = "off"
    DESC = "desc"
    ASC = "asc"

    def next(self) -> "SortDirection":
        """Cycle to next sort direction."""
        return {
            SortDirection.OFF: SortDirection.DESC,
            SortDirection.DESC: SortDirection.ASC,
            SortDirection.ASC: SortDirection.OFF,
        }[self]

    def icon(self) -> str:
        """Return visual indicator for sort direction."""
        return {
            SortDirection.OFF: " ",
            SortDirection.DESC: "↓",
            SortDirection.ASC: "↑",
        }[self]


class SortColumn:
    """Represents a sortable column with key and display name."""

    def __init__(self, key: str, display_name: str, sort_fn: Optional[Callable] = None):
        self.key = key
        self.display_name = display_name
        self.sort_fn = sort_fn or (lambda p: p.get(key, 0))

    def get_sort_value(self, process: dict):
        """Get the value to sort by for a process."""
        return self.sort_fn(process)


class SortManager:
    """Manages sorting state and operations for process list."""

    COLUMNS = [
        SortColumn("pid", "PID", lambda p: p.get("pid") or 0),
        SortColumn("name", "Process", lambda p: (p.get("name") or "").lower()),
        SortColumn("num_threads", "🧵", lambda p: p.get("num_threads") or 0),
        SortColumn(
            "memory_rss",
            "Memory",
            lambda p: getattr(p.get("memory_info"), "rss", 0) or 0,
        ),
        SortColumn("total_io_rate", "Net", lambda p: p.get("total_io_rate") or 0),
        SortColumn("num_connections", "Conn", lambda p: p.get("num_connections") or 0),
        SortColumn("cpu_percent", "CPU", lambda p: p.get("cpu_percent") or 0),
    ]

    def __init__(self):
        self.active_column_index = len(self.COLUMNS) - 1
        self.sort_direction = SortDirection.DESC
        self.sort_mode_active = False

    def current_column(self) -> SortColumn:
        """Get the currently active sort column."""
        return self.COLUMNS[self.active_column_index]

    def toggle_column(self, index: int) -> None:
        """Switch to a different sort column."""
        if 0 <= index < len(self.COLUMNS):
            if self.active_column_index == index:
                self.sort_direction = self.sort_direction.next()
            else:
                self.active_column_index = index
                self.sort_direction = SortDirection.DESC

    def apply_sort(self, processes: list) -> list:
        """Sort processes based on current sort settings."""
        if self.sort_direction == SortDirection.OFF:
            return processes

        column = self.current_column()
        reverse = self.sort_direction == SortDirection.DESC

        try:
            def safe_sort_key(p):
                try:
                    val = column.get_sort_value(p)
                    return (val is None, val)
                except (TypeError, AttributeError, ValueError):
                    return (True, 0)

            return sorted(processes, key=safe_sort_key, reverse=reverse)
        except Exception:
            return processes

    def navigate_columns(self, direction: int) -> None:
        """Navigate between columns in sort mode. Direction: -1 (left) or 1 (right)."""
        new_index = self.active_column_index + direction
        if 0 <= new_index < len(self.COLUMNS):
            self.active_column_index = new_index
            if self.sort_direction == SortDirection.OFF:
                self.sort_direction = SortDirection.DESC

    def enter_sort_mode(self) -> None:
        """Enter interactive sort mode."""
        self.sort_mode_active = True

    def exit_sort_mode(self) -> None:
        """Exit interactive sort mode."""
        self.sort_mode_active = False

    def get_sort_indicator_str(self) -> str:
        """Get string representation of current sort state for display."""
        column = self.current_column()
        if self.sort_direction == SortDirection.OFF:
            return "unsorted"
        direction_icon = self.sort_direction.icon()
        return f"{column.display_name} {direction_icon}"
