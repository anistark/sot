"""Confirmation dialog for destructive actions."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label

from ..tui import keymap


class ConfirmModal(ModalScreen[bool]):
    """Ask before doing something; dismisses with ``True`` when confirmed."""

    BINDINGS = [*keymap.CONFIRM]
    AUTO_FOCUS = "#cancel"

    DEFAULT_CSS = """
    ConfirmModal {
        align: center middle;
    }

    ConfirmModal > Vertical {
        width: 60;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $panel;
    }

    ConfirmModal.-danger > Vertical {
        border: round $error;
    }

    ConfirmModal #title {
        text-style: bold;
    }

    ConfirmModal #message {
        margin: 1 0;
        color: $text-muted;
    }

    ConfirmModal #buttons {
        height: auto;
        align-horizontal: right;
    }

    ConfirmModal Button {
        margin-left: 1;
    }
    """

    def __init__(
        self,
        title: str,
        message: str,
        confirm_label: str = "Confirm",
        danger: bool = True,
    ) -> None:
        super().__init__(classes="-danger" if danger else None)
        self.title_text = title
        self.message_text = message
        self.confirm_label = confirm_label
        self.danger = danger

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.title_text, id="title")
            yield Label(self.message_text, id="message")
            with Horizontal(id="buttons"):
                yield Button(
                    f"{self.confirm_label} (y)",
                    variant="error" if self.danger else "primary",
                    id="confirm",
                )
                yield Button("Cancel (n)", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
