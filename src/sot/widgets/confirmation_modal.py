"""
Confirmation Modal Widget

Simple confirmation dialog using Textual best practices.
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmationModal(ModalScreen[bool]):
    """A modal for confirming actions. Returns True if confirmed, False if cancelled."""

    class Confirmed(Message):
        """Posted when user confirms."""

        def __init__(self, action_data: dict) -> None:
            self.action_data = action_data
            super().__init__()

    BINDINGS = [("escape", "cancel")]

    CSS = """
    ConfirmationModal {
        align: center middle;
    }

    ConfirmationModal > Container {
        width: 60;
        height: 9;
        border: solid $accent;
        background: $panel;
    }

    ConfirmationModal #title {
        margin: 1 2;
        width: 1fr;
    }

    ConfirmationModal #message {
        margin: 0 2;
        width: 1fr;
    }

    ConfirmationModal #buttons {
        margin: 1 2 0 2;
        width: 1fr;
    }

    ConfirmationModal Button {
        margin-right: 1;
    }
    """

    def __init__(self, title: str, message: str, action_data: dict = None) -> None:
        super().__init__()
        self.title_text = title
        self.message_text = message
        self.action_data = action_data or {}

    def compose(self) -> ComposeResult:
        with Container():
            yield Label(self.title_text, id="title")
            yield Label(self.message_text, id="message")
            with Horizontal(id="buttons"):
                yield Button("Kill", variant="error", id="confirm")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "confirm":
            self.app.post_message(self.Confirmed(self.action_data))
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Handle escape key."""
        self.dismiss(False)
