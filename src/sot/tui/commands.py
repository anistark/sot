"""Command palette: go to a view, find a process or volume, act on a process."""

from __future__ import annotations

from functools import partial
from typing import Callable

from textual.command import DiscoveryHit, Hit, Hits, Provider

from .._collectors import process_sampler
from ..disk.volumes import get_volume_info
from .components.process_table import ProcessTable
from .keymap import VIEWS
from .messages import ProcessAction, Reveal

MAX_PROCESS_HITS = 20


class SotCommands(Provider):
    def _post(self, message) -> None:
        self.app.post_message(message)

    def _views(self) -> list[tuple[str, Callable[[], object], str]]:
        return [
            (
                f"Go to {label}",
                partial(self.app.run_action, f"switch_mode('{mode}')"),
                f"Switch to the {label.lower()} view",
            )
            for mode, label in VIEWS.items()
        ]

    def _process_actions(self) -> list[tuple[str, Callable[[], object], str]]:
        table = self.screen.focused
        if not isinstance(table, ProcessTable):
            return []
        proc = table.selected_process()
        if proc is None:
            return []
        name, pid = proc.get("name") or "process", proc["pid"]
        return [
            (
                f"Kill {name} ({pid})",
                partial(self._post, ProcessAction("kill", proc)),
                "Send SIGKILL after confirming",
            ),
            (
                f"Terminate {name} ({pid})",
                partial(self._post, ProcessAction("terminate", proc)),
                "Send SIGTERM after confirming",
            ),
            (f"Copy PID {pid}", partial(self._copy, str(pid)), "Copy to clipboard"),
        ]

    def _copy(self, text: str) -> None:
        self.app.copy_to_clipboard(text)
        self.app.notify(f"Copied {text}")

    async def discover(self) -> Hits:
        for title, callback, help_text in [*self._views(), *self._process_actions()]:
            yield DiscoveryHit(title, callback, help=help_text)

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for title, callback, help_text in [*self._views(), *self._process_actions()]:
            if (score := matcher.match(title)) > 0:
                yield Hit(score, matcher.highlight(title), callback, help=help_text)

        processes = []
        for proc in process_sampler.sample():
            text = f"{proc.get('name') or ''} {proc['pid']}"
            if (score := matcher.match(text)) > 0:
                processes.append((score, text, proc))
        processes.sort(key=lambda hit: hit[0], reverse=True)
        for score, text, proc in processes[:MAX_PROCESS_HITS]:
            reveal = Reveal("processes", "proc-table", str(proc["pid"]))
            yield Hit(
                score,
                matcher.highlight(text),
                partial(self._post, reveal),
                help="Show in Processes",
            )

        for volume in get_volume_info():
            text = f"{volume['volume_name']} {volume['disk_id']}"
            if (score := matcher.match(text)) > 0:
                reveal = Reveal("disks", "volume-list", volume["disk_id"])
                yield Hit(
                    score,
                    matcher.highlight(text),
                    partial(self._post, reveal),
                    help="Show in Disks",
                )
