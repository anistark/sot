"""Command-line interface for ps TUI."""

from rich.console import Console

from .ps_tui import ProcessTUIApp

console = Console()


def ps_command(args) -> int:
    """Launch the process TUI application."""
    try:
        app = ProcessTUIApp()
        app.run()
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Process viewer terminated by user[/]")
        return 0
    except Exception as e:
        console.print(f"[red]Error launching process viewer: {e}[/]")
        return 1
