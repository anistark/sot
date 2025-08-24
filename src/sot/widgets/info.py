"""
Info Widget

Displays system information line with user, hostname, OS, uptime, and battery.
"""

import getpass
import platform
import time
from datetime import datetime, timedelta

import distro
import psutil
from rich.table import Table

from .base_widget import BaseWidget


def seconds_to_h_m(seconds):
    """Convert seconds to hours and minutes."""
    return seconds // 3600, (seconds // 60) % 60


class InfoWidget(BaseWidget):
    """Info line widget displaying system and user information."""

    def __init__(self, **kwargs):
        super().__init__(title="", border_style="", **kwargs)

    def on_mount(self):
        self.width = 0
        self.height = 0
        self.set_interval(1.0, self.update_info)

        # Get user and system information
        username = getpass.getuser()
        ustring = f"{username} @"
        node = platform.node()
        if node:
            ustring += f" [b]{platform.node()}[/]"

        system = platform.system()
        if system == "Linux":
            ri = distro.os_release_info()
            system_list = [ri["name"]]
            if "version_id" in ri:
                system_list.append(ri["version_id"])
            system_list.append(f"{platform.architecture()[0]} / {platform.release()}")
            system_string = " ".join(system_list)
        elif system == "Darwin":
            system_string = f" macOS {platform.mac_ver()[0]}"
        else:
            system_string = ""

        self.left_string = " ".join([ustring, system_string])
        self.boot_time = psutil.boot_time()

    def update_info(self):
        uptime = timedelta(seconds=time.time() - self.boot_time)
        h, m = seconds_to_h_m(uptime.seconds)

        right = [f"💚 {uptime.days}d, {h}:{m:02d}h"]

        bat = psutil.sensors_battery()
        if bat is not None:
            bat_string = f"{bat.percent:.1f}%"
            if bat.power_plugged:
                bat_string = "🔋 [aquamarine3]" + bat_string + "[/]"
            elif bat.percent < 10:
                bat_string = "🪫 [red3 reverse bold]" + bat_string + "[/]"
            elif bat.percent < 15:
                bat_string = "🪫 [slate_blue1]" + bat_string + "[/]"
            elif bat.percent < 20:
                bat_string = "🔋 [yellow]" + bat_string + "[/]"

            # Handle invalid battery percentages
            if bat.percent < 0 or bat.percent > 100:
                bat_string = "[red3 reverse bold]⚠ [/] " + bat_string

            right.append(bat_string)

        table = Table(show_header=False, expand=True, box=None, padding=0)
        if self.width < 100:
            table.add_column(justify="left", no_wrap=True)
            table.add_column(justify="right", no_wrap=True)
            table.add_row(self.left_string, ", ".join(right))
        else:
            table.add_column(justify="left", no_wrap=True, ratio=1)
            table.add_column(justify="center", no_wrap=True, ratio=1)
            table.add_column(justify="right", no_wrap=True, ratio=1)
            table.add_row(
                self.left_string, datetime.now().strftime("%c"), "  ".join(right)
            )

        self.update_panel_content(table)

    def render(self):
        panel = getattr(self, "panel", None)
        if panel and hasattr(panel, "renderable"):
            return panel.renderable or Table()
        return Table()

    async def on_resize(self, event):
        self.width = self.size.width
        self.height = self.size.height
