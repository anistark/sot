"""
Themes for the TUI.

A theme pairs ``Colors`` (semantic color roles) with a ``Design`` (how
components are drawn: frames, graphs, meters, indicators, logo, ...). Widgets
ask the active theme via ``theme()`` instead of hardcoding either, so a new
theme only overrides the fields that differ from the classic defaults.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, replace
from functools import lru_cache

from rich.box import ROUNDED, SQUARE, Box
from rich.color import Color, blend_rgb
from rich.style import Style
from rich.text import Text
from textual.theme import BUILTIN_THEMES
from textual.theme import Theme as TextualTheme

from .blockchar_stream import BlockCharStream
from .braille_stream import BrailleStream

CYBER_BOX = Box("▛──▜\n" "│  │\n" "├──┤\n" "│  │\n" "├──┤\n" "├──┤\n" "│  │\n" "▙──▟\n")

RAIL_BOX = Box("▗── \n" "▐   \n" "▐   \n" "▐   \n" "▐   \n" "▐   \n" "▐   \n" "▝── \n")

CLASSIC_LOGO = (
    "      ▄▀▀  ▄▀▀▄  ▀█▀      ",
    "      ▀▀▄  █  █   █       ",
    "      ▄▄▀  ▀▄▄▀   █       ",
)

CYBER_LOGO = (
    "    ▟▀▀▀ ▟▀▀▙ ▀█▀    ",
    "    ▀▀▀▙ █  █  █     ",
    "    ▀▀▀▘ ▜▄▄▛  ▀     ",
)


@dataclass(frozen=True)
class Colors:
    text: str = "bright_white"
    muted: str = "dim"
    accent: str = "cyan"
    border: str = "bright_black"
    border_focus: str = "bright_white"
    border_alert: str = "yellow"
    label: str = "bold"
    selected: str = "black on white"
    alert_tag: str = "bold yellow on black"
    title_tag: str = "bold"
    primary: str = "yellow"
    secondary: str = "aquamarine3"
    info: str = "sky_blue3"
    temp: str = "slate_blue1"
    warm: str = "dark_orange"
    danger: str = "red3"
    rx: str = "aquamarine3"
    tx: str = "yellow"
    # Per-thread CPU load, low -> high.
    load: tuple[str, str, str, str] = (
        "yellow",
        "dark_orange",
        "sky_blue3",
        "aquamarine3",
    )
    # Health levels, good -> critical.
    health: tuple[str, str, str, str] = (
        "bright_green",
        "bright_cyan",
        "bright_yellow",
        "bright_red",
    )
    # Disk usage levels: normal, high, full.
    usage: tuple[str, str, str] = ("green", "yellow", "red")
    logo: str = "bright_yellow"
    wave: tuple[str, str, str] = ("bright_cyan", "sky_blue3", "aquamarine3")
    # Color the top of graphs blends toward (see ``Design.graph_heat``).
    heat: str = "red"
    # Background of alternate table rows (see ``Design.stripes``).
    stripe: str = "grey11"

    @property
    def ok(self) -> str:
        return self.health[0]

    @property
    def warn(self) -> str:
        return self.health[2]

    @property
    def memory(self) -> tuple[str, ...]:
        return (self.primary, self.secondary, self.info, self.temp, self.danger)


@dataclass(frozen=True)
class Meter:
    fill: str = "█"
    empty: str = "░"
    # Optional fill glyph per health level, good -> critical.
    by_level: tuple[str, str, str, str] | None = None


@dataclass(frozen=True)
class Design:
    # Textual border type framing every panel.
    frame: str = "solid"
    # Frame for Rich panels and printed tables.
    app_box: Box = ROUNDED
    # Frame for boxes nested inside a panel (CPU cores, rx/tx).
    inner_box: Box = SQUARE
    # "plain": bold label; "tag": label on a colored tag.
    title: str = "plain"
    upper_titles: bool = False
    separator: str = " - "
    # "braille" (two samples per cell) or "blocks" (bar chart).
    graph: str = "braille"
    # 0 keeps graphs flat; up to 1 blends their top rows into ``Colors.heat``.
    graph_heat: float = 0.0
    meter: Meter = field(default_factory=lambda: Meter(by_level=("█", "▓", "▒", "░")))
    # Status glyphs, good -> critical.
    indicators: tuple[str, str, str, str] = ("●", "◐", "◑", "○")
    stripes: bool = False
    logo: tuple[str, ...] = CLASSIC_LOGO
    tagline: str | None = None
    glitch: bool = False


@dataclass(frozen=True)
class SotTheme:
    name: str
    colors: Colors = field(default_factory=Colors)
    design: Design = field(default_factory=Design)
    textual: TextualTheme | None = None

    def __post_init__(self):
        if self.textual is not None:
            variables = {**self._css_variables(), **self.textual.variables}
            object.__setattr__(
                self, "textual", replace(self.textual, variables=variables)
            )

    def _css_variables(self) -> dict[str, str]:
        """Expose the frame and cursor look to Textual CSS as ``$sot-*``."""
        c = self.colors
        selected = Style.parse(c.selected)
        variables = {
            "sot-frame": self.design.frame,
            "sot-border": textual_color(c.border),
            "sot-border-focus": textual_color(c.border_focus),
            "sot-border-alert": textual_color(c.border_alert),
            "sot-stripe": textual_color(c.stripe),
        }
        if selected.color and selected.bgcolor:
            variables["block-cursor-foreground"] = textual_color(selected.color.name)
            variables["block-cursor-background"] = textual_color(selected.bgcolor.name)
        return variables

    def title(self, label: str, detail: str | None = None) -> str:
        """Format a panel title, e.g. ``CPU`` with detail ``Apple M1``."""
        c, d = self.colors, self.design
        if d.upper_titles:
            label = label.upper()
        if d.title == "tag":
            head = f"[{c.title_tag}] {label} [/][{c.primary}]◤[/]"
            return f"{head} [{c.muted}]{detail}[/]" if detail else head
        head = f"[{c.title_tag}]{label}[/]"
        return f"{head}{d.separator}{detail}" if detail else head

    def stream(
        self,
        width: int,
        height: int,
        minval: float,
        maxval: float,
        flipud: bool = False,
    ) -> BrailleStream | BlockCharStream:
        cls = BlockCharStream if self.design.graph == "blocks" else BrailleStream
        return cls(width, height, minval, maxval, flipud=flipud)

    def graph(self, lines: list[str], color: str, flipud: bool = False) -> Text:
        """Render graph rows, blending toward the heat color as they rise."""
        heat = self.design.graph_heat
        n = len(lines)
        if not heat or n < 2:
            return Text("\n".join(lines), style=color)
        text = Text()
        for i, line in enumerate(lines):
            rise = i / (n - 1) if flipud else (n - 1 - i) / (n - 1)
            if i:
                text.append("\n")
            text.append(line, style=_blend(color, self.colors.heat, rise * heat))
        return text

    def meter(
        self,
        fraction: float,
        width: int,
        color: str,
        level: int | None = None,
        empty_style: str | None = None,
    ) -> Text:
        m = self.design.meter
        filled = int(max(0.0, min(1.0, fraction)) * width)
        fill = m.by_level[level] if m.by_level and level is not None else m.fill
        text = Text(fill * filled, style=color)
        text.append(m.empty * (width - filled), style=empty_style or color)
        return text


_ANSI_NAMES = {
    f"{prefix}{name}"
    for prefix in ("", "bright_")
    for name in ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")
}


def textual_color(name: str) -> str:
    """A Rich color name as Textual CSS understands it; ANSI colors stay ANSI."""
    if name in _ANSI_NAMES:
        return f"ansi_{name}"
    if name.startswith("#"):
        return name
    return Color.parse(name).get_truecolor().hex


@lru_cache(maxsize=256)
def _blend(base: str, target: str, amount: float) -> str:
    rgb = blend_rgb(
        Color.parse(base).get_truecolor(), Color.parse(target).get_truecolor(), amount
    )
    return Color.from_triplet(rgb).name


CLASSIC = SotTheme(
    name="classic",
    # ANSI colors so the TUI follows the terminal's own palette and background.
    textual=TextualTheme(
        name="classic",
        primary="ansi_yellow",
        secondary="ansi_cyan",
        accent="ansi_cyan",
        warning="ansi_yellow",
        error="ansi_red",
        success="ansi_green",
        foreground="ansi_default",
        background="ansi_default",
        surface="ansi_default",
        panel="ansi_default",
        boost="ansi_default",
        dark=True,
        ansi=True,
        variables=dict(BUILTIN_THEMES["ansi-dark"].variables),
    ),
)

_CP_BG = "#0b0b10"
_CP_YELLOW = "#fcee0a"
_CP_CYAN = "#00f0ff"
_CP_PINK = "#ff2a6d"
_CP_PURPLE = "#b967ff"
_CP_ORANGE = "#ff9f1c"
_CP_GREEN = "#00ff41"
_CP_TEXT = "#e8f9ff"
_CP_MUTED = "#6b6b85"

CYBERPUNK = SotTheme(
    name="cyberpunk",
    colors=Colors(
        text=_CP_TEXT,
        muted=_CP_MUTED,
        accent=_CP_CYAN,
        border="#6e1a37",
        border_focus=_CP_CYAN,
        border_alert=_CP_YELLOW,
        label=f"bold {_CP_GREEN}",
        selected=f"bold {_CP_BG} on {_CP_CYAN}",
        alert_tag=f"bold {_CP_BG} on {_CP_PINK}",
        title_tag=f"bold {_CP_BG} on {_CP_YELLOW}",
        primary=_CP_YELLOW,
        secondary=_CP_CYAN,
        info=_CP_PURPLE,
        temp=_CP_GREEN,
        warm=_CP_ORANGE,
        danger=_CP_PINK,
        rx=_CP_CYAN,
        tx=_CP_GREEN,
        load=(_CP_CYAN, _CP_YELLOW, _CP_ORANGE, _CP_PINK),
        health=(_CP_GREEN, _CP_CYAN, _CP_YELLOW, _CP_PINK),
        usage=(_CP_GREEN, _CP_YELLOW, _CP_PINK),
        logo=_CP_YELLOW,
        wave=(_CP_CYAN, _CP_PURPLE, _CP_GREEN),
        heat=_CP_PINK,
        stripe="#14101a",
    ),
    design=Design(
        frame="outer",
        app_box=CYBER_BOX,
        inner_box=RAIL_BOX,
        title="tag",
        upper_titles=True,
        separator=" // ",
        graph="blocks",
        graph_heat=0.8,
        meter=Meter(fill="▰", empty="▱"),
        indicators=("◆", "◈", "◇", "✕"),
        stripes=True,
        logo=CYBER_LOGO,
        tagline="// SYSTEM OBSERVATION TOOL",
        glitch=True,
    ),
    textual=TextualTheme(
        name="cyberpunk",
        primary=_CP_YELLOW,
        secondary=_CP_GREEN,
        accent=_CP_CYAN,
        warning=_CP_ORANGE,
        error=_CP_PINK,
        success=_CP_GREEN,
        foreground=_CP_TEXT,
        background=_CP_BG,
        surface="#12121a",
        panel="#1c0d14",
        dark=True,
    ),
)

THEMES = {t.name: t for t in (CLASSIC, CYBERPUNK)}
DEFAULT_THEME = CLASSIC.name

_active = CLASSIC


def theme() -> SotTheme:
    return _active


def set_theme(name: str) -> SotTheme:
    global _active
    try:
        _active = THEMES[name]
    except KeyError:
        raise ValueError(
            f"Unknown theme '{name}'. Available: {', '.join(THEMES)}"
        ) from None
    return _active


class ThemedStream:
    """A graph stream that keeps its raw samples and draws them in the style of
    the active theme, so switching themes keeps the history."""

    def __init__(
        self,
        width: int,
        height: int,
        minval: float,
        maxval: float,
        flipud: bool = False,
        history: int = 1024,
    ):
        self.width = width
        self.height = height
        self.minval = minval
        self.flipud = flipud
        self.values: deque[float] = deque(maxlen=history)
        self._maxval = maxval
        self._stream: BrailleStream | BlockCharStream | None = None
        self._style: str | None = None

    @property
    def maxval(self) -> float:
        return self._maxval

    @maxval.setter
    def maxval(self, value: float) -> None:
        self._maxval = value
        if self._stream is not None:
            self._stream.maxval = value

    def _drawn(self) -> BrailleStream | BlockCharStream:
        t = theme()
        if self._stream is None or self._style != t.design.graph:
            stream = t.stream(
                self.width, self.height, self.minval, self._maxval, self.flipud
            )
            for value in list(self.values)[-(2 * self.width + 1) :]:
                stream.add_value(value)
            self._stream, self._style = stream, t.design.graph
        return self._stream

    def add_value(self, value: float) -> None:
        self.values.append(value)
        if self._stream is not None and self._style == theme().design.graph:
            self._stream.add_value(value)

    @property
    def graph(self) -> list[str]:
        return self._drawn().graph

    def reset_width(self, width: int) -> None:
        self.width = width
        if self._stream is not None:
            self._stream.reset_width(width)

    def reset_height(self, height: int) -> None:
        self.height = height
        if self._stream is not None:
            self._stream.reset_height(height)
