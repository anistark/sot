# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added
- **One app, six views** - Overview (`1`), Processes (`2`), Disks (`3`), System (`4`), Bench (`5`) and Clean (`6`) live in one app; `sot ps`, `sot disk`, `sot bench` and `sot clean` open it on their view
  - Switch with the number keys or by clicking the header tabs; each view keeps its selection, sort and scroll while hidden, and stops polling until you come back
  - Same header, footer and frames on every view; `?` shows every key for the focused panel
  - Process, port and dev environment lists are scrollable tables with mouse support; click a column header to sort
- **Drill down** - `Enter` on the overview's process list, disk panel or connections panel opens that process, volume or the ports list in its view; `Esc` goes back
- **Detail drawer** - `Enter` or a double-click in a list opens live details for the process, port or dev environment, following the cursor
- **Filter** - `/` filters the focused list (name, PID, user, command); `Esc` clears it
- **Command palette** - `Ctrl+P` jumps to a view, a process or a volume, and kills, terminates or copies the PID of the selected process
- **Bench view** - Pick a disk, watch each test finish, change the duration with `+`/`-`, export JSON with `e`, cancel with `Esc`
  - `sot bench --disk <id or mountpoint>` runs without any prompt
- **Overview zoom** - `+` makes the memory, disk and network graphs taller, `-` shortens them and gives the rows to the process list; the level is remembered for the next start
- **Clean view** - Scan, tick targets with `space` (`a` for all), dry run with `d`, clean with `c` after a confirmation
- **Browser session cleanup** - `sot clean` removes the old session snapshots Chrome, Chromium, Edge, Brave, Vivaldi, Opera, Arc, Firefox, LibreWolf and Zen leave in every profile, keeping the newest so your tabs still come back
  - `sot clean --force`, or `f` in the Clean view, removes the newest ones too
- **System view** - What `sot info` prints, as panels, with uptime, memory and battery kept live
- **Config file** - `~/.config/sot/config.toml` sets the theme, default view, `--net`/`--disk` defaults, refresh rates and key bindings; `sot --config-path` shows the path, `sot --keys` lists every binding id
  - A theme picked with `Ctrl+P` is remembered for the next start
- **Live theme switching** - Change the theme while `sot`, `sot ps` or `sot disk` is running: `Ctrl+P` → Theme
  - Graphs keep their history and lists keep their selection, sort and scroll position
  - The theme picker only lists SOT themes

### Changed
- **BREAKING: keys** - `x` kills (was `k`), `j`/`k` move in every list (vim style), `g`/`G` jump to the first/last row
- **Process columns adapt to the width** - Narrow panels drop the I/O, connection, user and thread columns before the process name; the old "Net I/O" column is now "I/O" since it shows disk I/O
- **Frames** - Every panel uses the same theme frame (`solid` in classic, `outer` in cyberpunk)
- The dashboard's `i` (interactive mode) toggle is gone: the process list responds to keys whenever it has focus
- **Classic follows your terminal** - The `classic` theme now uses the terminal's own palette and background inside the TUI, matching the printed commands
- **Confirmation dialog** - Kill and terminate both ask first in a dialog (`y` to confirm, `n` or `Esc` to cancel) instead of a notification
- **`sot --disk` without a value** - The volume picker opens inside sot instead of a separate prompt
- **`sot bench` and `sot clean`** - Open their view in a terminal; flags and non-terminal runs keep the printed flow
- **Printed output follows `--theme`** - `sot --version`, `sot info`, `sot bench`, `sot clean` and `sot disk --list` use the theme's colours and frames
- **Connections panel** - Shows sockets by state (active, listen, UDP, other) with a stacked bar, a graph of active connections over time and the processes holding the most sockets
  - On macOS without `sudo` it lists your own processes' sockets instead of an "access denied" lock, and says so in the panel

### Fixed
- Disk, network and per-process I/O rates use the real time between samples instead of assuming a fixed interval
- Volume picker for `--disk` now lists every mountpoint on Linux, where there are no `/Volumes/*` mounts

