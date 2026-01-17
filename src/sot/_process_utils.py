"""Process management utilities for SOT."""

from __future__ import annotations

from typing import Literal

import psutil
from psutil import AccessDenied, NoSuchProcess, ZombieProcess

SeverityLevel = Literal["information", "warning", "error"]


class ProcessActionResult:
    """Result of a process action."""

    def __init__(
        self,
        success: bool,
        message: str,
        severity: SeverityLevel = "information",
    ):
        self.success = success
        self.message = message
        self.severity = severity


def kill_process(pid: int, name: str = "Unknown") -> ProcessActionResult:
    """Kill a process by PID.

    Args:
        pid: Process ID
        name: Process name for error messages

    Returns:
        ProcessActionResult with success status and message
    """
    if not pid:
        return ProcessActionResult(
            success=False,
            message="❌ Invalid process ID",
            severity="error",
        )

    try:
        target = psutil.Process(pid)
        target.kill()
        return ProcessActionResult(
            success=True,
            message=f"💥 Killed {name} (PID: {pid})",
            severity="warning",
        )
    except ZombieProcess:
        return ProcessActionResult(
            success=False,
            message=f"🧟 {name} (PID: {pid}) is a zombie process",
            severity="warning",
        )
    except NoSuchProcess:
        return ProcessActionResult(
            success=False,
            message=f"❌ Process {pid} no longer exists",
            severity="error",
        )
    except AccessDenied:
        return ProcessActionResult(
            success=False,
            message=f"🔒 Access denied to {name} (PID: {pid})",
            severity="error",
        )
    except Exception as e:
        return ProcessActionResult(
            success=False,
            message=f"❌ Error: {str(e)}",
            severity="error",
        )


def terminate_process(pid: int, name: str = "Unknown") -> ProcessActionResult:
    """Terminate a process by PID (graceful shutdown).

    Args:
        pid: Process ID
        name: Process name for error messages

    Returns:
        ProcessActionResult with success status and message
    """
    if not pid:
        return ProcessActionResult(
            success=False,
            message="❌ Invalid process ID",
            severity="error",
        )

    try:
        target = psutil.Process(pid)
        target.terminate()
        return ProcessActionResult(
            success=True,
            message=f"🛑 Terminated {name} (PID: {pid})",
            severity="information",
        )
    except ZombieProcess:
        return ProcessActionResult(
            success=False,
            message=f"🧟 {name} (PID: {pid}) is a zombie process",
            severity="warning",
        )
    except NoSuchProcess:
        return ProcessActionResult(
            success=False,
            message=f"❌ Process {pid} no longer exists",
            severity="error",
        )
    except AccessDenied:
        return ProcessActionResult(
            success=False,
            message=f"🔒 Access denied to {name} (PID: {pid})",
            severity="error",
        )
    except Exception as e:
        return ProcessActionResult(
            success=False,
            message=f"❌ Error: {str(e)}",
            severity="error",
        )


def format_process_details(process_info: dict) -> list[str]:
    """Format process information for display.

    Args:
        process_info: Process information dictionary

    Returns:
        List of formatted detail strings
    """
    from ._helpers import sizeof_fmt

    details = [
        f"📋 {process_info.get('name', 'Unknown')} (PID: {process_info.get('pid', 'N/A')})"
    ]

    cpu_percent = process_info.get("cpu_percent", 0) or 0
    details.append(f"💻 CPU: {cpu_percent:.1f}%")

    mem_info = process_info.get("memory_info")
    if mem_info:
        mem_str = sizeof_fmt(mem_info.rss, suffix="", sep="")
        details.append(f"🧠 Memory: {mem_str}")

    num_threads = process_info.get("num_threads")
    if num_threads:
        details.append(f"🧵 Threads: {num_threads}")

    total_io_rate = process_info.get("total_io_rate", 0)
    if total_io_rate > 0:
        net_io_str = sizeof_fmt(total_io_rate, fmt=".1f", suffix="", sep="") + "/s"
        details.append(f"🌐 Net I/O: {net_io_str}")

    num_connections = process_info.get("num_connections", 0)
    if num_connections > 0:
        details.append(f"🔗 Connections: {num_connections}")

    status = process_info.get("status")
    if status:
        status_emoji = {
            "running": "🏃",
            "sleeping": "😴",
            "stopped": "⏸️",
            "zombie": "🧟",
            "idle": "💤",
        }.get(status, "❓")
        details.append(f"{status_emoji} Status: {status}")

    return details
