from __future__ import annotations

import argparse
import os
import platform
from sys import version_info

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Header

from .__about__ import __current_year__, __version__
from ._gpu import has_gpu
from ._theme import DEFAULT_THEME, THEMES, set_theme, theme
from .tui.base import SotBaseApp
from .widgets import (
    CPUWidget,
    DiskWidget,
    GpuWidget,
    HealthScoreWidget,
    InfoWidget,
    MemoryWidget,
    NetworkConnectionsWidget,
    NetworkWidget,
    ProcessesWidget,
    SotWidget,
)


class CustomHelpFormatter(argparse.RawTextHelpFormatter):
    """Custom formatter to display subcommands."""

    def _format_action(self, action):
        # Get the default formatted action
        result = super()._format_action(action)

        # If this is a subparser action, reformat it
        if isinstance(action, argparse._SubParsersAction):
            # Get the metavar (e.g., "{info,bench}")
            metavar = self._metavar_formatter(action, action.dest)(1)[0]

            # Split the result into lines
            lines = result.split("\n")

            # Build new output with metavar on same line as title
            new_lines = []
            for line in lines:
                # Skip the standalone metavar line
                if (
                    line.strip()
                    and line.strip().startswith("{")
                    and line.strip().endswith("}")
                ):
                    continue
                # Skip empty lines at the start
                if not line.strip() and not new_lines:
                    continue
                new_lines.append(line)

            # Manually construct the section with metavar on same line
            parts = [f"commands: {metavar}"]
            parts.extend(new_lines)
            result = "\n".join(parts)

        return result

    def start_section(self, heading):
        # Override to prevent "positional arguments:" heading for subparsers
        if heading == "positional arguments":
            # Start section with no heading (empty string)
            super().start_section(None)
        else:
            super().start_section(heading)


# Main SOT Application
class SotApp(SotBaseApp):
    """SOT - System Observation Tool with interactive process management."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3;
        grid-columns: 35fr 20fr 45fr;
        grid-rows: 1 1fr 1.2fr 1.1fr;
    }

    #info-line {
        column-span: 3;
    }

    #procs-list {
        row-span: 2;
    }
    """

    def __init__(
        self,
        net_interface=None,
        disk_mountpoint=None,
        log_file=None,
        theme_name=DEFAULT_THEME,
    ):
        super().__init__(theme_name)
        self.net_interface = net_interface
        self.disk_mountpoint = disk_mountpoint
        self.log_file = log_file

        if log_file:
            os.environ["TEXTUAL_LOG"] = log_file

    def compose(self) -> ComposeResult:
        yield Header()

        # Row 1: Info line (spans all 3 columns)
        info_line = InfoWidget()
        info_line.id = "info-line"
        yield info_line

        # Row 2: CPU, Health Score, Process List (starts)
        cpu_widget = CPUWidget()
        cpu_widget.id = "cpu-widget"
        yield cpu_widget

        health_widget = HealthScoreWidget()
        health_widget.id = "health-widget"
        yield health_widget

        procs_list = ProcessesWidget()
        procs_list.id = "procs-list"
        yield procs_list

        # Row 3: Memory, GPU/Sot Widget (Process List continues)
        mem_widget = MemoryWidget()
        mem_widget.id = "mem-widget"
        yield mem_widget

        # Show live GPU stats when a GPU is detected; otherwise keep the
        # decorative SOT animation in this slot.
        if has_gpu():
            gpu_widget = GpuWidget()
            gpu_widget.id = "gpu-widget"
            yield gpu_widget
        else:
            sot_widget = SotWidget()
            sot_widget.id = "sot-widget"
            yield sot_widget

        # Row 4: Disk, Network Connections, Network Widget
        disk_widget = DiskWidget(self.disk_mountpoint)
        disk_widget.id = "disk-widget"
        yield disk_widget

        connections_widget = NetworkConnectionsWidget()
        connections_widget.id = "connections-widget"
        yield connections_widget

        # Pass the network interface to the NetworkWidget
        net_widget = NetworkWidget(self.net_interface)
        net_widget.id = "net-widget"
        yield net_widget

    def on_mount(self) -> None:
        self.title = "SOT"

        subtitle_parts = []
        if self.net_interface:
            subtitle_parts.append(f"Net: {self.net_interface}")
        if self.disk_mountpoint:
            subtitle_parts.append(f"Disk: {self.disk_mountpoint}")

        if subtitle_parts:
            self.sub_title = f"System Observation Tool - {', '.join(subtitle_parts)}"
        else:
            self.sub_title = "System Observation Tool"

        # Set initial focus to the process list for interactive features
        self.set_focus(self.query_one("#procs-list"))

        # Memory graphs have a fixed height; size their grid row to match.
        mem = self.query_one("#mem-widget", MemoryWidget)
        self.screen.styles.grid_rows = f"1 1fr {mem.panel_height} 1.1fr"


