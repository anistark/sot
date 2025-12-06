#!/usr/bin/env python3
"""Build script to generate man page for sot using argparse-manpage."""

import argparse
import sys
from pathlib import Path


def build_manpage():
    """Generate the sot man page."""
    # Add the src directory to the path so we can import sot
    src_dir = Path(__file__).parent.parent / "src"
    sys.path.insert(0, str(src_dir))

    from argparse_manpage.manpage import Manpage

    # Get the parser by creating a custom version that doesn't execute
    parser = argparse.ArgumentParser(
        prog="sot",
        description="Command-line System Observation Tool ≈",
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

    # Create subparsers for subcommands
    subparsers = parser.add_subparsers(dest="command", metavar="{info,bench,disk}")

    # Add info subcommand
    subparsers.add_parser(
        "info",
        help="Display system information",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Add bench subcommand
    bench_parser = subparsers.add_parser(
        "bench",
        help="Disk benchmarking",
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
        "--duration",
        "-d",
        type=float,
        default=10.0,
        help="Duration for each benchmark test in seconds (default: 10s)",
    )

    # Add disk subcommand
    subparsers.add_parser(
        "disk",
        help="Interactive disk information viewer",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Get version
    from sot.__about__ import __current_year__, __version__

    # Create the man page
    manpage = Manpage(parser)

    # Set manual metadata
    manpage.prog = "sot"
    manpage.description = (
        "sot is a Command-line System Observation Tool in the spirit of top. "
        "It displays various interesting system stats and graphs them. Works on all operating systems."
    )
    manpage.long_description = (
        "sot provides real-time monitoring of system resources including CPU usage, "
        "memory, disk I/O, and network statistics. It features an interactive TUI "
        "(Terminal User Interface) for monitoring processes and system performance.\n\n"
        "When run without arguments, sot launches the interactive monitoring interface. "
        "Additional subcommands are available for specific tasks:\n\n"
        "  info   - Display detailed system information with OS-specific ASCII logo\n"
        "  bench  - Run comprehensive disk benchmarking tests\n"
        "  disk   - Launch interactive disk information viewer"
    )
    manpage.project = "sot"
    manpage.version = __version__
    manpage.manual_section = 1
    manpage.manual_title = "User Commands"
    manpage.author = "Kumar Anirudha <sot@anirudha.dev>"
    manpage.date = f"2024-{__current_year__}"

    # Generate the man page content
    man_content = str(manpage)

    # Add additional sections manually
    additional_sections = f"""
.SH EXAMPLES
.TP
.B sot
Launch the interactive system monitoring TUI
.TP
.B sot --net eth0
Monitor system with specific network interface
.TP
.B sot info
Display comprehensive system information
.TP
.B sot bench
Run interactive disk benchmark
.TP
.B sot bench --duration 30 --output results.json
Run 30-second benchmarks and save results to JSON
.TP
.B sot disk
View interactive disk information

.SH FEATURES
.SS System Monitoring
.IP \\(bu 2
CPU usage per core and thread
.IP \\(bu 2
Process management with interactive sorting
.IP \\(bu 2
Memory usage and capacity monitoring
.IP \\(bu 2
Network upload/download speed and bandwidth
.IP \\(bu 2
Disk I/O statistics and usage

.SS System Information (sot info)
.IP \\(bu 2
Hardware details (chip, GPU, memory)
.IP \\(bu 2
Software information (OS, kernel, shell)
.IP \\(bu 2
Display configuration and brightness
.IP \\(bu 2
Battery status and system uptime
.IP \\(bu 2
OS-specific ASCII logos

.SS Disk Benchmarking (sot bench)
.IP \\(bu 2
Sequential read/write throughput
.IP \\(bu 2
Random read/write IOPS
.IP \\(bu 2
Latency percentiles (p50, p95, p99)
.IP \\(bu 2
JSON export for results

.SH INTERACTIVE CONTROLS
When running the main sot interface:
.TP
.B q
Quit the application
.TP
.B O
Enter order-by mode for process sorting
.TP
.B Arrow keys
Navigate columns in order-by mode
.TP
.B Enter
Toggle sort direction (DESC ↓ → ASC ↑ → OFF)

.SH CONFIGURATION
sot does not require configuration files. All options are provided via command-line arguments.

.SH EXIT STATUS
.TP
.B 0
Success
.TP
.B 1
General error (insufficient permissions, invalid arguments, etc.)

.SH SEE ALSO
.BR top (1),
.BR htop (1),
.BR btop (1),
.BR iostat (1),
.BR vmstat (8)

.SH BUGS
Report bugs at: https://github.com/anistark/sot/issues

.SH COPYRIGHT
MIT License © 2024-{__current_year__} Kumar Anirudha

.SH AUTHOR
Written by Kumar Anirudha.

.SH AVAILABILITY
The latest version is available at: https://github.com/anistark/sot
"""

    # Insert additional sections before the final .SH section (which is usually AUTHORS)
    # We'll append them to the end
    full_content = man_content.rstrip() + additional_sections

    return full_content


if __name__ == "__main__":
    try:
        content = build_manpage()
        # Output directory for man pages
        output_dir = Path(__file__).parent.parent / "man"
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / "sot.1"
        with open(output_file, "w") as f:
            f.write(content)

        print(f"✓ Man page generated: {output_file}")
        sys.exit(0)
    except Exception as e:
        print(f"✗ Error generating man page: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
