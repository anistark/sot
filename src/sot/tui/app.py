"""The SOT app: one app, a view per mode."""

from __future__ import annotations

import os

from . import keymap
from .base import SotBaseApp
from .views.disks import DisksScreen
from .views.overview import OverviewScreen
from .views.processes import ProcessesScreen


class SotApp(SotBaseApp):
    """SOT - System Observation Tool."""

    MODES = {
        "overview": OverviewScreen,
        "processes": ProcessesScreen,
        "disks": DisksScreen,
    }
    BINDINGS = [keymap.QUIT, keymap.HELP, *keymap.VIEW_KEYS]

    def __init__(
        self,
        start_mode: str = "overview",
        net_interface: str | None = None,
        disk_mountpoint: str | None = None,
        log_file: str | None = None,
        theme_name: str | None = None,
    ):
        # Textual reads the starting mode while initialising the app.
        self.DEFAULT_MODE = start_mode  # type: ignore[misc]
        super().__init__(theme_name)
        self.title = "SOT"
        self.net_interface = net_interface
        self.disk_mountpoint = disk_mountpoint
        self.log_file = log_file

        if log_file:
            os.environ["TEXTUAL_LOG"] = log_file
