import re
from pathlib import Path

import pytest

from sot import _theme
from sot.blockchar_stream import BlockCharStream
from sot.braille_stream import BrailleStream
from sot.disk.volumes import usage_style


@pytest.fixture(autouse=True)
def _restore_theme():
    yield
    _theme.set_theme(_theme.DEFAULT_THEME)


def test_default_is_classic():
    assert _theme.theme() is _theme.CLASSIC


def test_unknown_theme_raises():
    with pytest.raises(ValueError, match="Unknown theme"):
        _theme.set_theme("vaporwave")


def test_classic_title():
    t = _theme.CLASSIC
    assert t.title("CPU") == "[bold]CPU[/]"
    assert t.title("CPU", "Apple M1") == "[bold]CPU[/] - Apple M1"


def test_cyberpunk_title_is_tagged_and_uppercased():
    title = _theme.CYBERPUNK.title("Memory", "16 GiB")
    assert " MEMORY " in title
    assert "16 GiB" in title


def test_custom_theme_overrides_only_what_differs():
    custom = _theme.SotTheme(
        name="custom", design=_theme.Design(stripes=True, graph="blocks")
    )
    assert custom.colors == _theme.CLASSIC.colors
    assert custom.design.frame == _theme.CLASSIC.design.frame
    assert isinstance(custom.stream(5, 2, 0, 100), BlockCharStream)


def test_stream_follows_graph_design():
    assert isinstance(_theme.CLASSIC.stream(5, 2, 0, 100), BrailleStream)
    assert isinstance(_theme.CYBERPUNK.stream(5, 2, 0, 100), BlockCharStream)


def test_meter_uses_level_glyphs_in_classic():
    assert _theme.CLASSIC.meter(0.5, 4, "red", level=1).plain == "▓▓░░"
    assert _theme.CLASSIC.meter(0.5, 4, "red").plain == "██░░"


def test_meter_segments_in_cyberpunk():
    assert _theme.CYBERPUNK.meter(0.75, 4, "red", level=3).plain == "▰▰▰▱"


def test_meter_clamps_fraction():
    assert _theme.CLASSIC.meter(1.5, 3, "red").plain == "███"
    assert _theme.CLASSIC.meter(-1, 3, "red").plain == "░░░"


def test_flat_graph_has_single_style():
    text = _theme.CLASSIC.graph(["ab", "cd"], "yellow")
    assert text.plain == "ab\ncd"
    assert str(text.style) == "yellow"


def test_heat_graph_shades_rows_toward_heat():
    text = _theme.CYBERPUNK.graph(["top", "mid", "low"], "#000000")
    styles = [str(span.style) for span in text.spans]
    assert len(styles) == 3
    assert styles[-1] == "#000000"
    assert styles[0] != styles[-1]


def test_usage_style_follows_theme():
    _theme.set_theme("cyberpunk")
    assert usage_style(50) == _theme.CYBERPUNK.colors.usage[0]
    assert usage_style(96) == _theme.CYBERPUNK.colors.usage[2]


def test_cli_rejects_unknown_theme_from_env(monkeypatch, capsys):
    from sot._app import run

    monkeypatch.setenv("SOT_THEME", "vaporwave")
    assert run(["--version"]) == 1
    assert "Unknown theme" in capsys.readouterr().out


def test_every_theme_has_a_matching_textual_theme():
    for name, t in _theme.THEMES.items():
        assert t.textual is not None
        assert t.textual.name == name


def test_classic_follows_the_terminal_palette():
    textual_theme = _theme.CLASSIC.textual
    assert textual_theme.ansi
    assert {"ansi-background", "ansi-foreground"} <= textual_theme.variables.keys()


def test_color_shortcuts():
    colors = _theme.CYBERPUNK.colors
    assert colors.ok == colors.health[0]
    assert colors.warn == colors.health[2]


def _fed(stream, values):
    for value in values:
        stream.add_value(value)
    return stream


def test_themed_stream_redraws_history_in_the_active_style():
    values = (10.0, 50.0, 90.0)
    stream = _fed(_theme.ThemedStream(4, 1, 0.0, 100.0), values)
    assert stream.graph == _fed(BrailleStream(4, 1, 0.0, 100.0), values).graph

    _theme.set_theme("cyberpunk")
    assert stream.graph == _fed(BlockCharStream(4, 1, 0.0, 100.0), values).graph

    stream.add_value(30.0)
    expected = _fed(BlockCharStream(4, 1, 0.0, 100.0), (*values, 30.0))
    assert stream.graph == expected.graph
    assert list(stream.values) == [*values, 30.0]


def test_themed_stream_resizes_and_rescales():
    stream = _fed(_theme.ThemedStream(4, 1, 0.0, 10.0), (5.0,))
    stream.reset_width(6)
    stream.maxval = 20.0
    assert len(stream.graph[0]) == 6
    assert stream.maxval == 20.0


def test_version_screen_uses_the_theme_logo(capsys):
    from sot._app import run

    assert run(["--theme", "cyberpunk", "--version"]) == 0
    assert _theme.CYBER_LOGO[0].strip() in capsys.readouterr().out


_HARDCODED_COLOR = re.compile(
    r"\[/?((bold|dim|italic|underline|reverse) )*(bright_)?"
    r"(red|green|yellow|blue|cyan|magenta|white|black)\b"
    r'|(style|border_style|header_style|complete_style|finished_style)="[^"]*\b'
    r"(bright_)?(red|green|yellow|blue|cyan|magenta|white|black)\b"
)


def test_colors_only_come_from_the_theme():
    src = Path(_theme.__file__).parent
    offenders = [
        f"{path.relative_to(src)}:{number}"
        for path in src.rglob("*.py")
        if path.name != "_theme.py"
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if _HARDCODED_COLOR.search(line)
    ]
    assert offenders == []


def test_rich_colors_map_to_textual_colors():
    assert _theme.textual_color("bright_black") == "ansi_bright_black"
    assert _theme.textual_color("#fcee0a") == "#fcee0a"
    assert _theme.textual_color("aquamarine3").startswith("#")


def test_themes_expose_their_frame_to_css():
    classic = _theme.CLASSIC.textual.variables
    cyber = _theme.CYBERPUNK.textual.variables
    assert (classic["sot-frame"], cyber["sot-frame"]) == ("solid", "outer")
    assert classic["sot-border"] == "ansi_bright_black"
    assert cyber["block-cursor-background"] == "#00f0ff"
