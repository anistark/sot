"""Default key bindings. Every binding has an id so it can be remapped."""

from textual.binding import Binding

QUIT = Binding("q", "quit", "Quit", id="sot.quit")
HELP = Binding("question_mark", "toggle_help", "Help", id="sot.help")

LIST = [
    Binding("up,k", "cursor_up", "Up", show=False, id="sot.list.up"),
    Binding("down,j", "cursor_down", "Down", show=False, id="sot.list.down"),
    Binding("pageup,ctrl+u", "page_up", "Page up", show=False, id="sot.list.page_up"),
    Binding(
        "pagedown,ctrl+d", "page_down", "Page down", show=False, id="sot.list.page_down"
    ),
    Binding("home,g", "first", "First", show=False, id="sot.list.first"),
    Binding("end,G", "last", "Last", show=False, id="sot.list.last"),
]

DETAILS = Binding("enter", "details", "Details", id="sot.details")
REFRESH = Binding("r", "refresh", "Refresh", id="sot.refresh")

PROCESS = [
    DETAILS,
    Binding("x", "kill", "Kill", id="sot.process.kill"),
    Binding("t", "terminate", "Terminate", id="sot.process.terminate"),
    REFRESH,
]

NETWORK_COLUMNS = Binding(
    "n", "toggle_network", "Net columns", id="sot.process.network"
)

# Column picker: `o` opens it, then the arrows pick and enter toggles.
SORT_MODE = [
    Binding("o", "sort_mode", "Sort", id="sot.sort.mode"),
    Binding("left,h", "sort_prev", "Prev column", id="sot.sort.prev"),
    Binding("right,l", "sort_next", "Next column", id="sot.sort.next"),
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

VIEWS = {
    "overview": "Overview",
    "processes": "Processes",
    "disks": "Disks",
}

VIEW_KEYS = [
    Binding(str(n), f"switch_mode('{mode}')", label, show=False, id=f"sot.view.{mode}")
    for n, (mode, label) in enumerate(VIEWS.items(), 1)
]
