from __future__ import annotations

import argparse
from sys import version_info

from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Header

from .__about__ import __current_year__, __version__
from ._cpu import CPU
from ._disk import Disk
from ._info import InfoLine
from ._mem import Mem
from ._net import Net
from ._procs_list import ProcsList


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

    # with a grid
    class SotApp(App):
        CSS = """
        Screen {
            layout: grid;
            grid-size: 2;
            grid-columns: 36fr 55fr;
            grid-rows: 1 1fr 1.1fr 0.9fr;
        }

        #info-line {
            column-span: 2;
        }

        #procs-list {
            row-span: 2;
        }
        """

        def compose(self) -> ComposeResult:
            yield Header()
            yield InfoLine(id="info-line")
            yield CPU()
            yield ProcsList(id="procs-list")
            yield Mem()
            yield Disk()
            yield Net(self.net_interface)

        def on_mount(self) -> None:
            self.title = "SOT"
            self.sub_title = "System Observation Tool"

        def __init__(self, net_interface=None):
            super().__init__()
            self.net_interface = net_interface

        async def on_load(self, _):
            self.bind("q", "quit")

    # Update: Changed how logging is configured
    if args.log:
        app = SotApp(net_interface=args.net)
        app.run(log_file=args.log)  # Changed from log= to log_file=
    else:
        app = SotApp(net_interface=args.net)
        app.run()


def _get_version_text():
    python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

    return "\n".join(
        [
            f"sot {__version__} [Python {python_version}]",
            f"MIT License © 2024-{__current_year__} Kumar Anirudha",
        ]
    )
