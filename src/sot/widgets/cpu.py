"""
CPU Widget

Displays CPU usage, temperature, and frequency information with per-core breakdown.
"""

import re
from pathlib import Path

import psutil
from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .base_widget import BaseWidget
from ..braille_stream import BrailleStream


def val_to_color(val: float, minval: float, maxval: float) -> str:
    t = (val - minval) / (maxval - minval)
    k = round(t * 3)
    return {0: "yellow", 1: "dark_orange", 2: "sky_blue3", 3: "aquamarine3"}[k]


def chunks(lst, n):
    """Split list into chunks of size n."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def transpose(lst):
    """Transpose a list of lists."""
    return list(map(list, zip(*lst)))


def flatten(lst):
    """Flatten a list of lists."""
    return [item for sublist in lst for item in sublist]


def get_cpu_model():
    """Get CPU model name."""
    try:
        # On Linux, read from /proc/cpuinfo
        with open("/proc/cpuinfo") as f:
            content = f.read()
        m = re.search(r"model name\t: (.*)", content)
        model_name = m.group(1)
    except Exception:
        import cpuinfo
        model_name = cpuinfo.get_cpu_info()["brand_raw"]
    return model_name


def get_current_temps():
    """Get current CPU temperatures."""
    # First try manually reading the temperatures
    for key in ["coretemp", "k10temp"]:
        path = Path(f"/sys/devices/platform/{key}.0/hwmon/hwmon6/")
        if not path.is_dir():
            continue

        k = 1
        temps = []
        while True:
            file = path / f"temp{k}_input"
            if not file.exists():
                break
            with open(file) as f:
                content = f.read()
            temps.append(int(content) / 1000)
            k += 1

        return temps

    # Try psutil.sensors_temperatures()
    try:
        temps = psutil.sensors_temperatures()
    except AttributeError:
        return None
    else:
        # coretemp: intel, k10temp: amd
        for key in ["coretemp", "k10temp"]:
            if key not in temps:
                continue
            return [t.current for t in temps[key]]

    return None


def get_current_freq():
    """Get current CPU frequency."""
    # Try reading from sys filesystem first
    candidates = [
        "/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq",
        "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            with open(candidate) as f:
                content = f.read()
            return int(content) / 1000

    try:
        cpu_freq = psutil.cpu_freq().current
    except Exception:
        return None

    return cpu_freq


class CPUWidget(BaseWidget):
    """CPU widget displaying usage, temperature, and frequency information."""

    def __init__(self, **kwargs):
        super().__init__(title="CPU", **kwargs)

    def on_mount(self):
        self.width = 0
        self.height = 0

        self.num_cores = psutil.cpu_count(logical=False)
        num_threads = psutil.cpu_count(logical=True)

        assert num_threads % self.num_cores == 0
        self.core_threads = transpose(list(chunks(range(num_threads), self.num_cores)))

        self.cpu_total_stream = BrailleStream(50, 7, 0.0, 100.0)

        self.thread_load_streams = [
            BrailleStream(10, 1, 0.0, 100.0)
            for _ in range(num_threads)
        ]

        temps = get_current_temps()

        if temps is None:
            self.has_cpu_temp = False
            self.has_core_temps = False
        else:
            self.has_cpu_temp = len(temps) > 0
            self.has_core_temps = len(temps) == 1 + self.num_cores

            temp_low = 30.0
            temp_high = 100.0

            if self.has_cpu_temp:
                self.temp_total_stream = BrailleStream(
                    50, 7, temp_low, temp_high, flipud=True
                )

            if self.has_core_temps:
                self.core_temp_streams = [
                    BrailleStream(5, 1, temp_low, temp_high)
                    for _ in range(self.num_cores)
                ]

        self.has_fan_rpm = False
        try:
            fan_current = list(psutil.sensors_fans().values())[0][0].current
        except (AttributeError, IndexError):
            pass
        else:
            self.has_fan_rpm = True
            fan_low = 0
            if fan_current == 65535:
                fan_current = 1
            fan_high = max(fan_current, 1)
            self.fan_stream = BrailleStream(50, 1, fan_low, fan_high)

        box_title = ", ".join(
            [
                f"{self.num_cores} core" + ("s" if self.num_cores > 1 else ""),
                f"{num_threads} thread" + ("s" if num_threads > 1 else ""),
            ]
        )
        self.info_box = Panel(
            "",
            title=box_title,
            title_align="left",
            subtitle=None,
            subtitle_align="left",
            border_style="bright_black",
            box=box.SQUARE,
            expand=False,
        )

        try:
            cpu_model = get_cpu_model()
            self.panel.title = f"[b]CPU[/] - {cpu_model}"
        except:
            self.panel.title = "[b]CPU[/]"

        self.collect_data()
        self.set_interval(2.0, self.collect_data)

    def collect_data(self):
        # CPU loads
        self.cpu_total_stream.add_value(psutil.cpu_percent())
        
        load_per_thread = psutil.cpu_percent(percpu=True)
        assert isinstance(load_per_thread, list)
        for stream, load in zip(self.thread_load_streams, load_per_thread):
            stream.add_value(load)

        # CPU temperatures
        if self.has_cpu_temp or self.has_core_temps:
            temps = get_current_temps()
            assert temps is not None

            if self.has_cpu_temp:
                self.temp_total_stream.add_value(temps[0])

            if self.has_core_temps:
                for stream, temp in zip(self.core_temp_streams, temps[1:]):
                    stream.add_value(temp)

        lines_cpu = self.cpu_total_stream.graph
        current_val_string = f"{self.cpu_total_stream.values[-1]:5.1f}%"
        lines0 = lines_cpu[0][: -len(current_val_string)] + current_val_string
        lines_cpu = [lines0] + lines_cpu[1:]
        
        cpu_total_graph = "[yellow]" + "\n".join(lines_cpu) + "[/]\n"
        
        if self.has_cpu_temp:
            lines_temp = self.temp_total_stream.graph
            current_val_string = f"{round(self.temp_total_stream.values[-1]):3d}°C"
            lines0 = lines_temp[-1][: -len(current_val_string)] + current_val_string
            lines_temp = lines_temp[:-1] + [lines0]
            cpu_total_graph += "[slate_blue1]" + "\n".join(lines_temp) + "[/]"

        self._refresh_info_box(load_per_thread)

        t = Table(expand=True, show_header=False, padding=0, box=None)
        t.add_column("graph", no_wrap=True, ratio=1)
        t.add_column("box", no_wrap=True, justify="left", vertical="middle")
        t.add_row(cpu_total_graph, self.info_box)

        if self.has_fan_rpm:
            fan_current = list(psutil.sensors_fans().values())[0][0].current

            if fan_current == 65535:
                fan_current = self.fan_stream.maxval

            if fan_current > self.fan_stream.maxval:
                self.fan_stream.maxval = fan_current

            self.fan_stream.add_value(fan_current)
            string = f" {fan_current}rpm"
            graph = Text(
                self.fan_stream.graph[-1][: -len(string)] + string,
                style="dark_orange",
            )
            t.add_row(graph, "")

        self.update_panel_content(t)

    def _refresh_info_box(self, load_per_thread):
        lines = []
        for core_id, thread_ids in enumerate(self.core_threads):
            line = []
            for i in thread_ids:
                color = val_to_color(load_per_thread[i], 0.0, 100.0)
                line.append(
                    f"[{color}]"
                    + f"{self.thread_load_streams[i].graph[0]}"
                    + f"{round(self.thread_load_streams[i].values[-1]):3d}%"
                    + "[/]"
                )
            if self.has_core_temps:
                stream = self.core_temp_streams[core_id]
                val = stream.values[-1]
                color = "slate_blue1" if val < 70.0 else "red3"
                line.append(
                    f"[{color}]{stream.graph[0]} {round(stream.values[-1])}°C[/]"
                )

            lines.append(" ".join(line))

        self.info_box.renderable = "\n".join(lines)

        cpu_freq = get_current_freq()

        if cpu_freq is None:
            self.info_box.subtitle = None
        else:
            self.info_box.subtitle = f"{round(cpu_freq):4d} MHz"

        self.info_box_width = 4 + len(Text.from_markup(lines[0]))

    async def on_resize(self, event):
        graph_width = self.size.width - self.info_box_width - 5
        self.cpu_total_stream.reset_width(graph_width)
        if self.has_cpu_temp:
            self.temp_total_stream.reset_width(graph_width)
        if self.has_fan_rpm:
            self.fan_stream.reset_width(graph_width)
