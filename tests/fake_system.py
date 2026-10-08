"""A fixed, fake machine so TUI snapshots don't depend on the host."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import psutil

from sot import _collectors
from sot.clean.cli import CleanTarget
from sot.tui import refresh

GIB = 1024**3
NOW = datetime(2026, 10, 8, 9, 30, 0)


class _Clock:
    @staticmethod
    def now():
        return NOW


def _usage(total, used):
    return SimpleNamespace(
        total=total, used=used, free=total - used, percent=round(used / total * 100, 1)
    )


def _proc(pid, name, cpu, rss_mib, user="dev", status="sleeping", cmd=None, ports=()):
    return {
        "pid": pid,
        "name": name,
        "username": user,
        "cmdline": cmd or [name],
        "cpu_percent": cpu,
        "num_threads": 4,
        "memory_info": SimpleNamespace(rss=rss_mib * 1024**2),
        "status": status,
        "num_connections": len(ports),
        "listen_ports": list(ports),
        "io_read_bytes": 0,
        "io_write_bytes": 0,
    }


PROCESSES = [
    _proc(101, "postgres", 12.5, 220, ports=[5432]),
    _proc(202, "node", 8.0, 180, cmd=["node", "vite"], ports=[5173]),
    _proc(303, "python3", 3.2, 95, cmd=["python3", "-m", "uvicorn", "app:api"]),
    _proc(404, "sshd", 0.1, 6, user="root"),
    _proc(505, "launchd", 0.0, 12, user="root", status="running"),
]

PORTS = [
    {"port": 5432, "pid": 101, "name": "postgres", "address": "127.0.0.1"},
    {"port": 5173, "pid": 202, "name": "node", "address": "0.0.0.0"},
]


def _volume(disk_id, name, mount, total, used):
    usage = _usage(total, used)
    return {
        "disk_id": disk_id,
        "volume_name": name,
        "usage": usage,
        "io_stats": None,
        "partitions": [
            {
                "partition_id": f"{disk_id}s1",
                "device": f"/dev/{disk_id}s1",
                "mountpoint": mount,
                "fstype": "apfs",
                "usage": usage,
            }
        ],
    }


VOLUMES = [
    _volume("disk1", "System", "/", 500 * GIB, 320 * GIB),
    _volume("disk2", "Backup", "/Volumes/Backup", 2000 * GIB, 900 * GIB),
]

BENCH_DISKS = [
    {
        "disk_id": "/dev/disk1",
        "partitions": [{"device": "/dev/disk1s1", "mountpoint": "/"}],
        "largest_partition": {"device": "/dev/disk1s1", "mountpoint": "/"},
        "total_bytes": 500 * GIB,
        "free_bytes": 180 * GIB,
    }
]

SYSTEM_INFO = [
    ("System", [("Host", "dev@sotbox"), ("Model", "Test Machine")]),
    ("Software", [("OS", "TestOS 1.0"), ("Kernel", "6.0"), ("Shell", "zsh")]),
    ("Hardware", [("Chip", "Test CPU (8 cores)")]),
    ("Status", [("Uptime", "3d 4h 5m"), ("Memory", "8 GiB / 16 GiB")]),
]

CLEAN_TARGETS = [
    CleanTarget("User Caches", Path("/fake/caches"), "Application cache files"),
    CleanTarget("Temp Files", Path("/fake/tmp"), "Temporary files", requires_sudo=True),
    CleanTarget("npm Cache", Path("/fake/npm"), "Node.js npm cache"),
]
CLEAN_SIZES = {"User Caches": 2 * GIB, "Temp Files": 512 * 1024**2, "npm Cache": 0}


def install(monkeypatch) -> None:
    for name in dir(refresh):
        if name.isupper():
            monkeypatch.setattr(refresh, name, 3600.0)

    platform = SimpleNamespace(
        node=lambda: "sotbox",
        system=lambda: "Linux",
        architecture=lambda: ("64bit", ""),
        release=lambda: "6.0",
        mac_ver=lambda: ("", ("", "", ""), ""),
    )
    for module in ("sot.widgets.info", "sot.widgets.disk", "sot.tui.components.header"):
        monkeypatch.setattr(f"{module}.platform", platform)
    monkeypatch.setattr("sot.tui.components.header.datetime", _Clock)
    monkeypatch.setattr("sot.widgets.info.datetime", _Clock)
    monkeypatch.setattr("sot.widgets.info.time", SimpleNamespace(time=lambda: 1e6))
    monkeypatch.setattr("sot.widgets.info.getpass.getuser", lambda: "dev")
    monkeypatch.setattr(
        "sot.widgets.info.distro.os_release_info",
        lambda: {"name": "TestOS", "version_id": "1.0"},
    )
    monkeypatch.setattr("sot.widgets.network.__version__", "0.0.0")
    monkeypatch.setattr("sot.tui.components.drawer.timestamp", lambda: "09:30:00")
    monkeypatch.setattr("sot.widgets.sot.random.choice", lambda seq: seq[0])
    monkeypatch.setattr("sot.tui.views.overview.has_gpu", lambda: False)

    monkeypatch.setattr("sot.widgets.cpu.get_cpu_model", lambda: "Test CPU")
    monkeypatch.setattr("sot.widgets.cpu.get_current_temps", lambda: None)
    monkeypatch.setattr("sot.widgets.cpu.get_current_freq", lambda: 3200.0)

    def cpu_percent(interval=None, percpu=False):
        return [25.0, 50.0, 10.0, 75.0] if percpu else 40.0

    fakes = {
        "cpu_count": lambda logical=True: 4 if logical else 2,
        "cpu_percent": cpu_percent,
        "sensors_fans": lambda: {},
        "sensors_temperatures": lambda: {},
        "sensors_battery": lambda: None,
        "boot_time": lambda: 0.0,
        "pids": lambda: list(range(150)),
        "virtual_memory": lambda: SimpleNamespace(
            total=16 * GIB,
            available=8 * GIB,
            percent=50.0,
            used=7 * GIB,
            free=1 * GIB,
            cached=2 * GIB,
        ),
        "swap_memory": lambda: SimpleNamespace(total=2 * GIB, used=GIB // 4),
        "disk_partitions": lambda all=False: [
            SimpleNamespace(device="/dev/disk1s1", mountpoint="/", fstype="apfs")
        ],
        "disk_usage": lambda path: _usage(500 * GIB, 320 * GIB),
        "disk_io_counters": lambda: SimpleNamespace(
            read_bytes=10 * GIB,
            write_bytes=4 * GIB,
            read_count=1000,
            write_count=500,
            read_time=100,
            write_time=80,
        ),
        "net_if_stats": lambda: {"eth0": SimpleNamespace(isup=True)},
        "net_io_counters": lambda pernic=False: {
            "eth0": SimpleNamespace(bytes_recv=3 * GIB, bytes_sent=GIB)
        },
        "net_if_addrs": lambda: {
            "eth0": [
                SimpleNamespace(
                    family=2, address="192.168.1.20", netmask="255.255.255.0"
                )
            ]
        },
        "net_connections": lambda kind="inet": [],
    }
    for name, fake in fakes.items():
        monkeypatch.setattr(psutil, name, fake, raising=False)

    monkeypatch.setattr(_collectors, "get_process_list", lambda: PROCESSES)
    monkeypatch.setattr(_collectors, "process_sampler", _collectors.ProcessSampler())
    for module in (
        "sot.tui.components.process_table",
        "sot.tui.views.processes",
        "sot.tui.details",
        "sot.tui.commands",
    ):
        monkeypatch.setattr(f"{module}.process_sampler", _collectors.process_sampler)
    monkeypatch.setattr("sot.tui.views.processes.listening_ports", lambda: PORTS)
    monkeypatch.setattr("sot.tui.views.disks.get_volume_info", lambda: VOLUMES)
    monkeypatch.setattr("sot.tui.views.system.collect_system_info", lambda: SYSTEM_INFO)
    monkeypatch.setattr("sot.tui.views.system.system_logo", lambda: ["  /\\", " /  \\"])
    monkeypatch.setattr("sot.tui.views.system.status_section", lambda: SYSTEM_INFO[-1])
    monkeypatch.setattr("sot.tui.views.bench.get_physical_disks", lambda: BENCH_DISKS)
    monkeypatch.setattr("sot.tui.views.clean._get_targets", lambda: CLEAN_TARGETS)
    monkeypatch.setattr("sot.tui.views.clean._is_elevated", lambda: False)
    monkeypatch.setattr(
        "sot.tui.views.clean.scan_target",
        lambda target: {
            "target": target,
            "size": CLEAN_SIZES[target.name],
            "exists": True,
        },
    )
