"""Live details for the drawer, looked up by kind and key."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from .._collectors import dev_environments, listening_ports, process_sampler
from .._helpers import sizeof_fmt

Details = tuple[str, list[tuple[str, str]]]


def _process(pid: str) -> Details | None:
    proc = next((p for p in process_sampler.sample() if str(p["pid"]) == pid), None)
    if proc is None:
        return None
    mem = proc.get("memory_info")
    io_rate = proc.get("total_io_rate") or 0
    rows = [
        ("PID", pid),
        ("User", proc.get("username") or "-"),
        ("Status", proc.get("status") or "-"),
        ("CPU", f"{proc.get('cpu_percent') or 0:.1f}%"),
        ("Memory", sizeof_fmt(mem.rss, fmt=".1f") if mem else "-"),
        ("Threads", str(proc.get("num_threads") or "-")),
        ("I/O", sizeof_fmt(io_rate, fmt=".1f") + "/s" if io_rate else "-"),
        ("Connections", str(proc.get("num_connections") or 0)),
        ("Listening", ", ".join(map(str, proc.get("listen_ports") or [])) or "-"),
        ("Command", " ".join(proc.get("cmdline") or []) or "-"),
    ]
    return proc.get("name") or pid, rows


def _port(port: str) -> Details | None:
    info = next((p for p in listening_ports() if str(p["port"]) == port), None)
    if info is None:
        return None
    rows = [
        ("Port", port),
        ("Address", info["address"]),
        ("Process", info["name"]),
        ("PID", str(info["pid"] or "-")),
    ]
    return f"Port {port}", rows


def _dev_env(kind: str) -> Details | None:
    envs = dev_environments(process_sampler.sample())
    env = next((e for e in envs if e["type"] == kind), None)
    if env is None:
        return None
    memory = sizeof_fmt(env["memory_mb"] * 1024 * 1024, fmt=".1f")
    rows = [
        ("Processes", str(env["count"])),
        ("Ports", ", ".join(map(str, env["ports"])) or "-"),
        ("CPU", f"{env['cpu']:.1f}%"),
        ("Memory", memory),
        ("Examples", ", ".join(env["processes"]) or "-"),
    ]
    return f"{kind.upper()} environment", rows


LOOKUPS: dict[str, Callable[[str], Details | None]] = {
    "process": _process,
    "port": _port,
    "devenv": _dev_env,
}

# Kinds whose drawer offers the process keys.
ACTIONABLE = {"process", "port"}


def details(kind: str, key: str) -> Details | None:
    return LOOKUPS[kind](key)


def timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")
