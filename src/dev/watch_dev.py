#!/usr/bin/env python3
"""
File watcher that automatically restarts SOT when source files change.
Requires: pip install watchdog
Usage: python src/dev/watch_dev.py
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("❌ watchdog not installed. Install with: pip install watchdog")
    sys.exit(1)


class SotSourceFileHandler(FileSystemEventHandler):
    """Handles file system events for SOT development with meaningful naming."""
    
    def __init__(self, restart_application_callback):
        self.restart_application_callback = restart_application_callback
        self.last_restart_timestamp = 0
        self.debounce_delay_seconds = 1.0  # seconds
        
    def should_trigger_restart(self, file_event_path):
        """Check if the file change should trigger an application restart."""
        file_path = Path(file_event_path)
        
        # Only watch Python files in the src directory
        if not file_path.suffix == '.py':
            return False
            
        # Skip __pycache__ and other generated files
        if '__pycache__' in file_path.parts:
            return False
            
        # Skip hidden files and directories
        if any(path_part.startswith('.') for path_part in file_path.parts):
            return False
            
        # Skip dev files to avoid infinite restart loops
        if 'dev' in file_path.parts:
            return False
            
        return True
    
    def on_modified(self, file_system_event):
        if file_system_event.is_directory:
            return
            
        if not self.should_trigger_restart(file_system_event.src_path):
            return

        current_timestamp = time.time()
        if current_timestamp - self.last_restart_timestamp < self.debounce_delay_seconds:
            return
            
        self.last_restart_timestamp = current_timestamp
        print(f"🔄 File changed: {file_system_event.src_path}")
        self.restart_application_callback()


class SotDevelopmentProcessManager:
    """Manages the SOT development process with auto-restart and proper signal handling."""
    
    def __init__(self):
        self.sot_application_process = None
        self.file_system_observer = None
        self.source_code_path = Path(__file__).parent.parent / "sot"
        self.should_exit_flag = False

        signal.signal(signal.SIGINT, self.handle_interrupt_signal)
        signal.signal(signal.SIGTERM, self.handle_terminate_signal)
        
    def handle_interrupt_signal(self, signal_number, frame):
        """Handle SIGINT (Ctrl+C) for clean shutdown."""
        print("\n🛑 Interrupt signal received, shutting down...")
        self.should_exit_flag = True

        if self.sot_application_process and self.sot_application_process.poll() is None:
            self.sot_application_process.terminate()
        
    def handle_terminate_signal(self, signal_number, frame):
        """Handle SIGTERM for clean shutdown."""
        print("\n🛑 Terminate signal received, shutting down...")
        self.should_exit_flag = True

        if self.sot_application_process and self.sot_application_process.poll() is None:
            self.sot_application_process.terminate()
        
    def start_sot_application(self):
        """Start the SOT application process."""
        if self.sot_application_process and self.sot_application_process.poll() is None:
            print("🛑 Stopping previous SOT instance...")
            self.terminate_sot_application()
        
        print("🚀 Starting SOT application...")

        self.sot_application_process = subprocess.Popen([
            sys.executable, 
            str(Path(__file__).parent / "dev_runner.py"),
            "--debug"
        ], preexec_fn=None)
        
    def terminate_sot_application(self):
        """Terminate the SOT application gracefully."""
        if not self.sot_application_process:
            return
            
        print("🔄 Terminating SOT process...")
        self.sot_application_process.terminate()
        
        try:
            self.sot_application_process.wait(timeout=5)
            print("✅ SOT terminated gracefully")
        except subprocess.TimeoutExpired:
            print("💥 Force killing SOT process...")
            self.sot_application_process.kill()
            self.sot_application_process.wait()
            print("✅ SOT force killed")
            
        self.sot_application_process = None
        
    def restart_sot_application(self):
        """Restart the SOT application due to file changes."""
        print("🔄 Restarting SOT due to file changes...")
        self.start_sot_application()
        
    def check_sot_application_status(self):
        """Check if SOT application process is still running."""
        if not self.sot_application_process:
            return True

        process_has_ended = self.sot_application_process.poll() is not None
        
        if process_has_ended:
            exit_code = self.sot_application_process.returncode
            if exit_code == 0:
                print("✅ SOT exited normally (user quit)")
                self.should_exit_flag = True
            else:
                print(f"⚠️  SOT exited with code {exit_code}")
        
        return process_has_ended
        
    def start_file_system_watching(self):
        """Start watching for file changes."""
        if not self.source_code_path.exists():
            print(f"❌ Source path not found: {self.source_code_path}")
            return
            
        file_change_handler = SotSourceFileHandler(self.restart_sot_application)
        self.file_system_observer = Observer()
        self.file_system_observer.schedule(
            file_change_handler, 
            str(self.source_code_path), 
            recursive=True
        )
        self.file_system_observer.start()
        
        print(f"👀 Watching for changes in: {self.source_code_path}")
        print("📝 Edit any .py file to see SOT restart automatically")
        print("🔑 Press Ctrl+C to stop both watcher and SOT immediately")
        print("🚪 Or press 'q' in SOT to quit SOT (watcher will detect and exit)")
        
    def cleanup_resources(self):
        """Clean up all resources before exit."""
        if self.file_system_observer:
            print("🛑 Stopping file system observer...")
            self.file_system_observer.stop()
            self.file_system_observer.join()
            
        if self.sot_application_process and self.sot_application_process.poll() is None:
            self.terminate_sot_application()
        
    def run_development_environment(self):
        """Run the complete development environment with file watching."""
        try:
            self.start_sot_application()
            self.start_file_system_watching()

            while not self.should_exit_flag:
                time.sleep(0.5)
                
                if self.check_sot_application_status():
                    if not self.should_exit_flag:
                        print("💀 SOT process ended unexpectedly, restarting...")
                        self.start_sot_application()
                    else:
                        print("✅ SOT process ended, exiting watcher...")
                        break
                        
        except KeyboardInterrupt:
            # Handle Ctrl+C
            print("\n🛑 KeyboardInterrupt caught, shutting down...")
            self.should_exit_flag = True
            
        except Exception as error:
            print(f"❌ Unexpected error in development environment: {error}")
            
        finally:
            self.cleanup_resources()


def main():
    print("🔧 SOT Development File Watcher")
    print("===============================")
    
    development_manager = SotDevelopmentProcessManager()
    development_manager.run_development_environment()
    
    print("👋 Development environment shut down")


if __name__ == "__main__":
    main()
