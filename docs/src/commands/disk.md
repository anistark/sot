---
title: sot disk
description: Opens the Disks view (`3`) - every physical disk with its partitions, usage bars and read/write stats.
cmds: [disk]
---

## In the terminal

```sh
sot disk           # the Disks view
sot disk --list    # the same as a static table, then exits
```

`--list` (`-l`) prints disks and partitions as a plain table instead of opening the app, so it's pipe-friendly.

## On the overview

The overview shows one volume. Pick it with `--disk` (`-D`), or give no value to choose one in sot:

```sh
sot -D /Volumes/External
sot -D
```

Set a default with `disk` in the [config file](/configuration/). From the overview, `Enter` on the disk panel opens that volume in the Disks view; `Esc` comes back.
