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
            message="Invalid process ID",
            severity="error",
        )

    try:
        target = psutil.Process(pid)
        target.kill()
        return ProcessActionResult(
            success=True,
            message=f"Killed {name} (PID {pid})",
            severity="warning",
        )
    except ZombieProcess:
        return ProcessActionResult(
            success=False,
            message=f"{name} (PID {pid}) is a zombie process",
            severity="warning",
        )
    except NoSuchProcess:
        return ProcessActionResult(
            success=False,
            message=f"Process {pid} no longer exists",
            severity="error",
        )
    except AccessDenied:
        return ProcessActionResult(
            success=False,
            message=f"Access denied to {name} (PID {pid})",
            severity="error",
        )
    except Exception as e:
        return ProcessActionResult(
            success=False,
            message=f"Error: {e}",
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
            message="Invalid process ID",
            severity="error",
        )

    try:
        target = psutil.Process(pid)
        target.terminate()
        return ProcessActionResult(
            success=True,
            message=f"Terminated {name} (PID {pid})",
            severity="information",
        )
    except ZombieProcess:
        return ProcessActionResult(
            success=False,
            message=f"{name} (PID {pid}) is a zombie process",
            severity="warning",
        )
    except NoSuchProcess:
        return ProcessActionResult(
            success=False,
            message=f"Process {pid} no longer exists",
            severity="error",
        )
    except AccessDenied:
        return ProcessActionResult(
            success=False,
            message=f"Access denied to {name} (PID {pid})",
            severity="error",
        )
    except Exception as e:
        return ProcessActionResult(
            success=False,
            message=f"Error: {e}",
            severity="error",
        )


def run_process_action(action: str, pid: int, name: str) -> ProcessActionResult:
    """Run ``kill`` or ``terminate`` on a process."""
    if action == "kill":
        return kill_process(pid, name)
    if action == "terminate":
        return terminate_process(pid, name)
    return ProcessActionResult(
        success=False, message=f"Unknown action: {action}", severity="error"
    )
