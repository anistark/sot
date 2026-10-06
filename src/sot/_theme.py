"""
Themes for the TUI.

A theme pairs ``Colors`` (semantic color roles) with a ``Design`` (how
components are drawn: frames, graphs, meters, indicators, logo, ...). Widgets
ask the active theme via ``theme()`` instead of hardcoding either, so a new
theme only overrides the fields that differ from the classic defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from rich.box import ROUNDED, SQUARE, Box
from rich.color import Color, blend_rgb
from rich.text import Text
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
    box: Box = SQUARE
    # Frame for the standalone viewers (`sot ps`, `sot disk`).
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
    cursor: str = "▶ "
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
    css: str = ""

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

    def row_styles(self) -> list[str] | None:
        return ["", f"on {self.colors.stripe}"] if self.design.stripes else None


@lru_cache(maxsize=256)
def _blend(base: str, target: str, amount: float) -> str:
    rgb = blend_rgb(
        Color.parse(base).get_truecolor(), Color.parse(target).get_truecolor(), amount
    )
    return Color.from_triplet(rgb).name


CLASSIC = SotTheme(name="classic")

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
        box=CYBER_BOX,
        app_box=CYBER_BOX,
        inner_box=RAIL_BOX,
        title="tag",
        upper_titles=True,
        separator=" // ",
        graph="blocks",
        graph_heat=0.8,
        meter=Meter(fill="▰", empty="▱"),
        indicators=("◆", "◈", "◇", "✕"),
        cursor="▸ ",
        stripes=True,
        logo=CYBER_LOGO,
        tagline="// SYSTEM OBSERVATION TOOL",
        glitch=True,
    ),
    textual=TextualTheme(
        name="cyberpunk-2077",
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
    css=f"""
    Header {{
        background: {_CP_YELLOW};
        color: {_CP_BG};
        text-style: bold;
    }}
    HeaderClock {{
        background: {_CP_PINK};
        color: {_CP_BG};
    }}
    ListView > ListItem.-highlight {{
        background: {_CP_CYAN} 12%;
    }}
    ListView:focus > ListItem.-highlight {{
        background: {_CP_CYAN} 28%;
    }}
    """,
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


def apply_to_app(app) -> None:
    """Register the active theme's Textual theme and CSS on an App (pre-run)."""
    t = theme()
    if t.css:
        app.CSS = type(app).CSS + t.css
    if t.textual is not None:
        app.register_theme(t.textual)
        app.theme = t.textual.name
