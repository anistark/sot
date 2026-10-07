"""Base for every SOT widget."""

from __future__ import annotations

from typing import Callable, ClassVar

from textual.timer import Timer
from textual.widget import Widget


class SotWidget(Widget):
    """Keeps listed state across rebuilds and polls on timers its screen can
    pause while hidden.

    Name the attributes to keep in ``STATE``, call ``restore_state()`` at the
    start of ``on_mount``, and poll with ``every()`` instead of
    ``set_interval()``.
    """

    STATE: ClassVar[tuple[str, ...]] = ()

    def _store(self) -> dict | None:
        return getattr(self.app, "widget_state", None)

    def _state_key(self) -> str:
        return self.id or type(self).__name__

    def restore_state(self) -> bool:
        store = self._store()
        saved = store.pop(self._state_key(), None) if store is not None else None
        if not saved:
            return False
        for name, value in saved.items():
            setattr(self, name, value)
        return True

    def on_unmount(self) -> None:
        store = self._store()
        if store is not None and self.STATE:
            store[self._state_key()] = {
                name: getattr(self, name) for name in self.STATE if hasattr(self, name)
            }

    def every(self, seconds: float, callback: Callable[[], object]) -> Timer:
        timer = self.set_interval(seconds, callback)
        self._polls = [*getattr(self, "_polls", []), (timer, callback)]
        return timer

    def pause_polling(self) -> None:
        for timer, _ in getattr(self, "_polls", []):
            timer.pause()
        self._paused = True

    def resume_polling(self) -> None:
        if not getattr(self, "_paused", False):
            return
        self._paused = False
        for timer, callback in getattr(self, "_polls", []):
            callback()
            timer.resume()
