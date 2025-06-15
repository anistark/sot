#!/usr/bin/env python3
"""
Terminal performance diagnostics for SOT.
Run this to check if your terminal supports optimal Textual rendering.
"""

import os
import sys
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

def check_terminal_rendering_capabilities():
    """Check terminal capabilities that affect Textual rendering performance."""
    terminal_console = Console()
    
    capabilities_info_table = Table(title="🔍 Terminal Diagnostics")
    capabilities_info_table.add_column("Property", style="cyan")
    capabilities_info_table.add_column("Value", style="green")
    capabilities_info_table.add_column("Status", style="yellow")
    
    # Basic terminal information
    capabilities_info_table.add_row("Terminal Type", os.environ.get('TERM', 'unknown'), "")
    capabilities_info_table.add_row("Terminal Program", os.environ.get('TERM_PROGRAM', 'unknown'), "")
    capabilities_info_table.add_row("Color Terminal", os.environ.get('COLORTERM', 'not set'), "")
    
    # Textual-specific environment variables
    capabilities_info_table.add_row("Textual Driver", os.environ.get('TEXTUAL_DRIVER', 'auto'), "")
    capabilities_info_table.add_row("No Color Flag", os.environ.get('NO_COLOR', 'not set'), "")
    capabilities_info_table.add_row("Force Color Flag", os.environ.get('FORCE_COLOR', 'not set'), "")
    
    # Rich console capabilities
    capabilities_info_table.add_row("Color System", str(terminal_console.color_system), "")
    capabilities_info_table.add_row("Is Terminal", str(terminal_console.is_terminal), "")
    capabilities_info_table.add_row("Legacy Windows", str(terminal_console.legacy_windows), "")
    capabilities_info_table.add_row("Terminal Size", f"{terminal_console.size.width}x{terminal_console.size.height}", "")
    
    terminal_console.print(capabilities_info_table)
    terminal_console.print()
    
    # Generate performance recommendations
    performance_recommendations = []
    
    if terminal_console.color_system == "standard":
        performance_recommendations.append("⚠️  Limited color support - try a modern terminal")
    
    if not terminal_console.is_terminal:
        performance_recommendations.append("❌ Not running in a terminal")
        
    if terminal_console.legacy_windows:
        performance_recommendations.append("⚠️  Legacy Windows terminal - consider Windows Terminal")
        
    if os.environ.get('TERM') == 'screen':
        performance_recommendations.append("⚠️  Screen/tmux detected - may cause refresh issues")
        
    if not os.environ.get('COLORTERM'):
        performance_recommendations.append("💡 Set COLORTERM=truecolor for better colors")
    
    # Terminal-specific optimization suggestions
    terminal_program_name = os.environ.get('TERM_PROGRAM', '')
    if terminal_program_name == 'iTerm.app':
        performance_recommendations.append("✅ iTerm2 detected - should work well")
    elif terminal_program_name == 'Apple_Terminal':
        performance_recommendations.append("⚠️  Apple Terminal - try iTerm2 for better performance")
    elif 'kitty' in os.environ.get('TERM', ''):
        performance_recommendations.append("✅ Kitty terminal - excellent Textual support")
    elif 'alacritty' in os.environ.get('TERM', ''):
        performance_recommendations.append("✅ Alacritty - good performance")
    
    if performance_recommendations:
        terminal_console.print(Panel("\n".join(performance_recommendations), title="🔧 Recommendations"))
    else:
        terminal_console.print(Panel("✅ Terminal looks good for Textual!", title="🎉 Status"))

def run_terminal_performance_test():
    """Run a simple performance test to measure terminal rendering speed."""
    terminal_console = Console()
    
    terminal_console.print("\n🏃 Running performance test...")
    
    # Test terminal refresh rate capability
    test_start_time = time.time()
    total_test_frames = 100
    target_frame_delay = 0.01  # 100 FPS target
    
    for frame_number in range(total_test_frames):
        terminal_console.clear()
        terminal_console.print(f"Frame {frame_number + 1}/{total_test_frames}")
        time.sleep(target_frame_delay)
    
    test_end_time = time.time()
    actual_test_duration = test_end_time - test_start_time
    expected_test_duration = total_test_frames * target_frame_delay
    
    terminal_console.clear()
    terminal_console.print(f"⏱️  Performance: {actual_test_duration:.2f}s (expected ~{expected_test_duration:.2f}s)")
    
    if actual_test_duration > expected_test_duration * 2:
        terminal_console.print("❌ Slow rendering detected - terminal may have performance issues")
        return False
    elif actual_test_duration > expected_test_duration * 1.5:
        terminal_console.print("⚠️  Moderate rendering speed - consider terminal optimizations")
        return True
    else:
        terminal_console.print("✅ Good rendering performance")
        return True

def main():
    terminal_console = Console()
    terminal_console.print(Panel("🔍 SOT Terminal Diagnostics", style="bold blue"))
    
    check_terminal_rendering_capabilities()
    
    terminal_console.print("\nPress Enter to run performance test (or Ctrl+C to skip)...")
    try:
        input()
        has_good_performance = run_terminal_performance_test()
        
        terminal_console.print("\n🎯 Recommendations for SOT:")
        if has_good_performance:
            terminal_console.print("✅ Your terminal should work well with SOT")
            terminal_console.print("💡 Try: just dev")
        else:
            terminal_console.print("⚠️  Try these for better performance:")
            terminal_console.print("   • just dev-fast (reduced colors)")
            terminal_console.print("   • Use a modern terminal (iTerm2, Kitty, Alacritty)")
            terminal_console.print("   • Set TEXTUAL_DRIVER=auto")
            
    except KeyboardInterrupt:
        terminal_console.print("\n⏭️  Skipping performance test")
        
    terminal_console.print("\n🚀 Ready to run SOT! Try: just dev")

if __name__ == "__main__":
    main()
