---
title: sot ps
description: Opens the Processes view (`2`) - the process table, listening ports and running dev environments.
cmds: [ps]
---

## What it shows

- **Processes**: a scrollable table with mouse support. Click a column header to sort, or press `o`
- **Listening ports**: open from the overview too, with `Enter` on the connections panel
- **Dev environments**: running Node, Python, Docker, Ruby, Go and Rust environments

`Enter` or a double-click opens a detail drawer with live details for the process, port or dev environment, following the cursor.

## Keys

| Key | Action |
| --- | --- |
| `/` | Filter the focused list by name, PID, user or command; `Esc` clears it |
| `o` | Sort: in the process table pick a column with `←` `→` and flip with `Enter`; in port and dev lists `o` cycles the column and `s` flips |
| `x` / `t` | Kill / terminate the selected process (asks first) |
| `n` | Show or hide the I/O and connection columns |
| `Enter` | Open details |
| `Ctrl+P` | Command palette: jump to a process, kill, terminate or copy its PID |

## Connections without root

On macOS without `sudo`, the connections panel shows your own processes' sockets.
