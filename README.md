<p align="center" style="background-color: #ffffff;">
  <a href="https://github.com/anistark/sot"><img alt="sot" src="https://raw.githubusercontent.com/anistark/sot/refs/heads/main/images/sot.png" width="200px"/></a>
  <p align="center">Command-line system obervation tool.</p>
</p>

`sot` is a Command-line System Obervation Tool in the spirit of [top](<https://en.wikipedia.org/wiki/Top_(software)>). It displays various interesting system stats and graphs them. Works on all operating systems.

[![PyPI - Version](https://img.shields.io/pypi/v/sot)](https://pypi.org/project/sot/) [![PyPI Downloads](https://static.pepy.tech/badge/sot/month)](https://pypi.org/project/sot/) ![PyPI - Status](https://img.shields.io/pypi/status/sot) [![Open Source](https://img.shields.io/badge/open-source-brightgreen)](https://github.com/anistark/sot) [![Contributors](https://img.shields.io/github/contributors/anistark/sot)](https://github.com/anistark/sot/graphs/contributors) ![maintenance-status](https://img.shields.io/badge/maintenance-actively--developed-brightgreen.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Installation

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

### Quick Install (Recommended)

**One-line installer for macOS and Linux** - Automatically detects your environment and installs all dependencies:

<!--pytest-codeblocks: skip-->

```sh
curl -fsSL https://raw.githubusercontent.com/anistark/sot/main/install.sh | bash
```

This script will:
- ✅ Detect your operating system
- ✅ Check for Python 3.10+ (installs if missing)
- ✅ Install pipx (if not present)
- ✅ Install sot and configure PATH
- ✅ Verify the installation

**Note:** This installation script does not work on Windows. Windows users should use one of the [alternative installation methods](#alternative-installation-methods) below.

---

### Alternative Installation Methods

<details>
<summary>Using brew</summary>

<!--pytest-codeblocks: skip-->

```sh
brew tap anistark/tools
brew install sot
```

Or single line:

<!--pytest-codeblocks: skip-->

```sh
brew install anistark/tools/sot
```

Update using:

<!--pytest-codeblocks: skip-->

```sh
brew update && brew upgrade sot
```

</details>

<details>
<summary>Using uv</summary>

Install and run with [`uv`](https://github.com/astral-sh/uv):

<!--pytest-codeblocks: skip-->

```sh
uv tool install sot
```

</details>

<details>
<summary>Using pipx</summary>

Install and run with [`pipx`](https://github.com/pypa/pipx). Setup pipx before proceeding.

<!--pytest-codeblocks: skip-->

```sh
python3 -m pipx install sot
python3 -m pipx ensurepath
sudo pipx ensurepath --global
```

or in single line:

<!--pytest-codeblocks: skip-->

```sh
python3 -m pipx install sot && python3 -m pipx ensurepath && sudo pipx ensurepath --global
```
</details>

<details>
<summary>Using DEB Package (Experimental - Debian/Ubuntu)</summary>
### Using DEB Package (Experimental - Debian/Ubuntu)

**⚠️ Experimental**: DEB packages are experimental. Use `uv` or `pipx` for recommended installation.

Download the latest DEB package from the [releases page](https://github.com/anistark/sot/releases) and install:

<!--pytest-codeblocks: skip-->

```sh
# Download latest .deb file from releases
wget https://github.com/anistark/sot/releases/latest/download/sot-*.deb

# Install the package
sudo dpkg -i sot-*.deb

# Install any missing dependencies (if needed)
sudo apt-get install -f
```
</details>

<details>
<summary>Using RPM Package (Experimental - RHEL/CentOS/Fedora)</summary>

**⚠️ Experimental**: RPM packages are experimental. Use `uv` or `pipx` for recommended installation.

Download the latest RPM package from the [releases page](https://github.com/anistark/sot/releases) and install:

<!--pytest-codeblocks: skip-->

```sh
# Download latest .rpm file from releases
wget https://github.com/anistark/sot/releases/latest/download/sot-*.rpm

# Install the package
sudo rpm -ivh sot-*.rpm
```

### Verifying Package Signatures (Recommended)

For enhanced security, verify GPG signatures before installing packages:

<!--pytest-codeblocks: skip-->

```sh
# Import the public signing key (one time setup)
curl -fsSL https://github.com/anistark/sot/releases/latest/download/public-key.asc | gpg --import

# For DEB packages:
dpkg-sig --verify sot-*.deb
# Or verify using detached signature
gpg --verify sot-*.deb.asc sot-*.deb
# Verify checksums
gpg --verify SHA256SUMS.sig && sha256sum -c SHA256SUMS

# For RPM packages:
gpg --verify sot-*.rpm.asc sot-*.rpm
# Verify checksums
gpg --verify SHA256SUMS-RPM.sig && sha256sum -c SHA256SUMS-RPM
```

**GPG Key Fingerprint:** `DCD1 9CA3 2C3F ACAA 1360  1C78 F4D7 EFDB 552E 84C9`
</details>

<details>
<summary>Install from source</summary>

For testing or installing the latest version from source directly on your system.

**Using uv (Recommended):**

<!--pytest-codeblocks: skip-->

```sh
# Clone the repository
git clone https://github.com/anistark/sot.git
cd sot

# Install from source (system-wide)
uv pip install --system .

# Run from anywhere
sot
```

**Using pipx:**

<!--pytest-codeblocks: skip-->

```sh
# Clone the repository
git clone https://github.com/anistark/sot.git
cd sot

# Install from source using pipx
pipx install .

# Run from anywhere
sot
```
</details>

---

Run with:

<!--pytest-codeblocks: skip-->

```sh
sot
```

![sot-demo](https://github.com/user-attachments/assets/780449fd-27e0-40ee-ae9a-7527bf99d7de)

---

## Features

### System

- CPU Usage
  - Per Core and Thread level
- Processes with ID, threads, memory and cpu usage
  - **Interactive Order By**: Press `O` to enter order by mode, navigate columns with arrow keys, toggle sort direction with Enter (DESC ↓ → ASC ↑ → OFF → cycle)

### Disk

- **Interactive Disk TUI** - View all physical disks with partitions
  - Real-time disk usage monitoring with accurate APFS container calculations
  - Visual usage bars and percentage indicators
  - I/O statistics (read/write counts and bytes)
- Disk Usage
  - Per Read/Write
- Capacity
  - Free
  - Used
  - Total
  - Percent

### Memory

- Memory Usage
- Capacity
  - Free
  - Available
  - Used
  - Swap

### Network

- Local IP
- Upload/Download Speed
- Bandwidth
- Network Usage
- **Select Interface**: Use `--net` / `-N` to monitor a specific network interface

### Options

- **Disk Selection**: Use `--disk` / `-D` to monitor a specific volume
  - `sot --disk` - Interactive picker with arrow keys
  - `sot --disk /Volumes/External` - Monitor specific volume

---

## System Information

The `sot info` command displays comprehensive system information with a beautiful OS-specific ASCII logo.

### Usage

```sh
sot info
```

### Example Output

```
                  ,MMMM.            Host        -  john@macbook.local
                .MMMMMM             Model       -  MacBook Pro
                MMMMM,              SKU         -  MK1E3LL/A
      .;MMMMM:' MMMMMMMMMM;.        Identifier  -  MacBookPro18,1
    MMMMMMMMMMMMNWMMMMMMMMMMM:      Serial      -  C02YX2QZMD6R
  .MMMMMMMMMMMMMMMMMMMMMMMMWM.
  MMMMMMMMMMMMMMMMMMMMMMMMM.        OS          -  macOS 14.5.0 Sonoma
 ;MMMMMMMMMMMMMMMMMMMMMMMM:         Kernel      -  23.5.0
 :MMMMMMMMMMMMMMMMMMMMMMMM:         Firmware    -  10151.121.3
 .MMMMMMMMMMMMMMMMMMMMMMMMM.        DE          -  Aqua
  MMMMMMMMMMMMMMMMMMMMMMMMMMM.      WM          -  Quartz Compositor
   .MMMMMMMMMMMMMMMMMMMMMMMMMM.     Shell       -  zsh
     MMMMMMMMMMMMMMMMMMMMMMMM       Terminal    -  iTerm.app (3.5.2)
      ;MMMMMMMMMMMMMMMMMMMM.
        .MMMM,.    .MMMM,.          Chip        -  Apple M1 Pro (8P + 2E cores)
                                    GPU         -  Apple M1 Pro (16 cores)
                                    Memory      -  8 GiB / 32 GiB

                                    Displays    -  2560 x 1600 Retina (Color LCD)
                                                   3840 x 2160@60.00Hz (Dell U2720Q)

                                    Uptime      -  12d 4h 23m
                                    Battery     -  87% & Discharging
```

### Features

The info command displays detailed system information organized into logical sections:

**System Information**
- Host (user@hostname)
- Model name (e.g., MacBook Pro)
- SKU/Model number
- Model identifier
- Serial number

**Software**
- Operating system with version name (e.g., macOS 15.6.1 Sequoia)
- Kernel version
- Firmware version
- Desktop Environment (DE)
- Window Manager (WM)
- Shell
- Terminal emulator

**Hardware**
- Chip details with performance/efficiency core breakdown (e.g., Apple M1 Pro with 6P + 2E cores)
- GPU model with core count
- Memory (used / total)

**Displays**
- All connected displays with resolutions, refresh rates, and display names
- Screen brightness (when available)

**Status**
- System uptime
- Battery status (percentage and charging state)

### OS-Specific Logos

The command automatically detects your operating system and distribution, displaying the appropriate ASCII logo:

**macOS**: Apple logo

**Linux Distributions**:
- Ubuntu
- Debian
- Fedora
- Red Hat / RHEL
- Arch Linux
- Manjaro
- Pop!_OS
- CentOS
- Generic Linux/Tux (fallback)

**Windows**: Windows logo

---

## System Cleanup

The `sot clean` command performs a deep clean of your system by removing caches, logs, and temporary files.

### Usage

```sh
# Interactive mode - shows what can be cleaned and asks for confirmation
sot clean

# Dry run - preview what would be cleaned without deleting
sot clean --dry-run
```

### What Gets Cleaned

The clean command intelligently detects your operating system and cleans platform-specific locations:

**macOS:**
- Application caches (`~/Library/Caches`)
- Application logs (`~/Library/Logs`)
- Homebrew package cache
- System temporary files (`/tmp`)
- Browser caches (Chrome, Safari, Firefox)
- Python pip cache
- npm cache
- Trash bin

**Linux:**
- User cache (`~/.cache`)
- Thumbnails cache
- System temporary files (`/tmp`, `/var/tmp`)
- Package manager caches (APT, DNF, Yum)
- Browser caches
- Python pip cache
- npm cache

**Windows:**
- User temporary files (`%TEMP%`)
- Windows temporary files
- Prefetch files
- Browser caches
- Python pip cache
- npm cache

### Permissions

Some cleaning targets require elevated privileges (sudo/administrator). The clean command will:
- Show which items require elevated privileges in the summary
- Skip these items during cleaning if not running with sudo
- Provide clear notifications about what was skipped

To clean items requiring sudo:
```sh
sudo sot clean
```

### Safety Features

- **Dry run mode**: Preview what will be cleaned without making changes
- **Interactive confirmation**: Always asks before deleting files
- **Clear reporting**: Shows exactly what will be cleaned and how much space will be freed
- **Graceful error handling**: Skips files that can't be accessed rather than failing

---

## Disk Benchmarking

The `sot bench` command allows you to measure disk performance with comprehensive benchmarks including sequential throughput, random IOPS, and latency distribution.

### Interactive Mode (Default)

```sh
sot bench
```

This will display available disks and let you select one to benchmark interactively.

### Benchmark Options

```sh
# Benchmark with default 10 second duration per test
sot bench

# Specify custom duration (in seconds)
sot bench --duration 5     # Quick 5-second benchmark
sot bench -d 30            # Longer 30-second benchmark for more stable results

# Specify custom output file
sot bench --output results.json

# Combine options
sot bench --duration 20 --output bench_results.json
```

### Benchmark Tests

The benchmarking tool runs four comprehensive tests:

1. **Sequential Read** - Measures sustained read throughput (MB/s)
2. **Sequential Write** - Measures sustained write throughput (MB/s)
3. **Random Read IOPS** - Measures random read operations per second
4. **Random Write IOPS** - Measures random write operations per second

Each test runs for the specified duration (default: 10 seconds) and provides detailed metrics:
- Throughput/IOPS measurements
- Min/Avg/Max latencies
- p50, p95, p99 percentile latencies
- Total test duration

### Duration Parameter

The `--duration` flag controls how long each test runs:
- **Default: 10 seconds** - Quick, reliable measurements for most use cases
- **Shorter durations (5s)** - Very quick benchmarks for rapid testing
- **Longer durations (30s+)** - More stable results, accounts for system variance better

---

For all options, see

<!--pytest-codeblocks:skipif(sys.version_info < (3, 10))-->

```sh
sot -H
```

<!--pytest-codeblocks: expected-output-->

```
usage: sot [--help] [--version] [--log LOG] [--net NET] [--disk [DISK]]
           {info,bench,disk,clean} ...

Command-line System Obervation Tool ≈

commands: {info,bench,disk,clean}
    info                Display system information
    bench               Disk benchmarking
    disk                Interactive disk information viewer
    clean               Deep clean system caches, logs, and temp files

options:
  --help, -H                Show this help message and exit.
  --version, -V             Display version information with styling
  --log LOG, -L LOG         Debug log file path (enables debug logging)
  --net NET, -N NET         Network interface to display (default: auto-detect best interface)
  --disk [DISK], -D [DISK]  Disk mountpoint to display (use without value for interactive selection)
```

For benchmark-specific options:

```sh
sot bench -h
```

<!--pytest-codeblocks: expected-output-->

```
usage: sot bench [-h] [--output OUTPUT] [--duration DURATION]

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output file for benchmark results (JSON format)
  --duration DURATION, -d DURATION
                        Duration for each benchmark test in seconds (default: 10s)
```

For clean-specific options:

```sh
sot clean -h
```

<!--pytest-codeblocks: expected-output-->

```
usage: sot clean [-h] [--dry-run]

options:
  -h, --help  show this help message and exit
  --dry-run   Show what would be cleaned without actually deleting
```

Main Theme:

| Color | Hex | RGB |
| --- | --- | --- |
| sky_blue3 | `#5fafd7` | `rgb(95,175,215)` |
| aquamarine3 | `#5fd7af` | `rgb(95,215,175)` |
| yellow | `#808000` | `rgb(128,128,0)` |
| bright_black | `#808080` | `rgb(128,128,128)` |
| slate_blue1 | `#875fff` | `rgb(135,95,255)` |
| red3 | `#d70000` | `rgb(215,0,0)` |
| dark_orange | `#d75f00` | `rgb(215,95,0)` |

All supported [colors](https://rich.readthedocs.io/en/latest/appendix/colors.html).

---

<p align="center">
  <p align="center">🏴 ≈ 🏴</p>
</p>

---

`sot` uses:
- [Textual](https://github.com/willmcgugan/textual/) for layouting
- [rich](https://rich.readthedocs.io/en/latest/index.html) for rich text
- [psutil](https://github.com/giampaolo/psutil) for fetching system data.

Tested Systems:

![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0)
![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)

_If you use a system that's not listed above, feel free to add to the list. If you're facing any issues, would be happy to take a look._

---

Other top alternatives in alphabetical order:

- [tiptop](https://github.com/nschloe/tiptop) ✨ This project was created on top of `tiptop`, when it became unmaintained.
- [bashtop](https://github.com/aristocratos/bashtop), [bpytop](https://github.com/aristocratos/bpytop), [btop](https://github.com/aristocratos/btop)
- [bottom](https://github.com/ClementTsang/bottom) (one of my fav)
- [Glances](https://github.com/nicolargo/glances)
- [gtop](https://github.com/aksakalli/gtop)
- [htop](https://github.com/htop-dev/htop)
