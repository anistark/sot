"""Overview: the dashboard grid."""

from __future__ import annotations

from textual.app import ComposeResult

from ..._config import remember_zoom
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
from .. import keymap, zoom
from ..components.process_table import COMPACT, OverviewProcessTable
from ..screen import SotScreen

INFO_ROWS = 1
# Rows the CPU and the disk and network panels need before they clip.
MIN_TOP, MIN_BOTTOM = 9, 14


class OverviewScreen(SotScreen):
    MODE = "overview"
    BINDINGS = [*keymap.ZOOM]

    DEFAULT_CSS = """
    OverviewScreen #body {
        layout: grid;
        grid-size: 3;
        grid-columns: 35fr 20fr 45fr;
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
        self.size_rows()

    def rebuilt(self) -> None:
        self.size_rows()

    def focus_processes(self) -> None:
        self.query_one("#procs-list").focus()

    def _rows(self) -> tuple[int, int, int]:
        """Memory and bottom row heights, and rows left for the CPU row."""
        mem = self.query_one("#mem-widget", MemoryWidget).panel_height
        spare = self.query_one("#body").size.height - INFO_ROWS - mem
        weight = zoom.bottom_weight()
        bottom = max(MIN_BOTTOM, round(spare * weight / (1 + weight)))
        return mem, bottom, spare - bottom

    def size_rows(self) -> None:
        mem, bottom, _ = self._rows()
        self.query_one("#body").styles.grid_rows = f"{INFO_ROWS} 1fr {mem} {bottom}"

    def on_resize(self) -> None:
        self.size_rows()

    def action_zoom(self, step: int) -> None:
        before = zoom.level
        if zoom.set_level(before + step) == before:
            limit = "in" if step > 0 else "out"
            self.notify(f"Zoomed all the way {limit}", timeout=2)
            return
        if step > 0 and self._rows()[2] < MIN_TOP:
            zoom.set_level(before)
            self.notify("No room to zoom in, make the window taller", timeout=2)
            return
        remember_zoom(zoom.level)
        mem = self.query_one("#mem-widget", MemoryWidget)
        mem.fit_zoom()
        mem.refresh_table()
        self.size_rows()
        self.notify(f"Zoom {zoom.label()}", timeout=2)
