from __future__ import annotations

import argparse
import os
import platform
import sys
from sys import version_info

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .__about__ import __current_year__, __version__
from ._config import (
    EXAMPLE,
    apply_refresh,
    config_path,
    load_config,
    remembered_theme,
)
from ._theme import DEFAULT_THEME, THEMES, set_theme, theme
from .tui.app import SotApp

__all__ = ["SotApp", "run"]


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


def _print_keys() -> int:
    from .tui.keymap import all_bindings

    c = theme().colors
    table = Table(header_style=f"bold {c.accent}", box=theme().design.app_box)
    table.add_column("Id", style=c.label)
    table.add_column("Keys", style=c.primary)
    table.add_column("Action")
    for binding_id, binding in all_bindings().items():
        table.add_row(binding_id, binding.key, binding.description)
    Console().print(table)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sot",
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
        "--config-path",
        action="store_true",
        help="Print where sot reads its config file from",
    )

    parser.add_argument(
        "--keys",
        action="store_true",
        help="List every key binding id, for the [keymap] config table",
    )

    parser.add_argument(
        "--theme",
        "-T",
        choices=list(THEMES),
        metavar="THEME",
        default=None,
        help=f"Color theme: {', '.join(THEMES)} (default: $SOT_THEME, config, or classic)",
    )
    # Create subparsers for subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="{info,bench,disk,clean,ps}",
    )

    # Add info subcommand
    subparsers.add_parser(
        "info",
        help="Print system information (the System view is key 4)",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Add bench subcommand
    bench_parser = subparsers.add_parser(
        "bench",
        help="Disk benchmarking view; flags run it without the TUI",
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
        "--disk",
        dest="bench_disk",
        metavar="DISK",
        type=str,
        default=None,
        help="Disk to benchmark, by id (disk3, /dev/sda) or mountpoint; skips the prompt",
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
        help="Disks view; --list prints a table instead",
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
        help="Clean caches, logs and temp files; --dry-run only reports",
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
        help="Processes view: processes, listening ports, dev environments",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    return parser


def run(argv=None):  # noqa: C901
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.config_path:
        path = config_path()
        print(path if path.exists() else f"{path} (not created yet)\n\n{EXAMPLE}")
        return 0

    config = load_config()
    for warning in config.warnings:
        print(f"⚠️  {warning}", file=sys.stderr)
    apply_refresh(config)

    env_theme = os.environ.get("SOT_THEME")
    args.theme = (
        args.theme or env_theme or config.theme or remembered_theme() or DEFAULT_THEME
    )
    if args.theme not in THEMES:
        print(f"❌ Unknown theme '{args.theme}'. Available: {', '.join(THEMES)}")
        return 1
    set_theme(args.theme)
    args.net = args.net or config.net
    args.disk = args.disk or config.disk

    if args.keys:
        return _print_keys()

    # Handle info subcommand
    if args.command == "info":
        from .info.cli import info_command

        return info_command(args)

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    start_mode = config.default_view or "overview"

    # bench and clean open their view in a terminal; flags keep the printed flow.
    if args.command == "bench":
        if args.output or args.bench_disk or not interactive:
            from .bench.cli import benchmark_command

            return benchmark_command(args)
        start_mode = "bench"

    # Handle disk subcommand
    if args.command == "disk":
        if args.list:
            from .disk.listing import print_disk_list

            return print_disk_list()
        start_mode = "disks"

    if args.command == "clean":
        if args.dry_run or not interactive:
            from .clean.cli import clean_command

            return clean_command(args)
        start_mode = "clean"

    if args.command == "ps":
        start_mode = "processes"

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

    # A missing or unknown --disk opens a picker inside the app.
    pick_disk = False
    if args.disk:
        import psutil

        mountpoints = [p.mountpoint for p in psutil.disk_partitions()]
        if args.disk == "__select__" or args.disk not in mountpoints:
            if args.disk != "__select__":
                print(f"❌ Disk mountpoint '{args.disk}' not found.")
            pick_disk = True
            args.disk = None

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
        start_mode=start_mode,
        net_interface=args.net,
        disk_mountpoint=args.disk,
        log_file=args.log,
        theme_name=args.theme,
        pick_disk=pick_disk,
        keymap=config.keymap,
        bench_duration=getattr(args, "duration", 10.0),
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
