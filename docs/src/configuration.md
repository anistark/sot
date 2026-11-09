---
layout: layouts/doc.njk
title: Configuration
description: Optional. sot runs without a config file; add one to change the defaults.
window: config
---

## Where it lives

`~/.config/sot/config.toml`, following `$XDG_CONFIG_HOME`. `sot --config-path` prints the path, and a commented template when the file doesn't exist yet:

{% prompt "sot --config-path" %}
{% configTemplate %}

## Example

```toml
theme = "cyberpunk"          # classic, cyberpunk
default_view = "processes"   # overview, processes, disks, system, bench, clean
net = "en0"                  # network interface on the overview
disk = "/"                   # mountpoint on the overview

[refresh]                    # seconds
cpu = 1.0
processes = 2.0

[clean]
every = "daily"              # how often `sot clean -d` runs: hourly, daily, weekly, monthly

[keymap]                     # binding id = keys, see `sot --keys`
"sot.process.kill" = "ctrl+k"
"sot.view.processes" = "p"
```

## Settings

| Key | What it sets |
| --- | --- |
| `theme` | Colour theme: `classic` or `cyberpunk` |
| `default_view` | The view `sot` opens on: `overview`, `processes`, `disks`, `system`, `bench` or `clean` |
| `net` | Network interface on the overview |
| `disk` | Mountpoint on the overview |
| `[refresh]` | How often `cpu` and `processes` refresh, in seconds |
| `[clean]` `every` | How often [`sot clean -d`](/commands/clean/#on-a-schedule) runs: `hourly`, `daily`, `weekly` or `monthly` |
| `[keymap]` | Binding id = keys; the ids are in [keys](/keys/#every-binding) |

Every key is optional and invalid values are reported and ignored.

## What wins

Flags win over `SOT_THEME`, which wins over the config file. A schedule changed in the config applies the next time you run `sot clean -d`.
