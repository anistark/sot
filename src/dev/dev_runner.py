#!/usr/bin/env python3
"""
Development runner for SOT with hot reloading.
Usage: python src/dev/dev_runner.py [--debug] [--log LOG_FILE]
"""

import argparse
import sys
from pathlib import Path

# Add src to path so we can import sot
sys.path.insert(0, str(Path(__file__).parent.parent))

from textual.app import App, ComposeResult
from textual.widgets import Header

from sot._cpu import CPU
from sot._disk import Disk
from sot._info import InfoLine
from sot._mem import Mem
from sot._net import Net
from sot._procs_list import ProcsList


class SotDevelopmentApp(App):
    """Development version of SOT with enhanced debugging and performance optimizations."""
    
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

    def __init__(self, network_interface_name=None, **kwargs):
        super().__init__(**kwargs)
        self.network_interface_name = network_interface_name

    def compose(self) -> ComposeResult:
        yield Header()
        yield InfoLine(id="info-line")
        yield CPU()
        yield ProcsList(id="procs-list")
        yield Mem()
        yield Disk()
        yield Net(self.network_interface_name)

    def on_mount(self) -> None:
        self.title = "SOT (Development Mode)"
        self.sub_title = "System Observation Tool - DEV"
        
        # Performance optimization: reduce refresh frequency during startup
        self.refresh_rate = 30  # 30 FPS instead of default 60

    def action_toggle_dark(self) -> None:
        """Toggle between dark and light themes."""
        current_theme = getattr(self, 'theme', 'textual-dark')
        new_theme = "textual-light" if current_theme == "textual-dark" else "textual-dark"
        self.theme = new_theme
        self.notify(f"Switched to {new_theme.replace('textual-', '')} mode")

    def action_screenshot(self) -> None:
        """Take a screenshot and save to file."""
        screenshot_path = self.save_screenshot()
        self.notify(f"Screenshot saved to {screenshot_path}")

    def action_quit(self) -> None:
        """Quit the application gracefully."""
        self.exit()

    def on_procs_list_process_selected(self, message: ProcsList.ProcessSelected) -> None:
        """Handle process selection."""
        process_info = message.process_info
        process_name = process_info.get("name", "Unknown")
        process_id = process_info.get("pid", "N/A")
        self.notify(f"Selected: {process_name} (PID: {process_id})")

    def on_procs_list_process_action(self, message: ProcsList.ProcessAction) -> None:
        """Handle process actions like kill/terminate."""
        import psutil
        
        action = message.action
        process_info = message.process_info
        process_id = process_info.get("pid")
        process_name = process_info.get("name", "Unknown")
        
        if not process_id:
            self.notify("❌ Invalid process ID", severity="error")
            return
            
        try:
            target_process = psutil.Process(process_id)
            
            if action == "kill":
                target_process.kill()
                self.notify(f"💥 Killed {process_name} (PID: {process_id})", severity="warning")
            elif action == "terminate":
                target_process.terminate()
                self.notify(f"🛑 Terminated {process_name} (PID: {process_id})", severity="information")
            else:
                self.notify(f"❓ Unknown action: {action}", severity="error")
                
        except psutil.NoSuchProcess:
            self.notify(f"❌ Process {process_id} no longer exists", severity="error")
        except psutil.AccessDenied:
            self.notify(f"🔒 Access denied to {process_name} (PID: {process_id})", severity="error")
        except Exception as error:
            self.notify(f"❌ Error {action}ing process: {error}", severity="error")


def main():
    argument_parser = argparse.ArgumentParser(description="SOT Development Runner")
    argument_parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode with extra logging"
    )
    argument_parser.add_argument(
        "--log", 
        type=str, 
        help="Log file path for debugging"
    )
    argument_parser.add_argument(
        "--net", 
        type=str, 
        help="Network interface to monitor"
    )
    argument_parser.add_argument(
        "--css-hot-reload",
        action="store_true",
        help="Enable CSS hot reloading (watches .tcss files)"
    )
    argument_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colors for compatibility"
    )
    
    parsed_arguments = argument_parser.parse_args()
    
    # Set environment variables for better compatibility
    import os
    if parsed_arguments.no_color:
        os.environ['NO_COLOR'] = '1'
    
    # Force UTF-8 encoding
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Textual performance settings
    os.environ['TEXTUAL_DRIVER'] = 'auto'  # Let Textual choose best driver
    
    # Configure the app
    app_configuration = {}
    if parsed_arguments.css_hot_reload:
        app_configuration['watch_css'] = True
    
    sot_development_app = SotDevelopmentApp(
        network_interface_name=parsed_arguments.net, 
        **app_configuration
    )
    
    # Add development key bindings
    sot_development_app.bind("d", "toggle_dark")
    sot_development_app.bind("s", "screenshot")
    sot_development_app.bind("q", "quit")
    sot_development_app.bind("ctrl+c", "quit")
    
    # Run with appropriate logging
    try:
        if parsed_arguments.log:
            # Textual 3.4.0+: Use TEXTUAL_LOG environment variable instead
            os.environ['TEXTUAL_LOG'] = parsed_arguments.log
        elif parsed_arguments.debug:
            os.environ['TEXTUAL_LOG'] = "sot_debug.log"
        
        sot_development_app.run()
    except KeyboardInterrupt:
        print("\nExiting SOT development mode...")
        sys.exit(0)


if __name__ == "__main__":
    main()
