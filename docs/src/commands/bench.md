---
title: sot bench
description: A disk benchmark - sequential read and write throughput, random read and write IOPS, and latency.
cmds: [bench]
---

## What it measures

Four tests on the disk you pick: sequential read, sequential write, random read IOPS and random write IOPS, each with min/avg/max and p50/p95/p99 latency.

```sh
sot bench                                    # pick a disk in the Bench view
sot bench --disk disk3 --duration 5          # no prompt, 5 s per test (default 10)
sot bench --disk / --output results.json     # save results as JSON
```

`--disk` takes a disk id (`disk3`, `/dev/sda`) or a mountpoint and skips the prompt. With `--disk` or `--output`, or when it isn't run in a terminal, the benchmark runs without the app and prints its results.

## In the Bench view

| Key | Action |
| --- | --- |
| `Enter` | Run |
| `+` / `-` | Longer / shorter tests, one second at a time |
| `e` | Export the results as JSON |
| `Esc` | Cancel after the current test |
