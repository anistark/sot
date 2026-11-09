---
title: sot info
description: Prints a system summary next to an OS logo, like neofetch. The System view (`4`) shows the same, kept live.
cmds: [info]
---

## What it prints

Host, model, serial, OS, kernel, firmware, desktop and window manager, shell, terminal, chip (with performance/efficiency cores), GPU, memory, displays, uptime and battery, next to an ASCII logo for macOS, Windows, Ubuntu, Debian, Fedora, RHEL, Arch, Manjaro, Pop!_OS, CentOS or a generic Tux.

{% prompt "sot info" %}

```
                  ,MMMM.            Host        -  john@macbook.local
                .MMMMMM             Model       -  MacBook Pro
                MMMMM,              Identifier  -  MacBookPro18,1
      .;MMMMM:' MMMMMMMMMM;.
    MMMMMMMMMMMMNWMMMMMMMMMMM:      OS          -  macOS 14.5.0 Sonoma
  .MMMMMMMMMMMMMMMMMMMMMMMMWM.      Kernel      -  23.5.0
  MMMMMMMMMMMMMMMMMMMMMMMMM.        Shell       -  zsh
 ;MMMMMMMMMMMMMMMMMMMMMMMM:         Terminal    -  iTerm.app (3.5.2)
 :MMMMMMMMMMMMMMMMMMMMMMMM:
 .MMMMMMMMMMMMMMMMMMMMMMMMM.        Chip        -  Apple M1 Pro (8P + 2E cores)
  MMMMMMMMMMMMMMMMMMMMMMMMMMM.      GPU         -  Apple M1 Pro (16 cores)
   .MMMMMMMMMMMMMMMMMMMMMMMMMM.     Memory      -  8 GiB / 32 GiB
     MMMMMMMMMMMMMMMMMMMMMMMM
      ;MMMMMMMMMMMMMMMMMMMM.        Uptime      -  12d 4h 23m
        .MMMM,.    .MMMM,.          Battery     -  87% & Discharging
```

## In the app

Press `4` in any view for the System view: what `sot info` prints, with uptime, memory and battery kept live.
