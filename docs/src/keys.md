---
layout: layouts/doc.njk
title: Keys
description: "`?` in sot shows the keys for the focused panel. Every binding can be remapped in the config."
window: usage
---

## Everyday keys

| Key | Action |
| --- | --- |
| `1`-`6` | Switch view |
| `Tab` / `Shift+Tab` | Next / previous panel |
| `↑` `↓` or `k` `j` | Move |
| `PgUp` `PgDn` (`Ctrl+U` `Ctrl+D`), `Home` `End` (`g` `G`) | Page, first, last |
| `Enter` | Open details, or drill down from the overview |
| `Esc` | Close, clear the filter, or go back |
| `/` | Filter |
| `o` | Sort: in process tables pick a column with `←` `→` and flip with `Enter`; in port and dev lists `o` cycles the column and `s` flips |
| `x` / `t` | Kill / terminate the selected process (asks first) |
| `n` | Show or hide the I/O and connection columns |
| `+` / `-` | Overview zoom |
| `r` | Refresh |
| `Ctrl+P` | Command palette |
| `q` | Quit |

The Bench and Clean views have their own keys; see [`sot bench`](/commands/bench/) and [`sot clean`](/commands/clean/).

## Remap a key

Every binding has an id. Put the ones you want to change under `[keymap]` in the [config file](/configuration/), mapping the id to the new keys:

```toml
[keymap]
"sot.process.kill" = "ctrl+k"
"sot.view.processes" = "p"
```

## Every binding

`sot --keys` prints every binding with its id. This is its output for sot {{ sot.version }}:

{% prompt "sot --keys" %}
{% keysTable %}