## [6.3.0](https://github.com/anistark/sot/releases/tag/v6.3.0) - 2026-10-07

Also ships `sot disk --list`, which was prepared as 6.2.0 but never tagged or published.

### Added
- **Themes** - Pick a colour theme with `--theme` / `-T` or the `SOT_THEME` environment variable
  - `classic` stays the default and looks the same as before
  - New `cyberpunk` preset inspired by Cyberpunk 2077: neon yellow, cyan, pink and terminal green on near-black
  - Themes restyle components, not just colours: tag-style panel titles, block bar graphs that fade toward pink, segmented meters, striped tables and a glitching logo
  - Applies to the main dashboard, `sot ps` and `sot disk`
- **`sot disk --list`** - Print all disks and partitions as a plain, non-interactive table
  - One row per physical disk with its partitions nested underneath
  - Device, mountpoint, filesystem, size, used, free, colour-coded usage bar and percentage
  - Totals across all disks; compact layout on narrow terminals
  - `-l` short form

### Changed
- **Memory panel** - Each memory graph is now a fixed 2 rows and the panel's row shrinks to fit, giving the spare rows to the CPU, disk and network panels
  - The GPU graph and the SOT animation shrink to fit the shorter row instead of being cut off

## [6.1.0](https://github.com/anistark/sot/releases/tag/v6.1.0) - 2026-08-06

