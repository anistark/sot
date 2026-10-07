"""
Network Connections Widget

Displays network connection monitoring with cyberpunk styling and animated access denied.
"""

import psutil
from rich.console import Group
from rich.text import Text

from .._theme import theme
from ..tui import refresh
from .base_widget import BaseWidget


class NetworkConnectionsWidget(BaseWidget):
    """Network Connection Monitoring widget showing active connections."""

    def __init__(self, **kwargs):
        super().__init__(title="Network Connections", **kwargs)
        self.animation_frame = 0

    def on_mount(self):
        self.update_content()
        self.every(refresh.CONNECTIONS, self.update_content)
        self.every(refresh.LOCK_ANIMATION, self.animate_frame)

    def animate_frame(self):
        """Update animation frame counter"""
        self.animation_frame = (self.animation_frame + 1) % 8

    def get_animated_lock(self):
        """Get sick animated lock ASCII art for access denied"""
        frame = self.animation_frame

        glitch_chars = ["█", "▓", "▒", "░", "▄", "▀", "▌", "▐"]
        glitch = glitch_chars[frame % len(glitch_chars)]

        scan_patterns = [
            "╔═══════════════╗",
            "╔▓══════════════╗",
            "╔═▓═════════════╗",
            "╔══▓════════════╗",
            "╔═══▓═══════════╗",
            "╔════▓══════════╗",
            "╔═════▓═════════╗",
            "╔══════▓════════╗",
        ]
        top_border = scan_patterns[frame % len(scan_patterns)]

        if frame % 4 < 2:
            lock_body = "▐█▌"
            lock_hook = "╭─╮"
        else:
            lock_body = "▐▓▌"
            lock_hook = "╭▒╮"

        if frame % 6 < 3:
            warning = "░ACCESS░"
            warning2 = "░DENIED░"
        else:
            warning = "▓ACCESS▓"
            warning2 = "▓DENIED▓"

        static_line = glitch * 15

        lock_art = f"""{top_border}
{warning}
{lock_hook}
{lock_body}
{warning2}
{static_line[:13]}
UNAUTHORIZED
{glitch}{glitch} ZONE {glitch}{glitch}
╚═══════════════╝"""

        return lock_art

    def update_content(self):
        """Update the network connections content with cyberpunk styling."""
        try:
            # Get network connections
            connections = psutil.net_connections(kind="inet")

            # Count by status
            status_counts = {}
            local_ports = set()
            remote_hosts = set()

            for conn in connections:
                status = conn.status if conn.status else "UNKNOWN"
                status_counts[status] = status_counts.get(status, 0) + 1

                if conn.laddr:
                    local_ports.add(conn.laddr.port)
                if conn.raddr:
                    remote_hosts.add(conn.raddr.ip)

            t = theme()
            c = t.colors
            good, ok, warn, _ = c.health
            matrix_lines = []

            established = status_counts.get("ESTABLISHED", 0)
            listening = status_counts.get("LISTEN", 0)
            time_wait = status_counts.get("TIME_WAIT", 0)

            status_line1 = Text()
            status_line1.append("▲ ACTIVE: ", style=good)
            status_line1.append(f"{established:>3}", style=f"bold {c.text}")

            status_line2 = Text()
            status_line2.append("◆ LISTEN: ", style=ok)
            status_line2.append(f"{listening:>3}", style=f"bold {c.text}")

            status_line3 = Text()
            status_line3.append("○ WAIT  : ", style=warn)
            status_line3.append(f"{time_wait:>3}", style=f"bold {c.text}")

            matrix_lines.extend([status_line1, status_line2, status_line3])

            matrix_lines.append(Text(""))

            flow_line = Text()
            flow_line.append(f"PORTS:{len(local_ports):>2} ", style=ok)
            flow_line.append("◄─►", style=c.text)
            flow_line.append(f" HOSTS:{len(remote_hosts):>2}", style=good)
            matrix_lines.append(flow_line)

            matrix_lines.append(Text(""))
            matrix_lines.append(Text("DATA STREAMS:", style=f"dim {c.text}"))

            conn_count = 0
            for conn in connections[:3]:
                if conn.raddr and conn.status == "ESTABLISHED":
                    stream_line = Text()
                    stream_line.append("▸ ", style=ok)
                    stream_line.append(f"{conn.raddr.ip}", style=good)
                    stream_line.append(f":{conn.raddr.port}", style=warn)
                    matrix_lines.append(stream_line)
                    conn_count += 1
                if conn_count >= 3:
                    break

            if conn_count == 0:
                matrix_lines.append(Text("▸ NO ACTIVE STREAMS", style=c.muted))

            content = Group(*matrix_lines)

        except (psutil.AccessDenied, psutil.NoSuchProcess):
            lock_art = self.get_animated_lock()
            content = Text(lock_art, style=theme().colors.health[3], justify="center")

        except Exception as e:
            content = Text(
                f"ERROR: {str(e)[:15]}...",
                style=theme().colors.health[3],
                justify="center",
            )

        self.update_panel_content(content)
