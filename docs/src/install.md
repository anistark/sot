---
layout: layouts/doc.njk
title: Install
description: sot needs Python 3.10 or newer and runs on macOS, Linux and Windows.
window: install
---

## One line

On macOS and Linux, the install script installs Python 3.10+ and pipx if they're missing, then sot:

```sh
curl -fsSL https://raw.githubusercontent.com/anistark/sot/main/install.sh | bash
```

## Package managers

```sh
uv tool install sot                 # uv
pipx install sot                    # pipx
brew install anistark/tools/sot     # Homebrew
```

On Windows, use `uv` or `pipx`; the install script doesn't run there.

## Update

`sot update` takes minor and patch releases and `sot upgrade` takes major ones too. Both work out how sot was installed and go through that tool; add `--dry-run` to see what would run. On Windows they print the command instead, since a running program can't replace itself. See [`sot update`](/commands/update/).

## DEB and RPM packages

Experimental. Download the package from the [releases page](https://github.com/anistark/sot/releases/latest):

```sh
sudo dpkg -i sot-*.deb && sudo apt-get install -f    # Debian, Ubuntu
sudo rpm -ivh sot-*.rpm                              # RHEL, CentOS, Fedora
```

## From source

```sh
git clone https://github.com/anistark/sot.git && cd sot
uv pip install --system .    # or: pipx install .
```

## Verify a release

PyPI releases are published from GitHub Actions with [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) and carry [PEP 740 attestations](https://docs.pypi.org/attestations/). To verify a release file:

```sh
uvx pypi-attestations verify pypi --repository https://github.com/anistark/sot pypi:sot-<version>-py3-none-any.whl
```

## Uninstall

Remove it with the tool you installed it with:

```sh
uv tool uninstall sot
pipx uninstall sot
brew uninstall sot
```
