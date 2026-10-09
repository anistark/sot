#!/usr/bin/env python3
"""Build script to generate man page for sot using argparse-manpage."""

import sys
from pathlib import Path


def build_manpage():
    """Generate the sot man page."""
    # Add the src directory to the path so we can import sot
    src_dir = Path(__file__).parent.parent / "src"
    sys.path.insert(0, str(src_dir))

    from argparse_manpage.manpage import Manpage

    from sot._app import build_parser

    parser = build_parser()

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
    manpage.long_description = (  # type: ignore[attr-defined]
        "sot provides real-time monitoring of system resources including CPU usage, "
        "memory, disk I/O, and network statistics in one interactive TUI with six "
        "views: Overview, Processes, Disks, System, Bench and Clean. Press 1 to 6 or "
        "click the header tabs to switch; each view keeps its state.\n\n"
        "Without a subcommand sot opens the Overview. Subcommands open their view, "
        "or print and exit when given flags or when not run in a terminal:\n\n"
        "  info   - Print system information with an OS-specific ASCII logo\n"
        "  bench  - Bench view; --disk or --output run it without the TUI\n"
        "  disk   - Disks view; --list prints a table\n"
        "  clean  - Clean view; --dry-run prints what would be cleaned\n"
        "  ps     - Processes view with listening ports and dev environments"
    )
    manpage.project = "sot"  # type: ignore[attr-defined]
    manpage.version = __version__  # type: ignore[attr-defined]
    manpage.manual_section = 1  # type: ignore[attr-defined]
    manpage.manual_title = "User Commands"  # type: ignore[attr-defined]
    manpage.author = "Kumar Anirudha <sot@anirudha.dev>"  # type: ignore[attr-defined]
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
.B sot --disk
Pick the disk to monitor from a list
.TP
.B sot --disk /
Monitor system with root disk
.TP
.B sot --theme cyberpunk
Launch the TUI with the Cyberpunk 2077 inspired theme
.TP
.B sot info
Display comprehensive system information
.TP
.B sot bench
Open the Bench view: pick a disk, press Enter, export with e
.TP
.B sot bench --disk disk3 --duration 30 --output results.json
Run 30-second benchmarks without the TUI and save results to JSON
.TP
.B sot disk
Open the Disks view
.TP
.B sot disk --list
Print disks and partitions as a plain table and exit
.TP
.B sot clean --dry-run
Preview what would be cleaned without deleting
.TP
.B sot clean
Open the Clean view: pick targets, then c to clean after confirming
.TP
.B sot ps
Open the Processes view with ports and dev environments
.TP
.B sot --keys
List every key binding id for the [keymap] config table
.TP
.B sot --config-path
Show where the config file is read from

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

.SS System Cleaning (sot clean)
.IP \\(bu 2
Clean system caches (user, system, font caches)
.IP \\(bu 2
Remove temporary files
.IP \\(bu 2
Clear application logs and crash reports
.IP \\(bu 2
Dry-run mode to preview changes
.IP \\(bu 2
macOS-specific cleaning (Xcode, Homebrew, etc.)

.SS Process Viewer (sot ps)
.IP \\(bu 2
Interactive process list with sorting
.IP \\(bu 2
Port monitoring with process association
.IP \\(bu 2
Development environment detection
.IP \\(bu 2
Kill/terminate processes interactively
.IP \\(bu 2
Multi-panel interface with tab navigation

.SH INTERACTIVE CONTROLS
The footer lists the keys for the focused panel; press ? for all of them.
.SS Views
.TP
.B 1 2 3 4 5 6
Overview, Processes, Disks, System, Bench, Clean (the header tabs are clickable too)
.TP
.B Tab / Shift+Tab
Move focus between panels
.TP
.B Esc
Close the detail drawer, or go back after a drill-down
.TP
.B /
Filter the focused list; Enter keeps the filter, Esc clears it
.TP
.B Ctrl+P
Command palette: go to a view, find a process or volume, act on the selected process, pick a theme
.TP
.B ?
Show or hide the key help
.TP
.B q
Quit the application
.SS Lists
.TP
.B ↑/k, ↓/j
Move the selection
.TP
.B PgUp/Ctrl+U, PgDn/Ctrl+D
Page up and down
.TP
.B Home/g, End/G
First and last row
.TP
.B Click a column header
Sort by that column
.SS Overview
.TP
.B Enter
On the process list, open the process in the Processes view; on the disk panel, open the Disks view; on the connections panel, open the listening ports
.SS Process tables
.TP
.B Enter
Show live details in the side drawer (double-click works too)
.TP
.B x
Kill selected process (requires confirmation)
.TP
.B t
Terminate selected process gracefully (requires confirmation)
.TP
.B o
Enter order-by mode: ←/→ pick a column, Enter toggles direction (DESC ↓ → ASC ↑ → OFF), Esc leaves
.TP
.B n
Show or hide the I/O and connection columns
.TP
.B r
Refresh
.SS Ports and development environments
.TP
.B o
Change sort column (cycles through available columns)
.TP
.B s
Toggle sort direction (ascending/descending)
.SS Bench
.TP
.B Enter
Benchmark the selected disk
.TP
.B + / -
Change the duration of each test
.TP
.B e
Export the results to a JSON file in the current directory
.TP
.B Esc
Cancel a running benchmark after the current test
.SS Clean
.TP
.B Space
Select or unselect a target
.TP
.B a
Select all cleanable targets, or none
.TP
.B d
Toggle dry run
.TP
.B c
Clean the selected targets after confirming
.TP
.B r
Scan again

.SH CONFIGURATION
sot reads an optional TOML file at $XDG_CONFIG_HOME/sot/config.toml (default ~/.config/sot/config.toml). Every key is optional:
.PP
.nf
theme = "cyberpunk"
default_view = "processes"
net = "en0"
disk = "/"

[refresh]
cpu = 1.0
processes = 2.0

[keymap]
"sot.process.kill" = "ctrl+k"
.fi
.PP
Command-line flags win over SOT_THEME, which wins over the config. A theme picked from the command palette is remembered in $XDG_STATE_HOME/sot/state.toml and used when nothing else sets one. Invalid values are reported and ignored.

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
