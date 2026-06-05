"""
GPU data collection.

Cross-platform GPU detection and sampling with graceful degradation. Each backend
returns whatever metrics the platform exposes and leaves the rest as ``None`` so the
widget can render only what is actually available. Collection never raises.

Backends (probed in order, first match wins):
    * Apple Silicon - ``ioreg`` IOAccelerator statistics (no sudo required)
    * NVIDIA        - ``nvidia-smi`` CSV query
    * AMD           - ``rocm-smi`` JSON (best effort)
"""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Optional

# A GPU reader returns a sample, or ``None`` when it cannot read anything.
Reader = Callable[[], Optional["GpuSample"]]

_SUBPROCESS_TIMEOUT = 3.0


@dataclass
class GpuSample:
    """A single point-in-time GPU reading. Every metric is optional.

    Memory values are in bytes; ``mem_total`` is ``None`` on unified-memory
    architectures (e.g. Apple Silicon) where there is no dedicated VRAM.
    ``name`` and ``cores`` describe the device rather than its live state.
    """

    name: Optional[str] = None
    util_percent: Optional[float] = None
    mem_used: Optional[int] = None
    mem_total: Optional[int] = None
    mem_alloc: Optional[int] = None
    temp_c: Optional[float] = None
    power_w: Optional[float] = None
    cores: Optional[int] = None
    renderer_util_percent: Optional[float] = None
    tiler_util_percent: Optional[float] = None

    def is_empty(self) -> bool:
        """True when no live metric could be read (an unusable sample).

        Device identity (``name``, ``cores``) is ignored here - a sample with
        only a name is still useless for display.
        """
        return all(
            value is None
            for value in (
                self.util_percent,
                self.mem_used,
                self.mem_total,
                self.mem_alloc,
                self.temp_c,
                self.power_w,
                self.renderer_util_percent,
                self.tiler_util_percent,
            )
        )


