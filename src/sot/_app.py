from __future__ import annotations

import argparse
from sys import version_info

from textual.app import App

from .__about__ import __version__, __current_year__
from ._cpu import CPU
from ._disk import Disk
from ._info import InfoLine
from ._mem import Mem
from ._net import Net
from ._procs_list import ProcsList
# from ._sot import Sot

def run(argv=None):
    parser = argparse.ArgumentParser(
        description="Command-line System Obervation Tool ≈",
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False
    )

    parser.add_argument(
        "--help",
        "-H",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit."
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
    class sotApp(App):
        async def on_mount(self) -> None:
            grid = await self.view.dock_grid(edge="left")

            grid.add_column(fraction=36, name="left")
            # grid.add_column(fraction=15, name="middle")
            # grid.add_column(fraction=36, name="right")
            grid.add_column(fraction=45, name="right")

            grid.add_row(size=1, name="r0")
            grid.add_row(fraction=1, name="r1")
            grid.add_row(fraction=1, name="r2")
            grid.add_row(fraction=1, name="r3")
            grid.add_areas(
                area0="left-start|right-end,r0",
                area1="left,r1",
                # area2a="middle,r1-start|r1-end",
                # area2b="middle,r2-start|r2-end",
                # area2c="middle,r3-start|r3-end",
                area3a="right,r1",
                area3b="right,r2",
                area3c="right,r3",
                area4="left,r2-start|r3-end",
            )
            grid.place(
                area0=InfoLine(),
                area1=CPU(),
                # area2b=Sot(),
                area3a=Mem(),
                area3b=Disk(),
                area3c=Net(args.net),
                area4=ProcsList(),
            )

        async def on_load(self, _):
            await self.bind("q", "quit", "quit")

    sotApp.run(log=args.log)


def _get_version_text():
    python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

    return "\n".join(
        [
            f"sot {__version__} [Python {python_version}]",
            f"Copyright (c) 2024-{__current_year__} Kumar Anirudha",
        ]
    )
