"""Overview: the dashboard grid."""

from __future__ import annotations

from textual.app import ComposeResult

from ..._gpu import has_gpu
from ...widgets import (
    CPUWidget,
    DiskWidget,
    GpuWidget,
    HealthScoreWidget,
    InfoWidget,
    MemoryWidget,
    NetworkConnectionsWidget,
    NetworkWidget,
    SotLogoWidget,
)
from ..components.process_table import COMPACT, OverviewProcessTable
from ..screen import SotScreen


class OverviewScreen(SotScreen):
    MODE = "overview"

    DEFAULT_CSS = """
    OverviewScreen #body {
        layout: grid;
        grid-size: 3;
        grid-columns: 35fr 20fr 45fr;
        grid-rows: 1 1fr 1.2fr 1.1fr;
    }

    OverviewScreen #info-line {
        column-span: 3;
    }

    OverviewScreen #procs-list {
        row-span: 2;
    }
    """

    def compose_view(self) -> ComposeResult:
        app = self.app
        yield InfoWidget(id="info-line")
        yield CPUWidget(id="cpu-widget")
        yield HealthScoreWidget(id="health-widget")
        yield OverviewProcessTable(COMPACT, id="procs-list")
        yield MemoryWidget(id="mem-widget")
        # Live GPU stats when a GPU is detected, otherwise the SOT animation.
        yield (
            GpuWidget(id="gpu-widget") if has_gpu() else SotLogoWidget(id="sot-widget")
        )
        yield DiskWidget(getattr(app, "disk_mountpoint", None), id="disk-widget")
        yield NetworkConnectionsWidget(id="connections-widget")
        yield NetworkWidget(getattr(app, "net_interface", None), id="net-widget")

    def on_mount(self) -> None:
        self.focus_processes()
        self.size_memory_row()

    def rebuilt(self) -> None:
        self.size_memory_row()

    def focus_processes(self) -> None:
        self.query_one("#procs-list").focus()

    def size_memory_row(self) -> None:
        # Memory graphs have a fixed height; size their grid row to match.
        mem = self.query_one("#mem-widget", MemoryWidget)
        body = self.query_one("#body")
        body.styles.grid_rows = f"1 1fr {mem.panel_height} 1.1fr"
