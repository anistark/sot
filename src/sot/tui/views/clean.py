"""Clean: scan caches and logs, pick targets, clean them."""

from __future__ import annotations

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal

from ..._helpers import sizeof_fmt
from ..._theme import theme
from ...clean.cli import _get_targets, _is_elevated, clean_target, scan_target
from ...widgets.base_widget import BaseWidget
from ...widgets.confirmation_modal import ConfirmModal
from .. import keymap
from ..components.table import SotTable, cell
from ..screen import SotScreen


class TargetTable(SotTable):
    BINDINGS = [
        *keymap.LIST,
        Binding("space", "toggle_target", "Toggle", id="sot.clean.toggle"),
        Binding("a", "toggle_all", "All/none", id="sot.clean.all"),
        Binding("d", "dry_run", "Dry run", id="sot.clean.dry_run"),
        Binding("c", "clean", "Clean", id="sot.clean.run"),
        Binding("r", "rescan", "Rescan", id="sot.clean.rescan"),
    ]

    def __init__(self, **kwargs):
        super().__init__("Cleaning targets", **kwargs)

    def on_mount(self) -> None:
        for key, label in (
            ("pick", ""),
            ("name", "Target"),
            ("size", "Size"),
            ("sudo", "Sudo"),
            ("description", "Description"),
        ):
            self.add_column(label, key=key)
        self.reload()

    @property
    def view(self) -> CleanScreen:
        assert isinstance(self.screen, CleanScreen)
        return self.screen

    def reload(self) -> None:
        if not isinstance(self.screen, CleanScreen):
            return
        c = theme().colors
        view = self.view
        rows = []
        for name, result in view.results.items():
            text = f"{name} {result['target'].description}".lower()
            if self.filter_text and self.filter_text.lower() not in text:
                continue
            target, size = result["target"], result["size"]
            picked = name in view.selected
            if not result["exists"]:
                size_cell = cell("n/a", c.muted, "right")
            elif size == 0:
                size_cell = cell("empty", c.muted, "right")
            else:
                size_cell = cell(sizeof_fmt(size, fmt=".1f"), justify="right")
            rows.append(
                (
                    name,
                    (
                        cell("✓" if picked else "○", c.ok if picked else c.muted),
                        cell(name, c.text),
                        size_cell,
                        cell("✓" if target.requires_sudo else "-", c.warn),
                        cell(target.description, c.muted),
                    ),
                )
            )
        self.set_rows(rows)

    def action_toggle_target(self) -> None:
        if self.selected_row is not None:
            self.view.toggle(self.selected_row)

    def action_toggle_all(self) -> None:
        self.view.toggle_all()

    def action_dry_run(self) -> None:
        self.view.dry_run = not self.view.dry_run
        self.view.report = ""
        self.view.changed()

    def action_clean(self) -> None:
        self.view.clean()

    def action_rescan(self) -> None:
        self.view.scan()


class CleanSummary(BaseWidget):
    DEFAULT_CSS = """
    CleanSummary {
        width: 40;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(title="Summary", **kwargs)

    def redraw(self, view: CleanScreen) -> None:
        c = theme().colors
        text = Text()
        if view.busy:
            text.append(f"{view.busy}…\n\n", style=c.accent)
        picked = [view.results[name] for name in view.selected]
        total = sum(r["size"] for r in picked)
        text.append("Selected  ", style=c.label)
        text.append(f"{len(picked)} targets, {sizeof_fmt(total, fmt='.1f')}\n")
        text.append("Mode      ", style=c.label)
        if view.dry_run:
            text.append("dry run (nothing is deleted)\n", style=c.warn)
        else:
            text.append("clean\n", style=c.text)
        if not view.elevated:
            text.append("\nsudo targets are skipped; run with sudo to include them\n")
        if view.report:
            text.append(f"\n{view.report}\n", style=c.ok)
        for warning in view.warnings[-5:]:
            text.append(f"⚠ {warning}\n", style=c.warn)
        text.append("\nspace toggle · a all · d dry run · c clean", style=c.muted)
        self.update_panel_content(text)


class CleanScreen(SotScreen):
    MODE = "clean"

    DEFAULT_CSS = """
    CleanScreen #target-table {
        width: 1fr;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.results: dict[str, dict] = {}
        self.selected: set[str] = set()
        self.dry_run = False
        self.elevated = _is_elevated()
        self.busy = ""
        self.report = ""
        self.warnings: list[str] = []

    def compose_view(self) -> ComposeResult:
        with Horizontal():
            yield TargetTable(id="target-table")
            yield CleanSummary(id="clean-summary")

    def on_mount(self) -> None:
        self.query_one("#target-table").focus()
        if not self.results:
            self.scan()
        self.changed()

    def rebuilt(self) -> None:
        self.changed()

    def changed(self) -> None:
        self.query_one(TargetTable).reload()
        self.query_one(CleanSummary).redraw(self)

    def _cleanable(self, name: str) -> bool:
        result = self.results[name]
        sudo_ok = self.elevated or not result["target"].requires_sudo
        return result["exists"] and result["size"] > 0 and sudo_ok

    def toggle(self, name: str) -> None:
        self.report = ""
        if name in self.selected:
            self.selected.discard(name)
        elif self._cleanable(name):
            self.selected.add(name)
        self.changed()

    def toggle_all(self) -> None:
        cleanable = {name for name in self.results if self._cleanable(name)}
        self.selected = set() if self.selected == cleanable else cleanable
        self.report = ""
        self.changed()

    @work(thread=True, exclusive=True, group="clean")
    def scan(self) -> None:
        self.app.call_from_thread(self._set_busy, "Scanning")
        results = {}
        for target in _get_targets():
            results[target.name] = scan_target(target)
        self.app.call_from_thread(self._scanned, results)

    def _set_busy(self, busy: str) -> None:
        self.busy = busy
        self.changed()

    def _scanned(self, results: dict[str, dict]) -> None:
        self.results = results
        self.selected = {name for name in results if self._cleanable(name)}
        self.busy = ""
        self.changed()

    def clean(self) -> None:
        if self.busy or not self.selected:
            return
        total = sum(self.results[name]["size"] for name in self.selected)
        if self.dry_run:
            self.report = f"Dry run: would free {sizeof_fmt(total, fmt='.1f')}"
            self.changed()
            return

        def confirmed(ok: bool | None) -> None:
            if ok:
                self._clean([self.results[n]["target"] for n in sorted(self.selected)])

        self.app.push_screen(
            ConfirmModal(
                f"Clean {len(self.selected)} targets?",
                f"{sizeof_fmt(total, fmt='.1f')} will be deleted. This can't be undone.",
                confirm_label="Clean",
            ),
            confirmed,
        )

    @work(thread=True, exclusive=True, group="clean")
    def _clean(self, targets: list) -> None:
        freed, warnings = 0, []
        for target in targets:
            self.app.call_from_thread(self._set_busy, f"Cleaning {target.name}")
            target_freed, target_warnings = clean_target(target, self.elevated)
            freed += target_freed
            warnings.extend(target_warnings)
        self.app.call_from_thread(self._cleaned, freed, warnings)

    def _cleaned(self, freed: int, warnings: list[str]) -> None:
        self.report = f"Freed {sizeof_fmt(freed, fmt='.1f')}"
        self.warnings = warnings
        self.busy = ""
        self.notify(self.report)
        self.scan()
