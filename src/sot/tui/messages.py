"""Messages any view can post for the app to handle."""

from textual.message import Message


class ProcessSelected(Message):
    """Show details for a process."""

    def __init__(self, process_info: dict) -> None:
        self.process_info = process_info
        super().__init__()


class ProcessAction(Message):
    """Ask to kill or terminate a process; the app confirms first."""

    def __init__(self, action: str, process_info: dict) -> None:
        self.action = action
        self.process_info = process_info
        super().__init__()
