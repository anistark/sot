---
title: sot
description: Without a subcommand, sot opens the live dashboard. Subcommands open their own view, or print and exit when given flags or when not run in a terminal.
cmds: [sot]
---

## Commands

| Command | Opens | Without the TUI |
| --- | --- | --- |
| `sot` | Overview (`1`) | |
| [`sot ps`](/commands/ps/) | Processes (`2`) | |
| [`sot disk`](/commands/disk/) | Disks (`3`) | `--list` prints a table |
| [`sot info`](/commands/info/) | | Always prints; the System view is `4` |
| [`sot bench`](/commands/bench/) | Bench (`5`) | `--disk` or `--output` run it without the TUI |
| [`sot clean`](/commands/clean/) | Clean (`6`) | `--dry-run`, `--daemon` and `--scheduled` print |
| [`sot update`](/commands/update/), `sot upgrade` | | Always prints |

Everything that opens a screen opens the same app, so the number keys move between views from any of them.

## Options

| Flag | What it does |
| --- | --- |
| `--theme`, `-T` | Colour theme: `classic` (follows your terminal) or `cyberpunk` (neon) |
| `--net`, `-N` | Network interface for the overview, e.g. `sot -N en0` (default: auto-detect) |
| `--disk`, `-D` | Volume for the overview, e.g. `sot -D /Volumes/External`; with no value, pick one in sot |
| `--log`, `-L` | Write a debug log to this file |
| `--keys` | List every key binding and its id, for the [`[keymap]`](/keys/#remap-a-key) config table |
| `--config-path` | Show where the [config file](/configuration/) lives, with a commented template |
| `--version`, `-V` | Show the version |
| `--help`, `-H` | Show help (`sot <command> -h` for a command's flags) |

## Theme

Switch theme while running with `Ctrl+P` → Theme; graphs and selections are kept and the choice is remembered. `SOT_THEME=cyberpunk` sets the default. Flags win over `SOT_THEME`, which wins over the config file.

```sh
SOT_THEME=cyberpunk sot
sot --theme classic
```
