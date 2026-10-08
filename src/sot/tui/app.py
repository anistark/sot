"""The SOT app: one app, a view per mode."""

from __future__ import annotations

import os

from . import keymap
from .base import SotBaseApp
from .commands import SotCommands
from .components.picker import PickerScreen
from .messages import Reveal
from .screen import SotScreen
from .views.bench import BenchScreen
from .views.clean import CleanScreen
from .views.disks import DisksScreen
from .views.overview import OverviewScreen
from .views.processes import ProcessesScreen
from .views.system import SystemScreen


class SotApp(SotBaseApp):
    """SOT - System Observation Tool."""

    MODES = {
        "overview": OverviewScreen,
        "processes": ProcessesScreen,
        "disks": DisksScreen,
        "system": SystemScreen,
        "bench": BenchScreen,
        "clean": CleanScreen,
    }
    BINDINGS = [keymap.QUIT, keymap.HELP, *keymap.VIEW_KEYS]
    COMMANDS = SotBaseApp.COMMANDS | {SotCommands}

    def __init__(
        self,
        start_mode: str = "overview",
        net_interface: str | None = None,
        disk_mountpoint: str | None = None,
        log_file: str | None = None,
        theme_name: str | None = None,
        pick_disk: bool = False,
        bench_duration: float = 10.0,
        keymap: dict[str, str] | None = None,
    ):
        # Textual reads the starting mode while initialising the app.
        self.DEFAULT_MODE = start_mode  # type: ignore[misc]
        super().__init__(theme_name)
        self.title = "SOT"
        self.net_interface = net_interface
        self.disk_mountpoint = disk_mountpoint
        self.log_file = log_file
        self.pick_disk = pick_disk
        self.user_keymap = keymap or {}
        self.bench_duration = bench_duration
        # Where `esc` returns to after a drill-down.
        self.back_mode: str | None = None

        if log_file:
            os.environ["TEXTUAL_LOG"] = log_file

    def on_mount(self) -> None:
        if self.user_keymap:
            unknown = set(self.user_keymap) - set(keymap.all_bindings())
            if unknown:
                self.notify(
                    f"Unknown key binding ids: {', '.join(sorted(unknown))}",
                    severity="warning",
                )
            self.set_keymap(self.user_keymap)
        if self.pick_disk:
            from ..disk.volumes import volume_choices

            self.push_screen(
                PickerScreen("Pick a disk to monitor", volume_choices()),
                self._disk_picked,
            )

    async def _disk_picked(self, mountpoint: str | None) -> None:
        if mountpoint is None:
            return
        self.disk_mountpoint = mountpoint
        if isinstance(self.screen, SotScreen):
            await self.screen.rebuild()

    async def action_switch_mode(self, mode: str) -> None:
        self.back_mode = None
        await super().action_switch_mode(mode)

    async def on_reveal(self, message: Reveal) -> None:
        origin = self.current_mode
        await self.switch_mode(message.mode)
        self.back_mode = origin if origin != message.mode else None
        if isinstance(self.screen, SotScreen):
            self.screen.reveal(message.target, message.key)
