---
layout: layouts/doc.njk
title: Usage
description: One app with six views. Every command that opens a screen opens the same app on a different view.
window: usage
---

## Commands

| Command | What it does |
| --- | --- |
| [`sot`](/commands/) | Live dashboard: CPU, memory, GPU, disk, network, connections and processes |
| [`sot ps`](/commands/ps/) | Processes, listening ports and running dev environments |
| [`sot disk`](/commands/disk/) | Every physical disk with its partitions, usage and I/O |
| `sot disk --list` | The same as a static table, then exits (pipe-friendly) |
| [`sot info`](/commands/info/) | System summary with an OS logo, like neofetch |
| [`sot bench`](/commands/bench/) | Disk benchmark: sequential throughput, random IOPS and latency |
| [`sot clean`](/commands/clean/) | Find and remove caches, logs, temp files and build output |
| [`sot update`](/commands/update/) | Move to the newest minor or patch release of your major version |
| `sot upgrade` | Move to the newest release, major versions included |
| [`sot --keys`](/keys/) | List every key binding and its id |
| [`sot --config-path`](/configuration/) | Show where the config file lives, with a commented template |

Everything that opens a screen opens the same app on a different view, so you can hop between them with the number keys.

## Views

| Key | View | Shows |
| --- | --- | --- |
| `1` | Overview | CPU per core, health score, top processes, memory, GPU, disk, network and socket graphs |
| `2` | Processes | Process table, listening ports and dev environments (Node, Python, Docker, Ruby, Go, Rust) |
| `3` | Disks | Physical disks and partitions, usage bars, read/write stats |
| `4` | System | What `sot info` prints, with uptime, memory and battery kept live |
| `5` | Bench | Pick a disk and watch each benchmark finish |
| `6` | Clean | Scan, tick what to remove, dry run or clean |

You can also click the tabs in the header. Each view keeps its selection, sort and scroll while you're elsewhere.

## Highlights

- **Drill down**: `Enter` on an overview panel opens that process, disk or the ports list in its own view; `Esc` comes back
- **Detail drawer**: `Enter` or double-click in a list opens live details that follow the cursor
- **Filter**: `/` filters the focused list by name, PID, user or command
- **Command palette**: `Ctrl+P` jumps to a view, process or volume, kills, terminates or copies a PID, and switches theme
- **Sort anywhere**: click a column header, or press `o`
- **Zoom the overview**: `+` for taller graphs, `-` for more process rows (remembered)
- **GPU stats** on Apple Silicon (`ioreg`, no sudo), NVIDIA (`nvidia-smi`) and AMD (`rocm-smi`, best effort)
- **Connections without root**: on macOS without `sudo` the panel shows your own processes' sockets

Every key is listed in [keys](/keys/).

## Themes

Two colour themes: `classic` follows your terminal's colours and `cyberpunk` is neon. Pick one with `--theme` (`-T`), set `SOT_THEME=cyberpunk` as the default, or switch while running with `Ctrl+P` → Theme; graphs and selections are kept and the choice is remembered.

```sh
sot -T cyberpunk
```

(This site has a light and a dark theme instead. It follows your system; press `t` to switch.)

## Overview options

| Flag | What it does |
| --- | --- |
| `--net`, `-N` | Network interface for the overview, e.g. `sot -N en0` (default: auto-detect) |
| `--disk`, `-D` | Volume for the overview, e.g. `sot -D /Volumes/External`; with no value, pick one in sot |
| `--log`, `-L` | Write a debug log to this file |

The full list is in [`sot --help`](/commands/).
