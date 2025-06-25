from __future__ import annotations

import argparse
from sys import version_info

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

    def __init__(self, net_interface=None):
        super().__init__()
        self.net_interface = net_interface

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

        net_widget = NetworkWidget(self.net_interface)
        net_widget.id = "net-widget"
        yield net_widget

    def on_mount(self) -> None:
        self.title = "SOT"
        self.sub_title = "System Observation Tool"
        # Set initial focus to the process list for interactive features
        self.set_focus(self.query_one("#procs-list"))

    async def on_load(self, _):
        self.bind("q", "quit")

    def on_processes_widget_process_selected(
        self, message: ProcessesWidget.ProcessSelected
    ) -> None:
        """Handle process selection from the process list."""
        process_info = message.process_info
        process_name = process_info.get("name", "Unknown")
        process_id = process_info.get("pid", "N/A")
        cpu_percent = process_info.get("cpu_percent", 0) or 0

        # Show detailed process information
        memory_info = process_info.get("memory_info")
        memory_str = ""
        if memory_info:
            from ._helpers import sizeof_fmt

            memory_str = f" | Memory: {sizeof_fmt(memory_info.rss, suffix='', sep='')}"

        self.notify(
            f"📋 {process_name} (PID: {process_id}) | CPU: {cpu_percent:.1f}%{memory_str}",
            timeout=3,
        )

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

        try:
            target_process = psutil.Process(process_id)

            if action == "kill":
                target_process.kill()
                self.notify(
                    f"💥 Killed {process_name} (PID: {process_id})",
                    severity="warning",
                    timeout=4,
                )
            elif action == "terminate":
                target_process.terminate()
                self.notify(
                    f"🛑 Terminated {process_name} (PID: {process_id})",
                    severity="information",
                    timeout=4,
                )
            else:
                self.notify(f"❓ Unknown action: {action}", severity="error", timeout=3)

        except psutil.NoSuchProcess:
            self.notify(
                f"❌ Process {process_id} no longer exists",
                severity="error",
                timeout=3,
            )
        except psutil.AccessDenied:
            self.notify(
                f"🔒 Access denied to {process_name} (PID: {process_id}). Try running with elevated privileges.",
                severity="error",
                timeout=5,
            )
        except psutil.ZombieProcess:
            self.notify(
                f"🧟 Process {process_name} (PID: {process_id}) is a zombie process",
                severity="warning",
                timeout=4,
            )
        except Exception as error:
            self.notify(
                f"❌ Error {action}ing process {process_name}: {str(error)}",
                severity="error",
                timeout=5,
            )


def run(argv=None):
    parser = argparse.ArgumentParser(
        description="Command-line System Obervation Tool ≈",
        formatter_class=argparse.RawTextHelpFormatter,
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
        action="version",
        version=_get_version_text(),
        help="Display version information",
    )

    parser.add_argument(
        "--log",
        "-L",
        type=str,
        default=None,
        help="Debug log file",
    )

    parser.add_argument(
        "--net",
        "-N",
        type=str,
        default=None,
        help="Network interface to display (default: auto)",
    )

    args = parser.parse_args(argv)

    # Configure logging and run the application
    if args.log:
        import os

        os.environ["TEXTUAL_LOG"] = args.log
        app = SotApp(net_interface=args.net)
        app.run()
    else:
        app = SotApp(net_interface=args.net)
        app.run()


def _get_version_text():
    """Generate version information string."""
    python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

    return "\n".join(
        [
            f"sot {__version__} [Python {python_version}]",
            f"MIT License © 2024-{__current_year__} Kumar Anirudha",
        ]
    )
