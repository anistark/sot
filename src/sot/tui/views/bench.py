"""Bench: pick a disk, run the benchmarks, export the results."""

from __future__ import annotations

import tempfile
import time
from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical

from ..._helpers import iops_fmt, latency_fmt, sizeof_fmt, throughput_fmt
from ..._theme import theme
from ...bench.cli import get_physical_disks, volume_label, write_results_json
from ...bench.core import BenchmarkResult, DiskBenchmark, get_bench_cache_dir
from ...widgets.base_widget import BaseWidget
from .. import keymap, refresh
from ..components.table import SotTable, cell
from ..screen import SotScreen

TESTS = (
    ("Sequential Read", "sequential_read_test"),
    ("Sequential Write", "sequential_write_test"),
    ("Random Read IOPS", "random_read_test"),
    ("Random Write IOPS", "random_write_test"),
)
MIN_DURATION, MAX_DURATION = 1.0, 60.0


class DiskTable(SotTable):
    BINDINGS = [*keymap.LIST, Binding("enter", "run", "Run", id="sot.bench.run")]

    def __init__(self, **kwargs):
        super().__init__("Disks", **kwargs)
        self.disks: list[dict] = []

    def on_mount(self) -> None:
        for key, label in (
            ("disk", "Disk"),
            ("volume", "Volume"),
            ("total", "Total"),
            ("free", "Free"),
            ("parts", "Partitions"),
        ):
            self.add_column(label, key=key)
        self.reload()

    def reload(self) -> None:
        c = theme().colors
        disks = sorted(
            get_physical_disks(), key=lambda d: d["free_bytes"], reverse=True
        )
        if self.filter_text:
            text = self.filter_text.lower()
            disks = [d for d in disks if text in self._text(d)]
        self.disks = disks
        self.set_rows(
            [
                (
                    d["disk_id"],
                    (
                        cell(d["disk_id"], c.accent),
                        cell(volume_label(d["largest_partition"]["mountpoint"])),
                        cell(sizeof_fmt(d["total_bytes"], fmt=".1f"), justify="right"),
                        cell(sizeof_fmt(d["free_bytes"], fmt=".1f"), c.ok, "right"),
                        cell(len(d["partitions"]), c.muted, "right"),
                    ),
                )
                for d in disks
            ]
        )

    def _text(self, disk: dict) -> str:
        mounts = " ".join(p["mountpoint"] for p in disk["partitions"])
        return f"{disk['disk_id']} {mounts}".lower()

    def selected_disk(self) -> dict | None:
        return next((d for d in self.disks if d["disk_id"] == self.selected_row), None)

    def action_run(self) -> None:
        if (disk := self.selected_disk()) is not None and isinstance(
            self.screen, BenchScreen
        ):
            self.screen.start(disk)


class ResultsTable(SotTable):
    def __init__(self, **kwargs):
        super().__init__("Results", **kwargs)

    def on_mount(self) -> None:
        self.add_columns("Test", "Throughput / IOPS", "Avg", "p95", "p99", "Duration")
        self.reload()

    def reload(self) -> None:
        screen = self.screen
        results = screen.results if isinstance(screen, BenchScreen) else []
        c = theme().colors
        rows = []
        for result in results:
            if result.is_error():
                values = (cell(result.test_name, c.danger), cell("Error", c.danger))
                rows.append((result.test_name, values + (cell("-"),) * 4))
                continue
            if result.throughput_mbps is not None:
                metric = throughput_fmt(result.throughput_mbps)
            elif result.iops is not None:
                metric = iops_fmt(result.iops)
            else:
                metric = "-"
            rows.append(
                (
                    result.test_name,
                    (
                        cell(result.test_name, c.ok),
                        cell(metric, c.primary),
                        cell(latency_fmt(result.avg_latency_ms), c.info),
                        cell(latency_fmt(result.p95_latency_ms), c.info),
                        cell(latency_fmt(result.p99_latency_ms), c.info),
                        cell(latency_fmt(result.duration_ms)),
                    ),
                )
            )
        self.set_rows(rows)


