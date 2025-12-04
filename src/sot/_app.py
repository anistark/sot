from __future__ import annotations

import argparse
import os
import platform
from sys import version_info

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Header

from .__about__ import __current_year__, __version__
from .widgets import (
    CPUWidget,
    DiskWidget,
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
            lines = result.split('\n')

            # Build new output with metavar on same line as title
            new_lines = []
            for line in lines:
                # Skip the standalone metavar line
                if line.strip() and line.strip().startswith('{') and line.strip().endswith('}'):
                    continue
                # Skip empty lines at the start
                if not line.strip() and not new_lines:
                    continue
                new_lines.append(line)

            # Manually construct the section with metavar on same line
            parts = [f"commands: {metavar}"]
            parts.extend(new_lines)
            result = '\n'.join(parts)

        return result

    def start_section(self, heading):
        # Override to prevent "positional arguments:" heading for subparsers
        if heading == 'positional arguments':
            # Start section with no heading (empty string)
            super().start_section(None)
        else:
            super().start_section(heading)


# Main SOT Application
class SotApp(App):
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

    def __init__(self, net_interface=None, log_file=None):
        super().__init__()
        self.net_interface = net_interface
        self.log_file = log_file
        self.pending_kill = None
        self._waiting_for_kill_confirmation = False

        # Set up logging if specified
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

        # Row 3: Memory, Sot Widget (Process List continues)
        mem_widget = MemoryWidget()
        mem_widget.id = "mem-widget"
        yield mem_widget

        sot_widget = SotWidget()
        sot_widget.id = "sot-widget"
        yield sot_widget

        # Row 4: Disk, Network Connections, Network Widget
        disk_widget = DiskWidget()
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

        # Update subtitle to show active interface if specified
        if self.net_interface:
            self.sub_title = f"System Observation Tool - Net: {self.net_interface}"
        else:
            self.sub_title = "System Observation Tool"

        # Set initial focus to the process list for interactive features
        self.set_focus(self.query_one("#procs-list"))

    async def on_load(self, _):
        self.bind("q", "quit")

    def on_key(self, event) -> None:
        """Handle key events for kill confirmation."""
        if self._waiting_for_kill_confirmation:
            if event.key == "y":
                self._waiting_for_kill_confirmation = False
                self._kill_process(self.pending_kill["process_info"])
            else:
                # Any other key cancels
                self._waiting_for_kill_confirmation = False
                self.notify("❌ Kill cancelled", timeout=2)
            event.prevent_default()

    def on_processes_widget_process_selected(
        self, message: ProcessesWidget.ProcessSelected
    ) -> None:
        """Handle process selection from the process list with enhanced network details."""
        process_info = message.process_info
        process_name = process_info.get("name", "Unknown")
        process_id = process_info.get("pid", "N/A")
        cpu_percent = process_info.get("cpu_percent", 0) or 0

        details = [f"📋 {process_name} (PID: {process_id})"]
        details.append(f"💻 CPU: {cpu_percent:.1f}%")
        memory_info = process_info.get("memory_info")
        if memory_info:
            from ._helpers import sizeof_fmt

            memory_str = sizeof_fmt(memory_info.rss, suffix="", sep="")
            details.append(f"🧠 Memory: {memory_str}")

        num_threads = process_info.get("num_threads")
        if num_threads:
            details.append(f"🧵 Threads: {num_threads}")

        total_io_rate = process_info.get("total_io_rate", 0)
        if total_io_rate > 0:
            from ._helpers import sizeof_fmt

            net_io_str = sizeof_fmt(total_io_rate, fmt=".1f", suffix="", sep="") + "/s"
            details.append(f"🌐 Net I/O: {net_io_str}")

        num_connections = process_info.get("num_connections", 0)
        if num_connections > 0:
            details.append(f"🔗 Connections: {num_connections}")

        status = process_info.get("status")
        if status:
            status_emoji = {
                "running": "🏃",
                "sleeping": "😴",
                "stopped": "⏸️",
                "zombie": "🧟",
                "idle": "💤",
            }.get(status, "❓")
            details.append(f"{status_emoji} Status: {status}")

        if self.log_file:
            self.log(f"Process selected: {process_name} (PID: {process_id})")

        detailed_message = "\n".join(details)

        self.notify(
            detailed_message,
            timeout=5,
        )

    def on_processes_widget_kill_request(
        self, message: ProcessesWidget.KillRequest
    ) -> None:
        """Handle kill request by showing a pending confirmation."""
        process_info = message.process_info
        process_name = process_info.get("name", "Unknown")
        process_id = process_info.get("pid", "N/A")

        # Store pending kill for confirmation
        self.pending_kill = {
            "process_info": process_info,
            "process_name": process_name,
            "process_id": process_id,
            "timestamp": 0,
        }

        # Show confirmation prompt with danger emoji and error severity (red)
        self.notify(
            f"⚠️  KILL {process_name}? Press 'y' to confirm, any key to cancel",
            severity="error",
            timeout=10,
        )

        # Listen for confirmation key in the next on_key event
        self._waiting_for_kill_confirmation = True

        # Auto-cancel after 10 seconds (matching notification timeout)
        def reset_confirmation():
            if self._waiting_for_kill_confirmation:
                self._waiting_for_kill_confirmation = False
                self.notify("❌ Kill action expired", severity="error", timeout=2)

        self.set_timer(reset_confirmation, 10.0)

    def _kill_process(self, process_info: dict) -> None:
        """Execute the kill process action."""
        import psutil

        process_id = process_info.get("pid")
        process_name = process_info.get("name", "Unknown")

        if not process_id:
            self.notify("❌ Invalid process ID", severity="error", timeout=3)
            return

        # Log the action attempt if logging is enabled
        if self.log_file:
            self.log(f"Attempting to kill process: {process_name} (PID: {process_id})")

        try:
            target_process = psutil.Process(process_id)
            target_process.kill()
            if self.log_file:
                self.log(
                    f"Successfully killed process: {process_name} (PID: {process_id})"
                )
            self.notify(
                f"💥 Killed {process_name} (PID: {process_id})",
                severity="warning",
                timeout=4,
            )

        except psutil.ZombieProcess:
            self._handle_zombie_process_error(process_name, process_id)
        except psutil.NoSuchProcess:
            self._handle_no_such_process_error(process_id)
        except psutil.AccessDenied:
            self._handle_access_denied_error(process_name, process_id)
        except Exception as error:
            self._handle_general_process_error("kill", process_name, error)

    def on_processes_widget_process_action(
        self, message: ProcessesWidget.ProcessAction
    ) -> None:
        """Handle process actions like kill/terminate from the process list."""
        import psutil

        action = message.action
        process_info = message.process_info
        process_id = process_info.get("pid")
        process_name = process_info.get("name", "Unknown")

        if not process_id:
            self.notify("❌ Invalid process ID", severity="error", timeout=3)
            return

        # Log the action attempt if logging is enabled
        if self.log_file:
            self.log(
                f"Attempting to {action} process: {process_name} (PID: {process_id})"
            )

        try:
            target_process = psutil.Process(process_id)
            self._execute_process_action(
                target_process, action, process_name, process_id
            )

        except psutil.ZombieProcess:
            self._handle_zombie_process_error(process_name, process_id)
        except psutil.NoSuchProcess:
            self._handle_no_such_process_error(process_id)
        except psutil.AccessDenied:
            self._handle_access_denied_error(process_name, process_id)
        except Exception as error:
            self._handle_general_process_error(action, process_name, error)

    def _execute_process_action(self, target_process, action, process_name, process_id):
        """Execute the specified action on the target process."""
        if action == "kill":
            target_process.kill()
            if self.log_file:
                self.log(
                    f"Successfully killed process: {process_name} (PID: {process_id})"
                )
            self.notify(
                f"💥 Killed {process_name} (PID: {process_id})",
                severity="warning",
                timeout=4,
            )
        elif action == "terminate":
            target_process.terminate()
            if self.log_file:
                self.log(
                    f"Successfully terminated process: {process_name} (PID: {process_id})"
                )
            self.notify(
                f"🛑 Terminated {process_name} (PID: {process_id})",
                severity="information",
                timeout=4,
            )
        else:
            self.notify(f"❓ Unknown action: {action}", severity="error", timeout=3)

    def _handle_no_such_process_error(self, process_id):
        """Handle the case when a process no longer exists."""
        error_msg = f"Process {process_id} no longer exists"
        if self.log_file:
            self.log(f"Error: {error_msg}")
        self.notify(
            f"❌ {error_msg}",
            severity="error",
            timeout=3,
        )

    def _handle_access_denied_error(self, process_name, process_id):
        """Handle the case when access is denied to a process."""
        error_msg = f"Access denied to {process_name} (PID: {process_id})"
        if self.log_file:
            self.log(f"Error: {error_msg}")
        self.notify(
            f"🔒 {error_msg}. Try running with elevated privileges.",
            severity="error",
            timeout=5,
        )

    def _handle_zombie_process_error(self, process_name, process_id):
        """Handle the case when a process is a zombie."""
        error_msg = f"Process {process_name} (PID: {process_id}) is a zombie process"
        if self.log_file:
            self.log(f"Warning: {error_msg}")
        self.notify(
            f"🧟 {error_msg}",
            severity="warning",
            timeout=4,
        )

    def _handle_general_process_error(self, action, process_name, error):
        """Handle general process action errors."""
        error_msg = f"Error {action}ing process {process_name}: {str(error)}"
        if self.log_file:
            self.log(f"Exception: {error_msg}")
        self.notify(
            f"❌ {error_msg}",
            severity="error",
            timeout=5,
        )


def _show_styled_version():
    """Display a clean and focused version information."""
    console = Console()

    title_text = Text()
    title_text.append("      ▄▀▀  ▄▀▀▄  ▀█▀      \n", style="bold bright_yellow")
    title_text.append("      ▀▀▄  █  █   █       \n", style="bold bright_yellow")
    title_text.append("      ▄▄▀  ▀▄▄▀   █       \n", style="bold bright_yellow")
    title_text.append("\n")
    title_text.append("System Observation Tool", style="bold bright_cyan")

    version_table = Table(show_header=False, box=None, padding=(0, 1))
    version_table.add_column("Label", style="dim", width=12)
    version_table.add_column("Value", style="bold")

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

    version_table.add_row("Version:", f"[bright_green]{__version__}[/]")
    version_table.add_row("Python:", f"[bright_blue]{python_version}[/]")
    version_table.add_row("Platform:", f"[bright_magenta]{system_info}[/]")
    version_table.add_row("Architecture:", f"[bright_yellow]{platform.machine()}[/]")

    main_panel = Panel(
        title_text,
        title="[bold bright_white]System Observation Tool[/]",
        title_align="center",
        border_style="bright_cyan",
        padding=(1, 2),
    )

    info_panel = Panel(
        version_table,
        title="[bold]📋 Version Information[/]",
        border_style="bright_green",
        padding=(1, 2),
    )

    console.print(main_panel)
    console.print()
    console.print(info_panel)
    console.print()

    # Footer with copyright and links
    footer_text = Text()
    footer_text.append("MIT License © 2024-", style="dim")
    footer_text.append(f"{__current_year__}", style="dim")
    footer_text.append(" Kumar Anirudha\n", style="dim")
    footer_text.append("🔗 ", style="bright_blue")
    footer_text.append(
        "https://github.com/anistark/sot", style="link https://github.com/anistark/sot"
    )
    footer_text.append(" | 📖 ", style="bright_green")
    footer_text.append("sot --help", style="bold bright_white")
    footer_text.append(" | 🚀 ", style="bright_yellow")
    footer_text.append("sot", style="bold bright_cyan")

    console.print(Panel(footer_text, border_style="dim", padding=(0, 2)))


def run(argv=None):
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

    # Create subparsers for subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="{info,bench}",
    )

    # Add info subcommand
    info_parser = subparsers.add_parser(
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

    args = parser.parse_args(argv)

    # Handle info subcommand
    if args.command == "info":
        from .info.cli import info_command

        return info_command(args)

    # Handle bench subcommand
    if args.command == "bench":
        from .bench.cli import benchmark_command

        return benchmark_command(args)

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

    # Set up logging before using SotApp (Textual reads TEXTUAL_LOG at module import time)
    if args.log:
        os.environ["TEXTUAL_LOG"] = args.log
        # Reload textual.constants to pick up the new TEXTUAL_LOG value
        import importlib

        import textual.constants

        importlib.reload(textual.constants)
        print(f"🐛 Debug logging enabled: {args.log}")

    # Create and run the application with the specified options
    app = SotApp(net_interface=args.net, log_file=args.log)

    if args.net:
        print(f"📡 Using network interface: {args.net}")

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
