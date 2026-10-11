import pytest

from sot.tui import zoom


@pytest.fixture(autouse=True)
def _isolated_user_dirs(tmp_path, monkeypatch):
    """Keep tests away from the real config and remembered theme."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("SOT_THEME", raising=False)


@pytest.fixture(autouse=True)
def _reset_zoom():
    yield
    zoom.set_level(0)
