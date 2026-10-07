"""Actions shared by the process lists in the dashboard and `sot ps`."""

from __future__ import annotations

from ..widgets.process_sorter import SortManager
from .messages import ProcessAction, ProcessSelected
from .state import KeepsState, ListCursor

SORTING = {"sort_prev", "sort_next", "sort_toggle", "sort_done"}


class ProcessListActions(ListCursor, KeepsState):
    """Bindings: ``keymap.LIST``, ``keymap.PROCESS`` and ``keymap.SORT_MODE``."""

    can_focus = True

    processes: list[dict]
    sort_manager: SortManager

    def reload(self) -> None:
        raise NotImplementedError

    def row_count(self) -> int:
        return len(self.processes)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        # While picking a sort column only the sort keys apply.
        return (action in SORTING) == self.sort_manager.sort_mode_active

    def selected_process(self) -> dict | None:
        if 0 <= self.selected_index < len(self.processes):
            return self.processes[self.selected_index]
        return None

    def action_details(self) -> None:
        if (proc := self.selected_process()) is not None:
            self.post_message(ProcessSelected(proc))

    def action_kill(self) -> None:
        if (proc := self.selected_process()) is not None:
            self.post_message(ProcessAction("kill", proc))

    def action_terminate(self) -> None:
        if (proc := self.selected_process()) is not None:
            self.post_message(ProcessAction("terminate", proc))

    def action_refresh(self) -> None:
        self.reload()

    def action_sort_mode(self) -> None:
        self.sort_manager.enter_sort_mode()
        self.redraw()

    def action_sort_prev(self) -> None:
        self.sort_manager.navigate_columns(-1)
        self.redraw()

    def action_sort_next(self) -> None:
        self.sort_manager.navigate_columns(1)
        self.redraw()

    def action_sort_toggle(self) -> None:
        self.sort_manager.toggle_column(self.sort_manager.active_column_index)
        self.reload()

    def action_sort_done(self) -> None:
        self.sort_manager.exit_sort_mode()
        self.redraw()
