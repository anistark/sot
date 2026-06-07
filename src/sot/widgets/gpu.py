"""
GPU Widget

Displays real-time GPU utilization with a history graph, plus memory, temperature,
power draw, and a utilization breakdown when the platform exposes them. Only the
metrics that are actually available are shown.
"""

from __future__ import annotations

from rich.console import Group
from rich.text import Text

from .._gpu import GpuSample, read_gpu
from .._helpers import sizeof_fmt
from ..braille_stream import BrailleStream
from .base_widget import BaseWidget

# Initial graph size; widths are recomputed on resize.
_GRAPH_WIDTH = 20
_GRAPH_HEIGHT = 6
_LABEL_WIDTH = 7


def _metric_line(label: str, value: str, color: str) -> Text:
    """Render a single ``label   value`` metric row with an aligned label."""
    line = Text()
    line.append(f"{label:<{_LABEL_WIDTH}}", style="bright_white")
    line.append(value, style=color)
    return line


class GpuWidget(BaseWidget):
    """GPU widget showing utilization, memory, temperature, and power."""

    def __init__(self, **kwargs):
        super().__init__(title="GPU", **kwargs)

    def on_mount(self):
        self.util_stream = BrailleStream(_GRAPH_WIDTH, _GRAPH_HEIGHT, 0.0, 100.0)

        sample = read_gpu()
        if sample is not None and sample.name:
            title = f"[b]GPU[/] - {sample.name}"
            if sample.cores:
                title += f" · {sample.cores} cores"
            self.panel.title = title

        self.collect_data()
        self.set_interval(2.0, self.collect_data)

    def _memory_text(self, sample: GpuSample) -> str:
        used = sizeof_fmt(sample.mem_used, fmt=".1f")
        if sample.mem_total:
            return f"{used} / {sizeof_fmt(sample.mem_total, fmt='.1f')}"
        return used

    def _metric_rows(self, sample: GpuSample) -> list[Text]:
        """Build a metric row per available reading (skips anything missing)."""
        rows: list[Text] = []
        if sample.mem_used is not None:
            rows.append(_metric_line("Mem", self._memory_text(sample), "sky_blue3"))
        if sample.mem_alloc is not None:
            rows.append(
                _metric_line("Alloc", sizeof_fmt(sample.mem_alloc, fmt=".1f"), "cyan")
            )
        if sample.temp_c is not None:
            rows.append(
                _metric_line("Temp", f"{round(sample.temp_c)}°C", "slate_blue1")
            )
        if sample.power_w is not None:
            rows.append(_metric_line("Power", f"{sample.power_w:.0f} W", "aquamarine3"))
        if sample.renderer_util_percent is not None:
            rows.append(
                _metric_line(
                    "Render", f"{round(sample.renderer_util_percent)}%", "yellow"
                )
            )
        if sample.tiler_util_percent is not None:
            rows.append(
                _metric_line(
                    "Tiler", f"{round(sample.tiler_util_percent)}%", "dark_orange"
                )
            )
        return rows

    def _util_graph(self, sample: GpuSample) -> Text:
        # Fall back to 0 so the history keeps scrolling even if util is missing.
        self.util_stream.add_value(sample.util_percent or 0.0)
        lines = self.util_stream.graph
        if sample.util_percent is not None:
            value_str = f"{sample.util_percent:5.1f}%"
            if len(lines[0]) >= len(value_str):
                lines = [lines[0][: -len(value_str)] + value_str] + lines[1:]
        return Text.from_markup("[yellow]" + "\n".join(lines) + "[/]")

    def collect_data(self):
        sample = read_gpu()
        if sample is None:
            self.update_panel_content(Text("No GPU data available", style="dim"))
            return

        graph = self._util_graph(sample)
        self.update_panel_content(Group(graph, Text(""), *self._metric_rows(sample)))

    async def on_resize(self, event):
        graph_width = max(10, self.size.width - 4)
        self.util_stream.reset_width(graph_width)
