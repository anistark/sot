"""
Network Widget

Displays network interface statistics including upload/download speeds and IP addresses.
"""

import socket

import psutil
from rich.console import Group
from rich.table import Table
from rich.text import Text

from ..__about__ import __version__
from .._helpers import sizeof_fmt
from ..braille_stream import BrailleStream
from .base_widget import BaseWidget


def _autoselect_interface():
    """
    Auto-select the best network interface based on priority scoring.
    """
    try:
        stats = psutil.net_if_stats()
        score_dict = {}
        for name, stats in stats.items():
            if not stats.isup:
                score_dict[name] = 0
            elif (
                name.startswith("lo")
                or name.lower().startswith("loopback")
                or name.lower().startswith("docker")
                or name.lower().startswith("anpi")
            ):
                score_dict[name] = 1
            elif name.lower().startswith("fw") or name.lower().startswith("Bluetooth"):
                score_dict[name] = 2
            elif name.lower().startswith("en"):
                score_dict[name] = 4
            else:
                score_dict[name] = 3

        if not score_dict:
            return "lo"

        max_score = max(score_dict.values())
        max_keys = [key for key, score in score_dict.items() if score == max_score]
        return sorted(max_keys)[0]
    except Exception:
        return "lo"


def _validate_interface(interface_name):
    """
    Validate that the specified interface exists and is available.
    """
    try:
        available_interfaces = psutil.net_if_stats()
        return interface_name in available_interfaces
    except Exception:
        return False


