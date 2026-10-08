"""Behavior shared by every SOT app: themes, confirmations, process actions."""

from __future__ import annotations

from pathlib import Path

from textual.app import App
from textual.command import CommandPalette
from textual.theme import Theme, ThemeProvider

from .._config import remember_theme
from .._process_utils import ProcessActionResult, run_process_action
from .._theme import THEMES, set_theme, theme
from ..widgets.confirmation_modal import ConfirmModal
from . import keymap
from .messages import ProcessAction


class SotThemeProvider(ThemeProvider):
    """Theme picker limited to SOT themes."""

    @property
    def commands(self):
        return [(name, cb) for name, cb in super().commands if name in THEMES]


class SotBaseApp(App):
    CSS_PATH = Path(__file__).parent.parent / "styles" / "sot.tcss"
    BINDINGS = [keymap.QUIT, keymap.HELP]

    def __init__(self, theme_name: str | None = None) -> None:
        super().__init__()
        # Widget data kept across rebuilds, see ``SotWidget``.
        self.widget_state: dict[str, dict] = {}
        for t in THEMES.values():
            if t.textual is not None:
                self.register_theme(t.textual)
        name = set_theme(theme_name or theme().name).name
        self._chosen_theme = name
        if name in self.available_themes:
            self.theme = name

    def on_mount(self) -> None:
        self.theme_changed_signal.subscribe(self, self._theme_changed)

    def search_themes(self) -> None:
        self.push_screen(
            CommandPalette(
                providers=[SotThemeProvider], placeholder="Search for themes…"
            )
        )

    def _theme_changed(self, new: Theme) -> None:
        if new.name not in THEMES:
            return
        set_theme(new.name)
        if new.name != self._chosen_theme:
            self._chosen_theme = new.name
            remember_theme(new.name)

    def action_toggle_help(self) -> None:
        if self.screen.query("HelpPanel"):
            self.action_hide_help_panel()
        else:
            self.action_show_help_panel()

    def notify_result(self, result: ProcessActionResult) -> None:
        self.notify(result.message, severity=result.severity, timeout=4)

    def on_process_action(self, message: ProcessAction) -> None:
        info = message.process_info
        pid = info.get("pid")
        name = info.get("name") or "Unknown"
        action = message.action
        if not isinstance(pid, int):
            self.notify_result(
                ProcessActionResult(False, "No process to act on", "error")
            )
            return

        signal = "SIGKILL" if action == "kill" else "SIGTERM"

        def done(confirmed: bool | None) -> None:
            if not confirmed:
                return
            result = run_process_action(action, pid, name)
            self.log(f"{action} {name} ({pid}): {result.message}")
            self.notify_result(result)

        self.push_screen(
            ConfirmModal(
                f"{action.title()} {name}?",
                f"PID {pid} will be sent {signal}.",
                confirm_label=action.title(),
            ),
            done,
        )
