#!/usr/bin/env python3
"""
Development runner for SOT with hot reloading.
Usage: python src/dev/dev_runner.py [--debug] [--log LOG_FILE]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sot._app import run, _get_version_text  # noqa: E402
from sot._app import SotApp  # noqa: E402


class SotDevelopmentApp(SotApp):
    """Development version of SOT with enhanced debugging and performance optimizations."""

    def on_mount(self) -> None:
        super().on_mount()
        
        self.title = "SOT (Development Mode)"
        self.sub_title = "System Observation Tool - DEV"

        self.refresh_rate = 30  # 30 FPS for dev

    def action_toggle_dark(self) -> None:
        """Toggle between dark and light themes."""
        current_theme = getattr(self, "theme", "textual-dark")
        new_theme = (
            "textual-light" if current_theme == "textual-dark" else "textual-dark"
        )
        self.theme = new_theme
        self.notify(f"Switched to {new_theme.replace('textual-', '')} mode")

    def action_screenshot(self) -> None:
        """Take a screenshot and save to file."""
        screenshot_path = self.save_screenshot()
        self.notify(f"Screenshot saved to {screenshot_path}")

    def action_quit(self) -> None:
        """Quit the application gracefully."""
        self.exit()


def main():
    argument_parser = argparse.ArgumentParser(description="SOT Development Runner")
    argument_parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode with extra logging"
    )
    argument_parser.add_argument("--log", type=str, help="Log file path for debugging")
    argument_parser.add_argument("--net", type=str, help="Network interface to monitor")
    argument_parser.add_argument(
        "--css-hot-reload",
        action="store_true",
        help="Enable CSS hot reloading (watches .tcss files)",
    )
    argument_parser.add_argument(
        "--no-color", action="store_true", help="Disable colors for compatibility"
    )

    parsed_arguments = argument_parser.parse_args()

    import os

    if parsed_arguments.no_color:
        os.environ["NO_COLOR"] = "1"

    # UTF-8 encoding
    os.environ["PYTHONIOENCODING"] = "utf-8"

    os.environ["TEXTUAL_DRIVER"] = "auto"  # Let Textual choose best driver

    app_configuration = {}
    if parsed_arguments.css_hot_reload:
        app_configuration["watch_css"] = True

    sot_development_app = SotDevelopmentApp(
        net_interface=parsed_arguments.net, **app_configuration
    )

    # dev key bindings
    sot_development_app.bind("d", "toggle_dark")
    sot_development_app.bind("s", "screenshot")
    sot_development_app.bind("q", "quit")
    sot_development_app.bind("ctrl+c", "quit")

    try:
        if parsed_arguments.log:
            os.environ["TEXTUAL_LOG"] = parsed_arguments.log
        elif parsed_arguments.debug:
            os.environ["TEXTUAL_LOG"] = "sot_debug.log"

        sot_development_app.run()
    except KeyboardInterrupt:
        print("\nExiting SOT development mode...")
        sys.exit(0)


if __name__ == "__main__":
    main()
