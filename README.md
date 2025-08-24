<p align="center" style="background-color: #ffffff;">
  <a href="https://github.com/anistark/sot"><img alt="sot" src="https://raw.githubusercontent.com/anistark/sot/refs/heads/main/images/sot.png" width="200px"/></a>
  <p align="center">Command-line system obervation tool.</p>
</p>

`sot` is a Command-line System Obervation Tool in the spirit of [top](<https://en.wikipedia.org/wiki/Top_(software)>). It displays various interesting system stats and graphs them. Works on all operating systems.

[![PyPI Downloads](https://static.pepy.tech/badge/sot/month)](https://pypi.org/project/sot/) [![Open Source](https://img.shields.io/badge/open-source-brightgreen)](https://github.com/anistark/sot) [![Contributors](https://img.shields.io/github/contributors/anistark/sot)](https://github.com/anistark/sot/graphs/contributors) ![maintenance-status](https://img.shields.io/badge/maintenance-actively--developed-brightgreen.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Installation

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

### Using uv (Recommended)

Install and run with [`uv`](https://github.com/astral-sh/uv):

<!--pytest-codeblocks: skip-->

```sh
uv tool install sot
```

### Using pipx

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

### Using RPM Package (Experimental - RHEL/CentOS/Fedora)

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

### Disk

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

---

For all options, see

<!--pytest-codeblocks:skipif(sys.version_info < (3, 10))-->

```sh
sot -H
```

<!--pytest-codeblocks: expected-output-->

```
usage: sot [--help] [--version] [--log LOG] [--net NET]

Command-line System Obervation Tool ≈

options:
  --help, -H     Show this help message and exit.
  --version, -V  Display version information
  --log, -L LOG  Debug log file
  --net, -N NET  Network interface to display (default: auto)
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