class BenchStatus(BaseWidget):
    DEFAULT_CSS = """
    BenchStatus {
        height: 7;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(title="Run", **kwargs)

    def on_mount(self) -> None:
        self.every(refresh.BENCH_PROGRESS, self.redraw)
        self.redraw()

    def redraw(self) -> None:
        screen = self.screen
        if not isinstance(screen, BenchScreen):
            return
        t = theme()
        c = t.colors
        text = Text()
        text.append(f"Duration per test: {screen.duration:.0f}s", style=c.text)
        text.append("  (+/- to change)\n", style=c.muted)
        if screen.running is not None:
            done = len(screen.results)
            current = TESTS[min(done, len(TESTS) - 1)][0]
            elapsed = time.monotonic() - screen.started
            text.append(f"{screen.running['disk_id']}: {current}\n", style=c.accent)
            text.append_text(t.meter(done / len(TESTS), 30, c.ok))
            text.append(f"  {done}/{len(TESTS)}  {elapsed:.0f}s", style=c.muted)
            if screen.cancelling:
                text.append("\ncancelling after this test…", style=c.warn)
        elif screen.results:
            text.append("Finished. e exports JSON.", style=c.ok)
        else:
            text.append("Pick a disk and press enter.", style=c.muted)
        self.update_panel_content(text)


class BenchScreen(SotScreen):
    MODE = "bench"

    BINDINGS = [
        Binding("plus,equals_sign", "longer", "+1s", id="sot.bench.longer"),
        Binding("minus", "shorter", "-1s", id="sot.bench.shorter"),
        Binding("e", "export", "Export", id="sot.bench.export"),
    ]

    DEFAULT_CSS = """
    BenchScreen #bench-left {
        width: 62;
    }

    BenchScreen #disk-table {
        height: 1fr;
    }

    BenchScreen #results-table {
        width: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.duration = 10.0
        self.results: list[BenchmarkResult] = []
        self.running: dict | None = None
        self.finished_disk: dict | None = None
        self.cancelling = False
        self.started = 0.0

    def compose_view(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="bench-left"):
                yield DiskTable(id="disk-table")
                yield BenchStatus(id="bench-status")
            yield ResultsTable(id="results-table")

    def on_mount(self) -> None:
        self.duration = float(getattr(self.app, "bench_duration", self.duration))
        self.query_one("#disk-table").focus()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "back" and self.running is not None:
            return not self.cancelling
        if action == "export":
            return bool(self.results) and self.running is None
        return super().check_action(action, parameters)

    def _changed(self) -> None:
        self.query_one(BenchStatus).redraw()
        self.query_one(ResultsTable).reload()
        self.refresh_bindings()

    def action_longer(self) -> None:
        self.duration = min(MAX_DURATION, self.duration + 1)
        self._changed()

    def action_shorter(self) -> None:
        self.duration = max(MIN_DURATION, self.duration - 1)
        self._changed()

    async def action_back(self) -> None:
        if self.running is not None:
            self.cancelling = True
            self._changed()
        else:
            await super().action_back()

    def start(self, disk: dict) -> None:
        if self.running is not None:
            return
        try:
            with tempfile.NamedTemporaryFile(
                dir=str(get_bench_cache_dir()), prefix="sot_bench_"
            ):
                pass
        except OSError as e:
            self.notify(f"Cannot write to the bench cache: {e}", severity="error")
            return
        self.results, self.running, self.cancelling = [], disk, False
        self.started = time.monotonic()
        self._changed()
        self.run_benchmark(disk, self.duration)

    @work(thread=True, exclusive=True, group="bench")
    def run_benchmark(self, disk: dict, duration: float) -> None:
        mountpoint = disk["largest_partition"]["mountpoint"]
        bench = DiskBenchmark(disk["disk_id"], mountpoint, duration_seconds=duration)
        for _, method in TESTS:
            if self.cancelling:
                break
            result = getattr(bench, method)()
            self.app.call_from_thread(self._add_result, result)
        self.app.call_from_thread(self._finished)

    def _add_result(self, result: BenchmarkResult) -> None:
        self.results.append(result)
        self._changed()

    def _finished(self) -> None:
        cancelled = self.cancelling
        self.finished_disk, self.running, self.cancelling = self.running, None, False
        self._changed()
        if cancelled:
            self.notify("Benchmark cancelled", severity="warning")
        else:
            self.notify("Benchmark finished")

    def action_export(self) -> None:
        disk = self.finished_disk
        if disk is None or not self.results:
            return
        slug = disk["disk_id"].strip("/").replace("/", "-")
        path = Path.cwd() / f"sot-bench-{slug}-{datetime.now():%Y%m%d-%H%M%S}.json"
        try:
            write_results_json(self.results, disk, str(path))
        except OSError as e:
            self.notify(f"Export failed: {e}", severity="error")
            return
        self.notify(f"Saved {path}")
