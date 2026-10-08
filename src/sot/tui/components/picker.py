"""Modal list to pick one value."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option


class PickerScreen(ModalScreen[str | None]):
    """Dismisses with the chosen value, or ``None`` when cancelled."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", id="sot.picker.cancel")]

    DEFAULT_CSS = """
    PickerScreen {
        align: center middle;
    }

    PickerScreen > Vertical {
        width: 70;
        max-height: 80%;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $panel;
    }

    PickerScreen #title {
        text-style: bold;
        margin-bottom: 1;
    }

    PickerScreen OptionList {
        height: auto;
        max-height: 20;
        border: none;
    }
    """

    def __init__(self, title: str, choices: list[tuple[str, str]]) -> None:
        super().__init__()
        self.title_text = title
        self.choices = choices

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.title_text, id="title")
            yield OptionList(
                *(Option(label, id=value) for label, value in self.choices)
            )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def action_cancel(self) -> None:
        self.dismiss(None)