### Added
- **GPU Monitoring Widget** - Live GPU statistics now appear in the main `sot` dashboard:
  - Real-time utilization history graph with current percentage
  - Memory usage (used/total on NVIDIA; in-use and allocated on Apple Silicon's unified memory)
  - Temperature and power draw where the platform exposes them
  - Renderer/Tiler utilization breakdown and GPU core count on Apple Silicon
  - Cross-platform detection: Apple Silicon via `ioreg` (no sudo required), NVIDIA via `nvidia-smi`, AMD via `rocm-smi` (best effort)
  - Falls back to the decorative animation when no GPU is detected
  - No new runtime dependencies
- **Coding agent caches** - `sot clean` now finds the caches, debug logs and scratch directories of Claude Code, pi, opencode and Kilo Code
  - Only agents installed on the machine show up
  - Conversation history, sessions, credentials and config are left alone
  - Relocated directories are found through `CLAUDE_CONFIG_DIR`, the XDG variables, `APPDATA`/`LOCALAPPDATA` and `VSCODE_PORTABLE`
- **macOS Install Data cleaning** - `sot clean` now reports the leftover macOS installer payload, routinely 10GB+ on machines that have taken a system update
  - Covers both the data volume path and the pre-Catalina root path
  - Marked as requiring sudo; the SIP protected `Locked Files` stub inside is skipped with a warning

### Fixed
- **`sot clean` under sudo** - Targets marked as requiring sudo were skipped unconditionally, so `sudo sot clean` never cleaned them despite the summary saying it would
  - The skip now checks for actual elevation, making `Temp Files`, `System Logs` and `macOS Install Data` reclaimable
  - Running elevated is called out in the header, and the summary no longer reports those targets as "will be skipped"

## [6.0.1](https://github.com/anistark/sot/releases/tag/v6.0.1) - 2026-01-18

### Fixed
- **PyPI Package** - Fixed critical packaging issue where source code was excluded from sdist tarball
  - Removed overly restrictive `include` directive in `pyproject.toml` that excluded `src/` directory
  - Package can now be properly installed via pip and Homebrew
  - Version 6.0.0 was broken due to missing source files

## [6.0.0](https://github.com/anistark/sot/releases/tag/v6.0.0) - 2026-01-18

### Added
- **Process Viewer** - New `sot ps` command for interactive process monitoring with three synchronized panels:
  - **Process List**: All running processes with PID, name, memory usage, and CPU percentage
    - Navigate with arrow keys (↑/↓)
    - Sortable columns (press `O` to enter order by mode)
    - Real-time updates every 2 seconds
    - Shows up to 500 processes
    - Interactive actions: Enter for details, K to kill, T to terminate, R to refresh
  - **Listening Ports**: All open ports listening for connections
    - Shows port number, bind address, process name, and PID
    - Updates every 3 seconds
    - May require sudo on macOS for full port detection
    - Interactive process management for port-related processes
  - **Development Environment**: Automatically detects running development servers
    - Supports: Node.js, Python, Docker, Ruby, Go, Rust
    - Shows process count, listening ports, CPU and memory usage per environment type
    - Groups related processes together
    - Updates every 5 seconds
  - **Navigation**: Tab to switch panels, arrow keys to navigate, Q to quit

### Changed
- **Textual Framework Upgrade** - Upgraded from version 5.3.0 to 7.3.0:
  - Enhanced TUI performance and stability
  - Improved widget rendering and event handling
  - Better cross-platform compatibility

## [5.1.0](https://github.com/anistark/sot/releases/tag/v5.1.0) - 2026-01-02

### Added
- **System Deep Cleaning** - New `sot clean` command for removing system caches, logs, and temporary files:
  - Interactive mode with confirmation prompt before deletion
  - Dry run mode with `--dry-run` flag to preview what will be deleted without actually removing files
  - Cross-platform support (macOS, Linux, Windows)
  - Cleans multiple target types:
    - User caches and logs
    - System logs (macOS)
    - Temporary files (`/tmp`, `/var/tmp`, Windows temp and Prefetch)
    - Package manager caches (Homebrew, pip, npm, APT, DNF, Yum)
    - Browser caches (Chrome, Safari, Firefox)
    - Thumbnails (Linux)
    - Trash (macOS)
  - Visual preview showing size of items to be cleaned
  - Privileged cleaning with sudo for system-level items (requires elevated permissions)
  - Safe deletion with proper error handling and permission checks

- **Disk Selection Option** - New `--disk` / `-D` flag for selecting which disk to monitor:
  - Interactive volume picker with arrow key navigation when used without a value
  - Direct mountpoint specification (e.g., `sot --disk /Volumes/External`)
  - Shows only user-relevant volumes (Macintosh HD and mounted drives)
  - Displays accurate disk usage for macOS (uses Data volume for correct percentages)

### Changed
- **Man Page Enhancements** - Comprehensive man page documentation:
  - Detailed command descriptions and usage examples
  - Complete option and flag reference
  - Added examples for all subcommands

### Fixed
- Type annotations and formatting improvements

## [5.0.0](https://github.com/anistark/sot/releases/tag/v5.0.0) - 2025-12-06

### Added
- **Interactive Disk TUI** - New `sot disk` command for viewing all physical disks:
  - Displays all physical disks with accurate space calculations for APFS containers
  - Visual partition boxes with usage bars and statistics
  - Real-time I/O statistics per disk
  - Proper disk grouping (disk1, disk3, disk5, etc.)

- **System Information Display** - New `sot info` command for comprehensive system information:
  - Beautiful OS-specific ASCII logos (macOS, Linux distros, Windows)
  - Automatic distribution detection for Linux (Ubuntu, Debian, Fedora, Red Hat, Arch, Manjaro, Pop!_OS, CentOS)
  - Organized information sections:
    - **System**: Host, Model name, SKU, Identifier, Serial number
    - **Software**: OS with version name, Kernel, Firmware, DE, WM, Shell, Terminal
    - **Hardware**: Chip details with P+E core breakdown, GPU with core count, Memory
    - **Displays**: All connected displays with resolutions, refresh rates, and names
    - **Status**: Uptime, Battery status
  - Support for multiple display detection with detailed info (resolution, refresh rate, display name)
  - Chip information with performance/efficiency core breakdown (e.g., 6P + 2E cores)
  - macOS-specific features: Model name/number, Serial number, Firmware version
  - Cross-platform compatibility (macOS, Linux, Windows)

- **Disk Benchmarking Tool** - New `sot bench` command for measuring disk performance:
  - Sequential read/write throughput testing
  - Random read/write IOPS measurement
  - Real-time latency metrics with automatic unit scaling (ns, µs, ms, s)
  - Interactive disk selection with arrow keys
  - JSON export of benchmark results
  - Support for throughput auto-scaling (MB/s → GB/s → TB/s)
  - Configurable test duration with `--duration` flag (default: 10 seconds)
    - Run quick benchmarks with `--duration 5` or longer tests with `--duration 30`
  - Accurate disk latency measurements using fsync for real disk I/O
  - 1GB test files for proper disk performance characterization

- **Installation Script** - Bash installation script for easier source installation
- **Homebrew** - Install with `brew tap anistark/tools && brew install sot`

### Changed
- **Help Output Formatting** - Improved command-line help display:
  - Subcommands now display inline: `commands: {info,bench}` instead of separate lines
  - Cleaner, more compact help text

### Improved
- **Smart Unit Formatting** - Automatic scaling for performance metrics:
  - Disk sizes display with appropriate units (B, KB, MB, GB, TB)
  - Throughput shows in best-fit units (MB/s, GB/s, TB/s)
  - Latency measurements scale intelligently (ns, µs, ms, s)

### Fixed
- Release binary format issues
- Formatting improvements

## [4.4.2](https://github.com/anistark/sot/releases/tag/v4.4.2) - 2025-11-25

### Added
- Interactive Order By feature for Processes widget
  - Press `O` to enter order by mode with visual highlighting
  - Navigate between 7 sortable columns: PID, Process, Threads, Memory, Net I/O, Connections, CPU % using arrow keys.
  - Toggle sort direction with Enter: DESC (↓) → ASC (↑) → OFF → cycle
  - Press `O` or `Esc` to exit order by mode
  - Robust sorting with proper handling of all data types and edge cases
- Kill the selected process with `k`, after a confirmation dialog

### Changed
- Improved processes widget UI with color-coded sort indicators

### Fixed
- Release binaries

## [4.4.1](https://github.com/anistark/sot/releases/tag/v4.4.1) - 2025-11-20

### Added
- DEB packages with GPG signing and RPM packages, built by GitHub Actions
- GPG fingerprint in the README for package verification
- Badges in README for project visibility
- Comprehensive CHANGELOG following best practices

### Changed
- Upgraded to Textual v5 framework
- Type checking moved from `pyright` to `ty`
- Refactored GitHub Actions pipeline for better maintainability
- Improved README installation instructions
- Dependency version updates for security and compatibility:
  - `psutil`: 7.0.0 → 7.1.3 (bug fixes and enhancements)
  - `rich`: 14.1.0 → 14.2.0 (minor updates)
  - `textual-dev`: 1.6.0 → 1.8.0 (development enhancements)
  - `flake8`: 7.0.0 → 7.3.0 (code quality improvements)
  - `blacken-docs`: 1.16.0 → 1.19.1 (documentation formatting)
  - `build`: 1.0.0 → 1.3.0 (build system enhancements)

### Fixed
- CPU widget on Windows systems where the core and thread counts don't divide evenly
- `--log` debug logging, which Textual ignored because it reads the setting at import time
- DEB/RPM workflow triggers to use release published event instead of manual dispatch
- Graceful error handling when distribution artifacts are missing
- Release automation to publish PyPI immediately without waiting for DEB/RPM builds
- Typing and formatting issues

## [4.4.0](https://github.com/anistark/sot/releases/tag/vdev) - 2025-08-24

Released under the `vdev` tag.

### Added
- Type checking using `pyright` with comprehensive type annotations

### Changed
- Development tooling switched to the `uv` package manager

## [4.3.2](https://github.com/anistark/sot/releases/tag/v4.3.2) - 2025-07-19

### Fixed
- Completes 4.3.1, which was published without part of its network discovery and flake8 cleanup

## [4.3.1](https://github.com/anistark/sot/releases/tag/v4.3.1) - 2025-07-19

### Added
- Per-process network usage in the process widget
- `--net` option to pick the network interface to display, shown in the title

### Changed
- Build backend migration from `setuptools` to `hatchling`

### Fixed
- `setuptools` package discovery issues
- Process widget key bindings
- Layout of the network connections panel when its data needs elevated permissions

## [4.1.0](https://github.com/anistark/sot/releases/tag/v4.1.0) - 2025-06-18

### Added
- Health monitoring features
- Network connection details in system view
- 3-column layout redesign
- Animated SOT widget

### Changed
- Complete widget restructuring for better UX
- Improved information density in display

## [3.2.1](https://github.com/anistark/sot/releases/tag/v3.2.1) - 2025-06-15

### Added
- Interactive scrolling for process lists
- Development/watch modes for easier development

## [3.0.0](https://github.com/anistark/sot/releases/tag/v3.0.0) - 2025-06-15

### Changed
- Upgraded to Textual v3.4.0 and other packages

## [2.1.1](https://github.com/anistark/sot/releases/tag/v2.1.1) - 2025-04-04

### Changed
- More room for the process list in the grid
- Setup details in the README

## [2.1.0](https://github.com/anistark/sot/releases/tag/v2.1.0) - 2025-01-19

### Changed
- Upgraded to Textual v1.0.0

## [2.0.3](https://github.com/anistark/sot/releases/tag/v2.0.3) - 2025-01-12

### Added
- Battery value warnings

### Changed
- Updated `psutil`

### Fixed
- Syntax error from nested double quotes in the disk widget

## [2.0.2](https://github.com/anistark/sot/releases/tag/v2.0.2) - 2024-12-13

### Fixed
- Disk view

## [2.0.1](https://github.com/anistark/sot/releases/tag/v2.0.1) - 2024-11-28

First 2.x release on PyPI.

### Fixed
- Formatting fixes

## [2.0.0](https://github.com/anistark/sot/releases/tag/v2.0.0) - 2024-11-28

Tagged, but never published to PyPI.

### Changed
- Upgraded Textual and other packages

## [1.1.0](https://github.com/anistark/sot/releases/tag/v1.1.0) - 2024-11-22

### Changed
- Packaging moved off `setup.py`
- Updated install instructions

## 1.0.0 - 2024-11-22

### Added
- First release on PyPI, with core system monitoring features

---

## Legend

### Categories (For Users)
- **Added**: New features or functionality that users can benefit from
- **Changed**: Modifications to existing features or major updates
- **Fixed**: Bug fixes and corrections that improve stability
- **Removed**: Deprecated or removed features
- **Deprecated**: Features that will be removed in future versions
- **Security**: Security-related updates and CVE fixes

### Development Notes
Development-facing changes are included only when they impact user experience, stability, or are significant infrastructure improvements:
- Build system changes affecting package distribution
- Dependency updates with security or compatibility implications
- Major refactoring affecting maintainability or performance
- Type checking and code quality improvements

---

## Release Process

### Creating a New Release

1. Update version in `src/sot/__about__.py`
2. Create a new section at the top of CHANGELOG.md with `## [Version] - YYYY-MM-DD`
3. Move items from [Unreleased] section to the new version section
4. Group changes by category (Added, Changed, Fixed, etc.)
5. Focus on user-facing changes; include only significant development changes
6. Create a git tag: `git tag vX.Y.Z`
7. Push the tag: `git push origin vX.Y.Z`

### Versioning Strategy

This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR** (X.0.0): Breaking changes or significant feature additions
- **MINOR** (0.Y.0): New functionality added in backward-compatible manner
- **PATCH** (0.0.Z): Bug fixes and minor improvements

### Release Automation

Releases trigger automated workflows:
1. Tag push → PyPI publish workflow (builds and publishes to PyPI, creates GitHub release)
2. Release publish event → DEB/RPM build workflows (generates distribution packages)
3. All packages uploaded to GitHub release automatically