def _show_styled_version():
    """Display a clean and focused version information."""
    console = Console()
    t = theme()
    c = t.colors

    title_text = Text()
    for line in t.design.logo:
        title_text.append(f"{line}\n", style=f"bold {c.logo}")
    title_text.append("\n")
    title_text.append("System Observation Tool", style=f"bold {c.accent}")

    version_table = Table(show_header=False, box=None, padding=(0, 1))
    version_table.add_column("Label", style=c.muted, width=12)
    version_table.add_column("Value", style=f"bold {c.text}")

    python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    system_info = platform.system()
    if system_info == "Darwin":
        system_info = f"macOS {platform.mac_ver()[0]}"
    elif system_info == "Linux":
        try:
            import distro

            system_info = f"Linux ({distro.name()} {distro.version()})"
        except ImportError:
            system_info = f"Linux {platform.release()}"

    version_table.add_row("Version:", f"[{c.ok}]{__version__}[/]")
    version_table.add_row("Python:", f"[{c.info}]{python_version}[/]")
    version_table.add_row("Platform:", f"[{c.secondary}]{system_info}[/]")
    version_table.add_row("Architecture:", f"[{c.primary}]{platform.machine()}[/]")

    main_panel = Panel(
        title_text,
        title=f"[bold {c.text}]System Observation Tool[/]",
        title_align="center",
        border_style=c.accent,
        box=t.design.app_box,
        padding=(1, 2),
    )

    info_panel = Panel(
        version_table,
        title="[bold]📋 Version Information[/]",
        border_style=c.ok,
        box=t.design.app_box,
        padding=(1, 2),
    )

    console.print(main_panel)
    console.print()
    console.print(info_panel)
    console.print()

    # Footer with copyright and links
    footer_text = Text()
    footer_text.append("MIT License © 2024-", style=c.muted)
    footer_text.append(f"{__current_year__}", style=c.muted)
    footer_text.append(" Kumar Anirudha\n", style=c.muted)
    footer_text.append("🔗 ", style=c.info)
    footer_text.append(
        "https://github.com/anistark/sot", style="link https://github.com/anistark/sot"
    )
    footer_text.append(" | 📖 ", style=c.ok)
    footer_text.append("sot --help", style=f"bold {c.text}")
    footer_text.append(" | 🚀 ", style=c.primary)
    footer_text.append("sot", style=f"bold {c.accent}")

    console.print(
        Panel(footer_text, border_style=c.muted, box=t.design.app_box, padding=(0, 2))
    )


def _get_volume_display_name(mp: str) -> str:
    """Get display name for a volume mountpoint."""
    import psutil

    from ._helpers import sizeof_fmt

    name = "Macintosh HD" if mp == "/" else mp.split("/")[-1]
    try:
        usage_path = "/System/Volumes/Data" if mp == "/" else mp
        usage = psutil.disk_usage(usage_path)
        total = sizeof_fmt(usage.total, fmt=".1f")
        return f"{name} ({total}, {usage.percent:.1f}% used)"
    except (PermissionError, OSError):
        return name


def _read_arrow_key(stdin) -> str | None:
    """Read arrow key escape sequence, return 'up', 'down', or None."""
    ch2 = stdin.read(1)
    if ch2 != "[":
        return None
    ch3 = stdin.read(1)
    return {"A": "up", "B": "down"}.get(ch3)


