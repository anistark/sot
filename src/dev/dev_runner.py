#!/usr/bin/env python3
"""
Development runner for SOT with hot reloading.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sot._app import SotApp  # noqa: E402


class SotDevelopmentApp(SotApp):
    """Development version of SOT with enhanced debugging and performance optimizations."""

    def on_mount(self) -> None:
        super().on_mount()

        self.title = "SOT (Development Mode)"

        # Show which interface we're using in the subtitle
        if self.net_interface:
            self.sub_title = (
                f"System Observation Tool - DEV - Net: {self.net_interface}"
            )
        else:
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


def validate_network_interface(interface_name):
    """Validate that the network interface exists."""
    try:
        import psutil

        available_interfaces = list(psutil.net_if_stats().keys())
        return interface_name in available_interfaces, available_interfaces
    except Exception:
        return False, []


def main():
    argument_parser = argparse.ArgumentParser(description="SOT Development Runner")
    argument_parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode with extra logging"
    )
    argument_parser.add_argument("--log", type=str, help="Log file path for debugging")
    argument_parser.add_argument("--net", type=str, help="Network interface to monitor")
    argument_parser.add_argument(
        "--version", "-V", action="store_true", help="Display version information"
    )
    argument_parser.add_argument(
        "--css-hot-reload",
        action="store_true",
        help="Enable CSS hot reloading (watches .tcss files)",
    )
    argument_parser.add_argument(
        "--no-color", action="store_true", help="Disable colors for compatibility"
    )

    parsed_arguments = argument_parser.parse_args()

    # Handle version display
    if parsed_arguments.version:
        from sot._app import _show_styled_version

        print("🛠️  [Development Mode]\n")
        _show_styled_version()
        return 0

    # Validate network interface if specified
    if parsed_arguments.net:
        is_valid, available_interfaces = validate_network_interface(
            parsed_arguments.net
        )
        if not is_valid:
            print(f"❌ Error: Network interface '{parsed_arguments.net}' not found.")
            if available_interfaces:
                print(f"📡 Available interfaces: {', '.join(available_interfaces)}")
                print("💡 Run 'just network-discovery' to see detailed interface info")
            else:
                print("📡 No network interfaces detected or psutil error")
            print("🔧 SOT will fall back to auto-detection if you continue...")
            response = input("Continue anyway? (y/N): ")
            if response.lower() not in ["y", "yes"]:
                return 1

    import os

    if parsed_arguments.no_color:
        os.environ["NO_COLOR"] = "1"

    # UTF-8 encoding
    os.environ["PYTHONIOENCODING"] = "utf-8"

    os.environ["TEXTUAL_DRIVER"] = "auto"  # Let Textual choose best driver

    app_configuration = {}
    if parsed_arguments.css_hot_reload:
        app_configuration["watch_css"] = True

    # Print startup information
    print("🚀 Starting SOT Development Mode")
    if parsed_arguments.net:
        print(f"📡 Network interface: {parsed_arguments.net}")
    if parsed_arguments.log:
        print(f"📋 Logging to: {parsed_arguments.log}")
    if parsed_arguments.debug:
        print("🐛 Debug mode enabled")
    print("🔧 Press 'd' to toggle dark/light mode")
    print("📸 Press 's' to take screenshot")
    print("🚪 Press 'q' or Ctrl+C to quit")
    print()

    sot_development_app = SotDevelopmentApp(
        net_interface=parsed_arguments.net,
        log_file=parsed_arguments.log,
        **app_configuration,
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
        print("\n👋 Exiting SOT development mode...")
        return 0
    except Exception as e:
        print(f"\n💥 SOT development mode crashed: {e}")
        if parsed_arguments.log:
            print(f"📋 Check log file for details: {parsed_arguments.log}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
