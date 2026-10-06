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
        name="custom", design=_theme.Design(cursor="> ", graph="blocks")
    )
    assert custom.colors == _theme.CLASSIC.colors
    assert custom.design.box is _theme.CLASSIC.design.box
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


def test_row_styles_only_when_striped():
    assert _theme.CLASSIC.row_styles() is None
    assert _theme.CYBERPUNK.row_styles() == [
        "",
        f"on {_theme.CYBERPUNK.colors.stripe}",
    ]


def test_usage_style_follows_theme():
    _theme.set_theme("cyberpunk")
    assert usage_style(50) == _theme.CYBERPUNK.colors.usage[0]
    assert usage_style(96) == _theme.CYBERPUNK.colors.usage[2]


def test_cli_rejects_unknown_theme_from_env(monkeypatch, capsys):
    from sot._app import run

    monkeypatch.setenv("SOT_THEME", "vaporwave")
    assert run(["--version"]) == 1
    assert "Unknown theme" in capsys.readouterr().out