def _interactive_disk_select(volumes: list[str]) -> str | None:  # noqa: C901
    """Interactive volume selector using arrow keys."""
    import sys

    if not sys.stdin.isatty():
        print("💾 Available volumes:\n")
        for i, mp in enumerate(volumes, 1):
            print(f"  [{i}] {_get_volume_display_name(mp)}")
        print("\n❌ Interactive selection requires a terminal.")
        return None

    import termios
    import tty

    def render(selected_idx: int):
        sys.stdout.write("\033[?25l\033[H\033[2J\033[H")
        sys.stdout.write(
            "💾 Select a volume (↑/↓ to move, Enter to select, q to cancel):\r\n\r\n"
        )
        for i, mp in enumerate(volumes):
            info = _get_volume_display_name(mp)
            prefix = "  \033[1;36m❯" if i == selected_idx else "   "
            suffix = "\033[0m" if i == selected_idx else ""
            sys.stdout.write(f"{prefix} {info}{suffix}\r\n")
        sys.stdout.flush()

    selected_idx = 0
    render(selected_idx)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                arrow = _read_arrow_key(sys.stdin)
                if arrow == "up":
                    selected_idx = (selected_idx - 1) % len(volumes)
                elif arrow == "down":
                    selected_idx = (selected_idx + 1) % len(volumes)
                render(selected_idx)
            elif ch in ("\r", "\n"):
                break
            elif ch in ("q", "Q", "\x03"):
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                sys.stdout.write("\033[?25h")
                print("\n❌ Selection cancelled.")
                return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\033[?25h")

    print()
    return volumes[selected_idx]


def run(argv=None):  # noqa: C901
    parser = argparse.ArgumentParser(
        description="Command-line System Obervation Tool ≈",
        formatter_class=CustomHelpFormatter,
        add_help=False,
    )

    parser.add_argument(
        "--help",
        "-H",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )

    parser.add_argument(
        "--version",
        "-V",
        action="store_true",
        help="Display version information with styling",
    )

    parser.add_argument(
        "--log",
        "-L",
        type=str,
        default=None,
        help="Debug log file path (enables debug logging)",
    )

    parser.add_argument(
        "--net",
        "-N",
        type=str,
        default=None,
        help="Network interface to display (default: auto-detect best interface)",
    )

    parser.add_argument(
        "--disk",
        "-D",
        type=str,
        nargs="?",
        const="__select__",
        default=None,
        help="Disk mountpoint to display (use without value for interactive selection)",
    )

    parser.add_argument(
        "--theme",
        "-T",
        choices=list(THEMES),
        metavar="THEME",
        default=os.environ.get("SOT_THEME", DEFAULT_THEME),
        help=f"Color theme: {', '.join(THEMES)} (default: $SOT_THEME or classic)",
    )
    # Create subparsers for subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="{info,bench,disk,clean,ps}",
    )

    # Add info subcommand
    subparsers.add_parser(
        "info",
        help="Display system information",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Add bench subcommand
    bench_parser = subparsers.add_parser(
        "bench",
        help="Disk benchmarking",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    bench_parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file for benchmark results (JSON format)",
    )
    bench_parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=10.0,
        help="Duration for each benchmark test in seconds (default: 10s)",
    )

    # Add disk subcommand
    disk_parser = subparsers.add_parser(
        "disk",
        help="Interactive disk information viewer",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    disk_parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="Print disks and partitions as a plain list instead of the TUI",
    )

    # Add clean subcommand
    clean_parser = subparsers.add_parser(
        "clean",
        help="Deep clean system caches, logs, and temp files",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without actually deleting",
    )

    # Add ps subcommand
    subparsers.add_parser(
        "ps",
        help="Interactive process viewer",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    args = parser.parse_args(argv)

    if args.theme not in THEMES:
        print(f"❌ Unknown theme '{args.theme}'. Available: {', '.join(THEMES)}")
        return 1
    set_theme(args.theme)

    # Handle info subcommand
    if args.command == "info":
        from .info.cli import info_command

        return info_command(args)

    # Handle bench subcommand
    if args.command == "bench":
        from .bench.cli import benchmark_command

        return benchmark_command(args)

    # Handle disk subcommand
    if args.command == "disk":
        from .disk.cli import disk_command

        return disk_command(args)

    # Handle clean subcommand
    if args.command == "clean":
        from .clean.cli import clean_command

        return clean_command(args)

    # Handle ps subcommand
    if args.command == "ps":
        from .ps.cli import ps_command

        return ps_command(args)

    # Handle version display
    if args.version:
        _show_styled_version()
        return 0

    # Validate network interface if specified
    if args.net:
        import psutil

        available_interfaces = list(psutil.net_if_stats().keys())
        if args.net not in available_interfaces:
            print(f"❌ Error: Network interface '{args.net}' not found.")
            print(f"📡 Available interfaces: {', '.join(available_interfaces)}")
            return 1

    # Validate disk mountpoint if specified
    if args.disk:
        import psutil

        partitions = psutil.disk_partitions()
        all_mountpoints = [p.mountpoint for p in partitions]

        # Filter to show only user-relevant volumes (root + /Volumes/*)
        volumes = [
            mp for mp in all_mountpoints if mp == "/" or mp.startswith("/Volumes/")
        ]

        if args.disk == "__select__" or args.disk not in all_mountpoints:
            if args.disk != "__select__":
                print(f"❌ Disk mountpoint '{args.disk}' not found.\n")

            if not volumes:
                print("❌ No volumes found.")
                return 1

            selected = _interactive_disk_select(volumes)
            if selected is None:
                return 1
            args.disk = selected

    # Set up logging before using SotApp (Textual reads TEXTUAL_LOG at module import time)
    if args.log:
        os.environ["TEXTUAL_LOG"] = args.log
        # Reload textual.constants to pick up the new TEXTUAL_LOG value
        import importlib

        import textual.constants

        importlib.reload(textual.constants)
        print(f"🐛 Debug logging enabled: {args.log}")

    # Create and run the application with the specified options
    app = SotApp(
        net_interface=args.net,
        disk_mountpoint=args.disk,
        log_file=args.log,
        theme_name=args.theme,
    )

    if args.net:
        print(f"📡 Using network interface: {args.net}")
    if args.disk:
        print(f"💾 Using disk mountpoint: {args.disk}")

    try:
        app.run()
    except KeyboardInterrupt:
        print("\n👋 SOT terminated by user")
        return 0
    except Exception as e:
        print(f"💥 SOT crashed: {e}")
        if args.log:
            print(f"📋 Check log file for details: {args.log}")
        return 1

    return 0


# Deprecated. Can remove in future versions.
def _get_version_text():
    """Generate simple version information string for fallback."""
    python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

    return "\n".join(
        [
            f"sot {__version__} [Python {python_version}]",
            f"MIT License © 2024-{__current_year__} Kumar Anirudha",
        ]
    )
