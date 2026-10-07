"""Default key bindings. Every binding has an id so it can be remapped."""

from textual.binding import Binding

QUIT = Binding("q", "quit", "Quit", id="sot.quit")
FOCUS_NEXT = Binding("tab", "focus_next", "Next panel", id="sot.focus.next")

LIST = [
    Binding("up", "cursor_up", "Up", show=False, id="sot.list.up"),
    Binding("down", "cursor_down", "Down", show=False, id="sot.list.down"),
    Binding("pageup,ctrl+u", "page_up", "Page up", show=False, id="sot.list.page_up"),
    Binding(
        "pagedown,ctrl+d", "page_down", "Page down", show=False, id="sot.list.page_down"
    ),
    Binding("home,ctrl+home", "first", "First", show=False, id="sot.list.first"),
    Binding("end,ctrl+end", "last", "Last", show=False, id="sot.list.last"),
]

DETAILS = Binding("enter", "details", "Details", id="sot.details")
REFRESH = Binding("r", "refresh", "Refresh", id="sot.refresh")

PROCESS = [
    DETAILS,
    Binding("k", "kill", "Kill", id="sot.process.kill"),
    Binding("t", "terminate", "Terminate", id="sot.process.terminate"),
    REFRESH,
]

# Column picker: `o` opens it, then the arrows pick and enter toggles.
SORT_MODE = [
    Binding("o", "sort_mode", "Sort", id="sot.sort.mode"),
    Binding("left", "sort_prev", "Prev column", id="sot.sort.prev"),
    Binding("right", "sort_next", "Next column", id="sot.sort.next"),
    Binding("enter", "sort_toggle", "Toggle", id="sot.sort.toggle"),
    Binding("escape,o", "sort_done", "Done", id="sot.sort.done"),
]

# Simple sort: `o` cycles the column, `s` flips the direction.
SORT_CYCLE = [
    Binding("o", "sort_cycle", "Sort", id="sot.sort.cycle"),
    Binding("s", "sort_reverse", "Direction", id="sot.sort.reverse"),
]

CONFIRM = [
    Binding("y", "confirm", "Confirm", id="sot.confirm.yes"),
    Binding("n,escape", "cancel", "Cancel", id="sot.confirm.no"),
]
