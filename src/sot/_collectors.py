"""System data shared by the views, sampled once and reused."""

from __future__ import annotations

import time

import psutil

_PROCESS_ATTRS = [
    "pid",
    "name",
    "username",
    "cmdline",
    "cpu_percent",
    "num_threads",
    "memory_info",
    "status",
]


def get_process_list() -> list[dict]:
    """Every running process with its connection and I/O counters."""
    processes = []

    for proc in psutil.process_iter(_PROCESS_ATTRS):
        try:
            info = proc.info.copy()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

        info["num_connections"] = 0
        info["listen_ports"] = []
        info["io_read_bytes"] = 0
        info["io_write_bytes"] = 0
        try:
            connections = proc.net_connections(kind="inet")
            info["num_connections"] = len(connections)
            info["listen_ports"] = [
                c.laddr.port for c in connections if c.status == "LISTEN" and c.laddr
            ]
            io = getattr(proc, "io_counters", lambda: None)()
            if io is not None:
                info["io_read_bytes"] = io.read_bytes
                info["io_write_bytes"] = io.write_bytes
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            pass

        processes.append(info)

    return [p for p in processes if p.get("pid")]


class ProcessSampler:
    """Samples the process list at most once per ``max_age`` seconds and adds
    I/O rates, so every view sees the same data."""

    def __init__(self, max_age: float = 1.0):
        self.max_age = max_age
        self._rows: list[dict] = []
        self._taken = 0.0
        self._previous_io: dict[int, tuple[int, int]] = {}

    def sample(self) -> list[dict]:
        now = time.monotonic()
        if self._rows and now - self._taken < self.max_age:
            return self._rows

        rows = get_process_list()
        elapsed = now - self._taken if self._taken else 0.0
        for row in rows:
            io = (row["io_read_bytes"], row["io_write_bytes"])
            previous = self._previous_io.get(row["pid"])
            if previous is None or elapsed <= 0:
                read_rate = write_rate = 0.0
            else:
                read_rate = max(0.0, (io[0] - previous[0]) / elapsed)
                write_rate = max(0.0, (io[1] - previous[1]) / elapsed)
            row["io_read_rate"] = read_rate
            row["io_write_rate"] = write_rate
            row["total_io_rate"] = read_rate + write_rate

        self._previous_io = {
            row["pid"]: (row["io_read_bytes"], row["io_write_bytes"]) for row in rows
        }
        self._rows, self._taken = rows, now
        return rows


def listening_ports() -> list[dict]:
    """Listening sockets with the process behind each port."""
    ports: dict[int, dict] = {}
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        # macOS needs root to list other users' sockets.
        return []

    for conn in connections:
        if conn.status != "LISTEN" or not conn.laddr or conn.laddr.port in ports:
            continue
        name = "System"
        if conn.pid:
            try:
                name = psutil.Process(conn.pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                name = "Unknown"
        ports[conn.laddr.port] = {
            "port": conn.laddr.port,
            "pid": conn.pid,
            "name": name,
            "address": conn.laddr.ip,
        }
    return list(ports.values())


DEV_PATTERNS = {
    "node": ["node", "npm", "yarn", "pnpm", "next", "vite", "webpack"],
    "python": ["python", "uvicorn", "gunicorn", "flask", "django", "fastapi"],
    "docker": ["docker", "containerd", "dockerd"],
    "ruby": ["ruby", "rails", "puma"],
    "go": ["go", "air"],
    "rust": ["cargo"],
}


def _dev_type(proc: dict) -> str | None:
    name = (proc.get("name") or "").lower()
    cmdline = " ".join(proc.get("cmdline") or []).lower()
    for env, patterns in DEV_PATTERNS.items():
        if any(p in name or p in cmdline for p in patterns):
            return env
    return None


def dev_environments(processes: list[dict]) -> list[dict]:
    """Group development tool processes by ecosystem."""
    groups: dict[str, dict] = {}
    for proc in processes:
        env = _dev_type(proc)
        if env is None:
            continue
        group = groups.setdefault(
            env,
            {
                "type": env,
                "count": 0,
                "ports": set(),
                "cpu": 0.0,
                "memory_mb": 0.0,
                "processes": [],
            },
        )
        mem = proc.get("memory_info")
        group["count"] += 1
        group["ports"].update(proc.get("listen_ports") or [])
        group["cpu"] += proc.get("cpu_percent") or 0
        group["memory_mb"] += mem.rss / (1024 * 1024) if mem else 0
        group["processes"].append(proc.get("name"))

    return [
        {**group, "ports": sorted(group["ports"]), "processes": group["processes"][:3]}
        for group in groups.values()
    ]


process_sampler = ProcessSampler()