def _run(cmd: list[str]) -> Optional[str]:
    """Run a command and return stdout, or ``None`` on any failure."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _to_float(value: Optional[str]) -> Optional[float]:
    """Parse a float, tolerating ``None``, blanks, and ``[N/A]`` placeholders."""
    if value is None:
        return None
    try:
        return float(value.strip())
    except (AttributeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Apple Silicon
# --------------------------------------------------------------------------- #

_APPLE_UTIL_RE = re.compile(r'"Device Utilization %"=(\d+)')
_APPLE_RENDER_RE = re.compile(r'"Renderer Utilization %"=(\d+)')
_APPLE_TILER_RE = re.compile(r'"Tiler Utilization %"=(\d+)')
_APPLE_MEM_RE = re.compile(r'"In use system memory"=(\d+)')
_APPLE_ALLOC_RE = re.compile(r'"Alloc system memory"=(\d+)')
_APPLE_CORES_RE = re.compile(r'"gpu-core-count"\s*=\s*(\d+)')


def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


@lru_cache(maxsize=1)
def _apple_gpu_name() -> Optional[str]:
    """Chip brand string (e.g. ``Apple M1 Pro``); the GPU is part of the SoC."""
    stdout = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    if stdout is None:
        return None
    name = stdout.strip()
    return name or None


def _search_int(pattern: re.Pattern, text: str) -> Optional[int]:
    match = pattern.search(text)
    return int(match.group(1)) if match else None


def _parse_apple_ioreg(text: str) -> Optional[GpuSample]:
    """Parse ``ioreg -c IOAccelerator`` output into a sample (pure)."""
    util = _search_int(_APPLE_UTIL_RE, text)
    mem_used = _search_int(_APPLE_MEM_RE, text)
    if util is None and mem_used is None:
        return None

    render = _search_int(_APPLE_RENDER_RE, text)
    tiler = _search_int(_APPLE_TILER_RE, text)
    return GpuSample(
        name=_apple_gpu_name(),
        util_percent=float(util) if util is not None else None,
        # Unified memory: in-use and allocated sizes are known, but there is no
        # dedicated VRAM total to report.
        mem_used=mem_used,
        mem_total=None,
        mem_alloc=_search_int(_APPLE_ALLOC_RE, text),
        cores=_search_int(_APPLE_CORES_RE, text),
        renderer_util_percent=float(render) if render is not None else None,
        tiler_util_percent=float(tiler) if tiler is not None else None,
    )


def _read_apple_silicon() -> Optional[GpuSample]:
    stdout = _run(["ioreg", "-r", "-d", "1", "-w", "0", "-c", "IOAccelerator"])
    if stdout is None:
        return None
    return _parse_apple_ioreg(stdout)


# --------------------------------------------------------------------------- #
# NVIDIA
# --------------------------------------------------------------------------- #

_NVIDIA_QUERY = (
    "name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw"
)
_MIB = 1024 * 1024


def _parse_nvidia_csv(text: str) -> Optional[GpuSample]:
    """Parse one row of ``nvidia-smi --format=csv,noheader,nounits`` (pure)."""
    rows = [row for row in text.splitlines() if row.strip()]
    if not rows:
        return None
    # Report the first GPU only for now.
    fields = [field.strip() for field in rows[0].split(",")]
    if len(fields) < 6:
        return None

    name, util, mem_used, mem_total, temp, power = fields[:6]
    mem_used_mib = _to_float(mem_used)
    mem_total_mib = _to_float(mem_total)
    return GpuSample(
        name=name or None,
        util_percent=_to_float(util),
        mem_used=int(mem_used_mib * _MIB) if mem_used_mib is not None else None,
        mem_total=int(mem_total_mib * _MIB) if mem_total_mib is not None else None,
        temp_c=_to_float(temp),
        power_w=_to_float(power),
    )


def _read_nvidia() -> Optional[GpuSample]:
    stdout = _run(
        [
            "nvidia-smi",
            f"--query-gpu={_NVIDIA_QUERY}",
            "--format=csv,noheader,nounits",
        ]
    )
    if stdout is None:
        return None
    return _parse_nvidia_csv(stdout)


# --------------------------------------------------------------------------- #
# AMD (best effort)
# --------------------------------------------------------------------------- #


def _find_first(card: dict, *needles: str) -> Optional[str]:
    """Return the value of the first key containing all the given substrings.

    ``rocm-smi`` key names vary across versions, so match loosely.
    """
    for key, value in card.items():
        lowered = key.lower()
        if all(needle in lowered for needle in needles):
            return value
    return None


def _parse_amd_json(text: str) -> Optional[GpuSample]:
    """Parse ``rocm-smi --json`` output into a sample (pure, best effort)."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    cards = [value for key, value in data.items() if isinstance(value, dict)]
    if not cards:
        return None
    card = cards[0]

    mem_used = _to_float(_find_first(card, "vram", "used"))
    mem_total = _to_float(_find_first(card, "vram", "total"))
    sample = GpuSample(
        name=_find_first(card, "card series") or _find_first(card, "card model"),
        util_percent=_to_float(_find_first(card, "gpu use")),
        mem_used=int(mem_used) if mem_used is not None else None,
        mem_total=int(mem_total) if mem_total is not None else None,
        temp_c=_to_float(_find_first(card, "temperature", "edge")),
        power_w=_to_float(_find_first(card, "average graphics package power")),
    )
    return None if sample.is_empty() else sample


def _read_amd() -> Optional[GpuSample]:
    stdout = _run(
        [
            "rocm-smi",
            "--showuse",
            "--showmeminfo",
            "vram",
            "--showtemp",
            "--showpower",
            "--json",
        ]
    )
    if stdout is None:
        return None
    return _parse_amd_json(stdout)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


@lru_cache(maxsize=1)
def _select_reader() -> Optional[Reader]:
    """Probe available backends once and remember the first that returns data."""
    candidates: list[Reader] = []
    if _is_apple_silicon():
        candidates.append(_read_apple_silicon)
    if shutil.which("nvidia-smi"):
        candidates.append(_read_nvidia)
    if shutil.which("rocm-smi"):
        candidates.append(_read_amd)

    for reader in candidates:
        sample = reader()
        if sample is not None and not sample.is_empty():
            return reader
    return None


def has_gpu() -> bool:
    """Whether a readable GPU is available on this machine."""
    return _select_reader() is not None


def read_gpu() -> Optional[GpuSample]:
    """Return a current GPU sample, or ``None`` when no GPU is available."""
    reader = _select_reader()
    if reader is None:
        return None
    return reader()
