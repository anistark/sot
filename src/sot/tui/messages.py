"""Messages any view can post for the app or its screen to handle."""

from textual.message import Message


class ProcessAction(Message):
    """Ask to kill or terminate a process; the app confirms first."""

    def __init__(self, action: str, process_info: dict) -> None:
        self.action = action
        self.process_info = process_info
        super().__init__()


class ShowDetails(Message):
    """Toggle the detail drawer for an item, see ``tui.details``."""

    def __init__(self, kind: str, key: str) -> None:
        self.kind = kind
        self.key = key
        super().__init__()


class SelectionMoved(Message):
    """The cursor moved to another item; an open drawer follows it."""

    def __init__(self, kind: str, key: str) -> None:
        self.kind = kind
        self.key = key
        super().__init__()


class Reveal(Message):
    """Switch to a view, focus a widget in it and select an item."""

    def __init__(self, mode: str, target: str, key: str | None = None) -> None:
        self.mode = mode
        self.target = target
        self.key = key
        super().__init__()
