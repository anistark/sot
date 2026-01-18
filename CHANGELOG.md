# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

...

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
  - Cross-platform support (macOS, Linux)
  - Cleans multiple target types:
    - User and system caches
    - Application and system logs
    - Temporary files
    - Package manager caches (Homebrew, pip, npm, yarn, cargo, etc.)
    - Browser caches
    - Docker build cache and unused volumes
    - Trash/Recycle Bin
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

## [4.4.2](https://github.com/anistark/sot/releases/tag/v4.4.2) - 2024-11-25

### Added
- Interactive Order By feature for Processes widget
  - Press `O` to enter order by mode with visual highlighting
  - Navigate between 7 sortable columns: PID, Process, Threads, Memory, Net I/O, Connections, CPU % using arrow keys.
  - Toggle sort direction with Enter: DESC (↓) → ASC (↑) → OFF → cycle
  - Press `O` or `Esc` to exit order by mode
  - Robust sorting with proper handling of all data types and edge cases

### Changed
- Improved processes widget UI with color-coded sort indicators

## [4.4.1](https://github.com/anistark/sot/releases/tag/v4.4.1) - 2024-11-20

### Added
- Debug and fix DEB/RPM package generation workflows with proper error handling
- GitHub Actions improvements for reliable package distribution
- Comprehensive CHANGELOG following best practices

### Changed
- Dependency version updates for security and compatibility:
  - `psutil`: 7.0.0 → 7.1.3 (bug fixes and enhancements)
  - `rich`: 14.1.0 → 14.2.0 (minor updates)
  - `textual-dev`: 1.6.0 → 1.8.0 (development enhancements)
  - `flake8`: 7.0.0 → 7.3.0 (code quality improvements)
  - `blacken-docs`: 1.16.0 → 1.19.1 (documentation formatting)
  - `build`: 1.0.0 → 1.3.0 (build system enhancements)

### Fixed
- DEB/RPM workflow triggers to use release published event instead of manual dispatch
- Graceful error handling when distribution artifacts are missing
- Release automation to publish PyPI immediately without waiting for DEB/RPM builds

## [4.4.0](https://github.com/anistark/sot/releases/tag/vdev) - 2024-08-28

### Added
- Type checking using `pyright` with comprehensive type annotations
- RPM package distribution via GitHub Actions
- DEB package distribution with GPG signing support
- GitHub Actions automation for package releases
- Network information display in process widget
- Health status monitoring
- 3-column layout redesign
- Interactive scrolling for process lists
- Badges in README for project visibility

### Changed
- Major build system refactor: switched from `setuptools` to `uv` package manager
- Build backend migration from `setuptools` to `hatchling`
- Refactored GitHub Actions pipeline for better maintainability
- Improved README installation instructions
- Complete widget restructuring for better UX
- Upgraded to Textual v5 framework

### Fixed
- Fixed `setuptools` package discovery issues
- Network discovery edge cases
- Typing and formatting issues resolved
- Various compatibility fixes

## [4.3.2](https://github.com/anistark/sot/releases/tag/v4.3.2) - 2024-07-19

### Added
- GPG fingerprint documentation for package verification

### Changed
- Build backend migration from `setuptools` to `hatchling`
- Refactored GitHub Actions pipeline for better maintainability
- Improved README installation instructions

### Fixed
- Fixed `setuptools` package discovery issues
- Network discovery edge cases
- Typing and formatting issues resolved

## [4.3.1](https://github.com/anistark/sot/releases/tag/v4.3.1) - 2024-06-18

### Added
- Network information in process widget
- Health status monitoring

### Changed
- Improved network discovery module

### Fixed
- Various network detection issues

## [4.1.0](https://github.com/anistark/sot/releases/tag/v4.1.0) - 2024-06-18

### Added
- Health monitoring features
- Network connection details in system view
- 3-column layout redesign
- Interactive scrolling for process lists

### Changed
- Complete widget restructuring for better UX
- Improved information density in display

## [3.2.1](https://github.com/anistark/sot/releases/tag/v3.2.1) - 2024-06-15

### Added
- Development/watch modes for easier development
- Interactive scrolling capabilities

### Changed
- Upgraded to Textual v3 framework
- Improved terminal compatibility

## [3.0.0](https://github.com/anistark/sot/releases/tag/v3.0.0) - 2024-06-15

### Added
- Pre-release upgrade to Textual v3.4.0

## [2.1.1](https://github.com/anistark/sot/releases/tag/v2.1.1) - 2024-01-19

### Added
- Upgrade to Textual v1.0.0

## [2.1.0](https://github.com/anistark/sot/releases/tag/v2.1.0) - 2024-01-19

### Added
- Textual v1.0.0 support

## [2.0.3](https://github.com/anistark/sot/releases/tag/v2.0.3) - 2024-01-11

### Added
- Battery value warnings

## [2.0.2](https://github.com/anistark/sot/releases/tag/v2.0.2) - 2023-12-13

### Added
- First public-ready release with working components

## [2.0.1](https://github.com/anistark/sot/releases/tag/v2.0.1) - 2023-11-28

### Added
- Initial formatting fixes for public release

## [2.0.0](https://github.com/anistark/sot/releases/tag/v2.0.0) - 2023-01-11

### Added
- Foundation release with core system monitoring features

## [1.1.0] - Early Release

### Added
- Initial features and system monitoring capabilities

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
