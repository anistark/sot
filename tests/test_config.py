import asyncio

import pytest

from sot import _config, _theme
from sot._app import run
from sot.tui import refresh


@pytest.fixture(autouse=True)
def _restore_theme():
    yield
    _theme.set_theme(_theme.DEFAULT_THEME)


def write_config(text: str):
    path = _config.config_path()
    path.parent.mkdir(parents=True)
    path.write_text(text)


def test_config_values_are_read_and_bad_ones_reported():
    write_config(
        'theme = "cyberpunk"\n'
        'default_view = "nowhere"\n'
        'net = "en9"\n'
        "[refresh]\ncpu = 0.5\nmemory = -1\nwhatever = 3\n"
        '[keymap]\n"sot.process.kill" = "ctrl+k"\n"sot.quit" = 5\n'
    )
    config = _config.load_config()
    assert config.theme == "cyberpunk"
    assert config.default_view is None
    assert config.net == "en9"
    assert config.refresh == {"CPU": 0.5}
    assert config.keymap == {"sot.process.kill": "ctrl+k"}
    assert len(config.warnings) == 4


def test_broken_toml_is_reported_not_fatal():
    write_config("theme = ")
    config = _config.load_config()
    assert config.theme is None
    assert config.warnings


def test_refresh_overrides_apply(monkeypatch):
    monkeypatch.setattr(refresh, "CPU", refresh.CPU)
    _config.apply_refresh(_config.Config(refresh={"CPU": 0.5}))
    assert refresh.CPU == 0.5


@pytest.mark.parametrize(
    "argv, env, config, remembered, expected",
    [
        ([], None, None, None, "classic"),
        ([], None, None, "cyberpunk", "cyberpunk"),
        ([], None, "cyberpunk", "classic", "cyberpunk"),
        ([], "cyberpunk", "classic", None, "cyberpunk"),
        (["--theme", "classic"], "cyberpunk", "cyberpunk", None, "classic"),
    ],
)
def test_theme_precedence(monkeypatch, capsys, argv, env, config, remembered, expected):
    if env:
        monkeypatch.setenv("SOT_THEME", env)
    if config:
        write_config(f'theme = "{config}"\n')
    if remembered:
        _config.remember_theme(remembered)
    assert run([*argv, "--version"]) == 0
    assert _theme.theme().name == expected


def test_config_path_and_keys_are_printed(capsys):
    assert run(["--config-path"]) == 0
    assert str(_config.config_path()) in capsys.readouterr().out
    assert run(["--keys"]) == 0
    assert "sot.process.kill" in capsys.readouterr().out


def test_picking_a_theme_is_remembered():
    from sot.tui.base import SotBaseApp

    async def main():
        app = SotBaseApp()
        async with app.run_test() as pilot:
            app.theme = "cyberpunk"
            await pilot.pause()

    asyncio.run(main())
    assert _config.remembered_theme() == "cyberpunk"


def test_config_keymap_remaps_and_reports_unknown_ids():
    from sot.tui.app import SotApp

    async def main():
        app = SotApp(keymap={"sot.view.processes": "p", "sot.nope": "z"})
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert any("sot.nope" in str(n.message) for n in app._notifications)
            await pilot.press("p")
            for _ in range(100):
                if app.screen.MODE == "processes":
                    break
                await pilot.pause(0.05)
            assert app.screen.MODE == "processes"

    asyncio.run(main())
