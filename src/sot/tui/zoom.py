"""Overview zoom: `+` gives the graphs more room, `-` gives it to the processes."""

from __future__ import annotations

MIN, MAX = -2, 2

level = 0


def set_level(value: int) -> int:
    """Clamp ``value`` to the zoom range and make it the current level."""
    global level
    level = max(MIN, min(MAX, value))
    return level


def memory_rows() -> int:
    """Rows per memory graph."""
    return max(1, 2 + level)


def bottom_weight() -> float:
    """Height of the disk and network row, relative to the CPU row."""
    return 1.1 * 1.25**level


def label() -> str:
    return f"{level:+d}" if level else "0"