class NetworkWidget(BaseWidget):
    """Network widget displaying interface statistics and IP addresses."""

    def __init__(self, interface: str | None = None, **kwargs):
        if interface is None:
            self.interface = _autoselect_interface()
            self.interface_source = "auto-detected"
        elif _validate_interface(interface):
            self.interface = interface
            self.interface_source = "user-specified"
        else:
            self.interface = _autoselect_interface()
            self.interface_source = f"fallback ('{interface}' not found)"

        self.sot_string = f"sot v{__version__}"
        super().__init__(title=f"Network - {self.interface}", **kwargs)

        self.interface_error = None
        if interface and not _validate_interface(interface):
            self.interface_error = (
                f"Interface '{interface}' not found, using '{self.interface}'"
            )

    def on_mount(self):
        from rich import box
        from rich.panel import Panel

        self.down_box = Panel(
            "",
            title="▼ down",
            title_align="left",
            style="aquamarine3",
            width=20,
            box=box.SQUARE,
        )
        self.up_box = Panel(
            "",
            title="▲ up",
            title_align="left",
            style="yellow",
            width=20,
            box=box.SQUARE,
        )
        self.table = Table(expand=True, show_header=False, padding=0, box=None)
        self.table.add_column("graph", no_wrap=True, ratio=1)
        self.table.add_column("box", no_wrap=True, width=20)
        self.table.add_row("", self.down_box)
        self.table.add_row("", self.up_box)

        self.group = Group(self.table, "", "")

        title_suffix = ""
        if self.interface_source == "auto-detected":
            title_suffix = " (auto)"
        elif "fallback" in self.interface_source:
            title_suffix = " (fallback)"
        elif self.interface_source == "user-specified":
            title_suffix = " (specified)"

        self.panel.title = f"[b]Network - {self.interface}[/]{title_suffix}"
        self.panel.subtitle = self.sot_string
        self.panel.subtitle_align = "right"

        self.last_net = None
        self.max_recv_bytes_s = 0
        self.max_recv_bytes_s_str = ""
        self.max_sent_bytes_s = 0
        self.max_sent_bytes_s_str = ""

        self.recv_stream = BrailleStream(20, 5, 0.0, 1.0e6)
        self.sent_stream = BrailleStream(20, 5, 0.0, 1.0e6, flipud=True)

        if self.interface_error:
            self.app.notify(self.interface_error, severity="warning", timeout=5)

        self.refresh_ips()
        self.refresh_panel()

        self.interval_s = 2.0
        self.set_interval(self.interval_s, self.refresh_panel)
        self.set_interval(60.0, self.refresh_ips)

    def refresh_ips(self):
        try:
            addrs = psutil.net_if_addrs()[self.interface]
            ipv4 = []
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ipv4.append(addr.address + " / " + addr.netmask)
            ipv6 = []
            for addr in addrs:
                if addr.family == socket.AF_INET6:
                    ipv6.append(addr.address)

            ipv4_str = "\n      ".join(ipv4) if ipv4 else "No IPv4 address"
            ipv6_str = "\n      ".join(ipv6) if ipv6 else "No IPv6 address"

            if len(self.group.renderables) >= 3:
                self.group.renderables[1] = f"[b]IPv4:[/] {ipv4_str}"
                self.group.renderables[2] = f"[b]IPv6:[/] {ipv6_str}"
        except KeyError:
            if len(self.group.renderables) >= 3:
                self.group.renderables[1] = (
                    f"[b]IPv4:[/] Interface '{self.interface}' not found"
                )
                self.group.renderables[2] = "[b]IPv6:[/] ---"
        except Exception as e:
            if len(self.group.renderables) >= 3:
                self.group.renderables[1] = f"[b]IPv4:[/] Error: {str(e)}"
                self.group.renderables[2] = "[b]IPv6:[/] ---"

    def refresh_panel(self):
        try:
            net = psutil.net_io_counters(pernic=True)[self.interface]
        except KeyError:
            error_msg = f"Interface '{self.interface}' not found"
            self.update_panel_content(Text(error_msg, style="red3"))
            return
        except Exception as e:
            error_msg = f"Error reading interface data: {str(e)}"
            self.update_panel_content(Text(error_msg, style="red3"))
            return

        if self.last_net is None:
            recv_bytes_s_string = ""
            sent_bytes_s_string = ""
        else:
            recv_bytes_s = (net.bytes_recv - self.last_net.bytes_recv) / self.interval_s
            recv_bytes_s_string = sizeof_fmt(recv_bytes_s, fmt=".1f") + "/s"
            sent_bytes_s = (net.bytes_sent - self.last_net.bytes_sent) / self.interval_s
            sent_bytes_s_string = sizeof_fmt(sent_bytes_s, fmt=".1f") + "/s"

            if recv_bytes_s > self.max_recv_bytes_s:
                self.max_recv_bytes_s = recv_bytes_s
                self.max_recv_bytes_s_str = sizeof_fmt(recv_bytes_s, fmt=".1f") + "/s"

            if sent_bytes_s > self.max_sent_bytes_s:
                self.max_sent_bytes_s = sent_bytes_s
                self.max_sent_bytes_s_str = sizeof_fmt(sent_bytes_s, fmt=".1f") + "/s"

            self.recv_stream.add_value(recv_bytes_s)
            self.sent_stream.add_value(sent_bytes_s)

        self.last_net = net

        total_recv_string = sizeof_fmt(net.bytes_recv, sep=" ", fmt=".1f")
        total_sent_string = sizeof_fmt(net.bytes_sent, sep=" ", fmt=".1f")

        self.down_box.renderable = "\n".join(
            [
                f"{recv_bytes_s_string}",
                f"max   {self.max_recv_bytes_s_str}",
                f"total {total_recv_string}",
            ]
        )
        self.up_box.renderable = "\n".join(
            [
                f"{sent_bytes_s_string}",
                f"max   {self.max_sent_bytes_s_str}",
                f"total {total_sent_string}",
            ]
        )
        self.refresh_graphs()
        self.update_panel_content(self.group)

    def refresh_graphs(self):
        if (
            hasattr(self.table.columns[0], "_cells")
            and len(self.table.columns[0]._cells) >= 2
        ):
            self.table.columns[0]._cells[0] = Text(
                "\n".join(self.recv_stream.graph), style="aquamarine3"
            )
            self.table.columns[0]._cells[1] = Text(
                "\n".join(self.sent_stream.graph), style="yellow"
            )
        else:
            if hasattr(self.table, "_clear"):
                self.table._clear()
            else:
                self.table = Table(expand=True, show_header=False, padding=0, box=None)
                self.table.add_column("graph", no_wrap=True, ratio=1)
                self.table.add_column("box", no_wrap=True, width=20)

            self.table.add_row(
                Text("\n".join(self.recv_stream.graph), style="aquamarine3"),
                self.down_box,
            )
            self.table.add_row(
                Text("\n".join(self.sent_stream.graph), style="yellow"), self.up_box
            )

            if len(self.group.renderables) > 0:
                self.group.renderables[0] = self.table

    async def on_resize(self, event):
        width = self.size.width - 25
        self.sent_stream.reset_width(width)
        self.recv_stream.reset_width(width)
        self.refresh_graphs()
