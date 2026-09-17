"""Command-line interface for disk TUI."""

from rich.console import Console

from .disk_tui import DiskTUIApp

console = Console()


def disk_command(args) -> int:
    """
    Launch the disk TUI application, or print a static listing with ``--list``.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if getattr(args, "list", False):
        from .listing import print_disk_list

        return print_disk_list(console)

    try:
        app = DiskTUIApp()
        app.run()
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Disk viewer terminated by user[/]")
        return 0
    except Exception as e:
        console.print(f"[red]Error launching disk viewer: {e}[/]")
        return 1
