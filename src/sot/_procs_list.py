import psutil
from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widget import Widget

from ._helpers import sizeof_fmt


def get_process_list(num_procs: int):
    processes = list(
        psutil.process_iter(
            [
                "pid",
                "name",
                "username",
                "cmdline",
                "cpu_percent",
                "num_threads",
                "memory_info",
                "status",
            ]
        )
    )

    if processes[0].pid == 0:
        # Remove process with PID 0. On Windows, that's SYSTEM IDLE, and we
        # don't want that to appear at the top of the list.
        # <https://twitter.com/andre_roberge/status/1488885893716975622/photo/1>
        processes = processes[1:]

    processes = [p.info for p in processes]

    processes = sorted(
        processes,
        # The item.info["cpu_percent"] can be `ad_value` (default None).
        # It gets assigned to a dict key in case AccessDenied or
        # ZombieProcess exception is raised when retrieving that particular
        # process information.
        key=lambda p: (p["cpu_percent"] or 0.0),
        reverse=True,
    )
    processes = processes[:num_procs]
    return processes


class ProcsList(Widget):
    def on_mount(self):
        self.max_num_procs = 100
        self.collect_data()
        self.set_interval(6.0, self.collect_data)

    def collect_data(self):
        processes = get_process_list(self.max_num_procs)

        table = Table(
            show_header=True,
            header_style="bold",
            box=None,
            padding=(0, 1),
            expand=True,
        )
        # set ration=1 on all columns that should be expanded
        # <https://github.com/Textualize/rich/issues/2030>
        table.add_column(Text("PID", justify="left"), no_wrap=True, justify="right")
        table.add_column("Process", style="aquamarine3", no_wrap=True, ratio=1)
        # table.add_column("Args", no_wrap=True, ratio=2)
        table.add_column(
            Text("🧵", justify="left"),
            style="aquamarine3",
            no_wrap=True,
            justify="right",
        )
        # table.add_column("👤", no_wrap=True)
        table.add_column(
            Text("Mem", justify="left"),
            style="aquamarine3",
            no_wrap=True,
            justify="right",
        )
        table.add_column(
            Text("CPU %", style="u", justify="left"),
            no_wrap=True,
            justify="right",
        )

        for p in processes:
            # Everything can be None here, see comment above
            pid = p["pid"]
            pid = "" if pid is None else str(pid)
            #
            name = p["name"]
            if name is None:
                name = ""
            #
            # cmdline = p["cmdline"]
            # cmdline = "" if cmdline is None else " ".join(p["cmdline"][1:])
            #
            num_threads = p["num_threads"]
            num_threads = "" if num_threads is None else str(num_threads)
            #
            # username = p["username"]
            # if username is None:
            #     username = ""
            #
            mem_info = p["memory_info"]
            mem_info = (
                "" if mem_info is None else sizeof_fmt(mem_info.rss, suffix="", sep="")
            )
            #
            cpu_percent = p["cpu_percent"]
            cpu_percent = "" if cpu_percent is None else f"{cpu_percent:.1f}"
            table.add_row(
                pid,
                name,
                # cmdline,
                num_threads,
                # username,
                mem_info,
                cpu_percent,
            )

        total_num_threads = sum((p["num_threads"] or 0) for p in processes)
        num_sleep = sum(p["status"] == "sleeping" for p in processes)

        self.panel = Panel(
            table,
            title=f"[b]📋 Processes [/] - {len(processes)} ({total_num_threads} 🧵), {num_sleep} 😴",
            title_align="left",
            # border_style="dark_orange",
            border_style="bright_black",
            box=box.SQUARE,
        )

        self.refresh()

    def render(self) -> Panel:
        return self.panel

    def on_resize(self):
        # Calculate max processes based on available height
        # Subtract 3 for borders and header
        self.max_num_procs = self.size.height - 3
        self.collect_data()  # Refresh the display with new size
