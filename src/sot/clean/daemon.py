"""``sot clean --daemon`` schedules cleaning, ``--scheduled`` is each run.

Nobody is there to read a table or answer a prompt during a run, so it does
less than ``sot clean``: see ``unattended``.
"""

from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markup import escape

from .._config import (
    clean_log_path,
    remember_clean_schedule,
    remembered_clean_schedule,
)
from .._theme import theme
from ..update.install import PIPX_RUN, UVX, detect_install
from .agents import CACHE_ROOTS, without_consent_roots
from .cli import _get_targets, _is_elevated, _sizeof_fmt, clean_target, scan_targets
from .schedule import (
    DEFAULT_SCHEDULE,
    SCHEDULES,
    Job,
    Scheduler,
    SchedulerError,
    schedulers,
)
from .targets import CleanTarget, idle_paths, target_paths

# Long enough for a weekend away from a project to leave its caches warm.
IDLE_DAYS = 3
LOG_LINES = 2000
WARNINGS_PER_RUN = 20

# The job doesn't start from your shell, so what the targets read comes along.
JOB_ENV = (
    "PATH",
    "XDG_STATE_HOME",
    *(root.env for root in CACHE_ROOTS.values() if root.env),
)


def unattended(targets: list[CleanTarget], force: bool = False) -> list[CleanTarget]:
    """What a run can clean with nobody watching.

    ``targets`` must have been through ``_separate``. It's what keeps
    ``~/Library/Caches`` out of a cache listed on its own row, and that has to
    hold for the rows dropped here too.

    Nothing marked ``attended`` goes, and nothing needing sudo, since the job
    runs as you. What's left goes only as whole entries idle for ``IDLE_DAYS``,
    so running apps and warm builds aren't cleared under their feet; ``force``
    lifts that, as it does for other data in use. An ``action`` is the tool's
    own cleanup, and ``older_than`` is its own age check.
    """
    safe = []
    for target in targets:
        if target.attended or target.requires_sudo or target.review:
            continue
        if not force and target.action is None and target.older_than is None:
            paths = target_paths(target)
            target = target._replace(
                path=[p for path in paths for p in idle_paths(path, IDLE_DAYS)]
            )
        safe.append(target)
    return safe


def _cleanable(args) -> list[dict]:
    projects = Path(args.projects).expanduser().resolve() if args.projects else None
    with without_consent_roots():
        found = _get_targets(args.force, args.privacy, projects)
    results = scan_targets(unattended(found, args.force)).values()
    return [r for r in results if r["exists"] and r["size"] > 0]


def _log_lines() -> list[str]:
    text = clean_log_path().read_text(encoding="utf-8", errors="replace")
    return text.splitlines()


def _log(lines: list[str]) -> None:
    path = clean_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        old = _log_lines() if path.exists() else []
        kept = [*old, *lines][-LOG_LINES:]
        path.write_text("\n".join(kept) + "\n", encoding="utf-8", errors="replace")
    except OSError:
        pass


def _now() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def _clean(args) -> None:
    freed = 0
    cleaned = []
    warnings: list[str] = []
    for result in _cleanable(args):
        target = result["target"]
        done, problems = clean_target(target, False, result["size"])
        freed += done
        warnings.extend(problems)
        if done:
            cleaned.append(f"  {_sizeof_fmt(done):>9}  {target.name}")

    summary = f"{_now()} freed {_sizeof_fmt(freed)}"
    if warnings:
        summary += f", {len(warnings)} skipped"
    hidden = len(warnings) - WARNINGS_PER_RUN
    more = [f"  ... and {hidden} more"] if hidden > 0 else []
    shown = [f"  {warning}" for warning in warnings[:WARNINGS_PER_RUN]]
    _log([summary, *cleaned, *shown, *more])


def scheduled_clean(args) -> int:
    """One run: nothing is asked, and what happened goes to the log."""
    if args.dry_run:
        results = _cleanable(args)
        for result in results:
            print(f"{_sizeof_fmt(result['size']):>9}  {result['target'].name}")
        total = sum(result["size"] for result in results)
        # Tools like `uv cache prune` keep what's used, so sizes are upper limits.
        print(f"A scheduled run frees up to {_sizeof_fmt(total)}. Nothing was deleted.")
        return 0

    try:
        _clean(args)
    except Exception as error:  # the log is the only place anyone will look
        _log([f"{_now()} failed: {error!r}"])
        return 1
    return 0


def _job(args, every: str) -> Job:
    sot = shutil.which("sot") or os.path.abspath(sys.argv[0])
    command = [sot, "clean", "--scheduled"]
    if args.force:
        command.append("--force")
    if args.privacy:
        command.append("--privacy")
    if args.projects:
        # Schedulers start jobs from / or from home, not from here.
        command += ["--projects", str(Path(args.projects).expanduser().resolve())]
    env = {name: os.environ[name] for name in JOB_ENV if os.environ.get(name)}
    return Job(every, command, env)


def _say(text: str) -> None:
    Console().print(text, highlight=False, soft_wrap=True)


def _fail(text: str) -> int:
    _say(f"[{theme().colors.danger}]❌ {escape(text)}[/]")
    return 1


def _start(args, every: str) -> int:
    c = theme().colors
    found = schedulers()
    if not found:
        return _fail("Scheduling needs launchd, systemd or cron, and none is here.")
    if detect_install().manager in (UVX, PIPX_RUN):
        return _fail(
            "This is a cached copy of sot. Install it to run it on a schedule."
        )

    scheduler = found[0]
    job = _job(args, every)
    if args.dry_run:
        _say(f"Would run [{c.ok}]{every}[/] through {scheduler.name}:")
        _say(f"[{c.muted}]{escape(scheduler.location())}[/]\n")
        Console().print(
            scheduler.preview(job), markup=False, highlight=False, soft_wrap=True
        )
        _say(f"[{c.warn}]Dry run mode - nothing was changed[/]")
        return 0

    try:
        for other in found[1:]:
            if other.installed():
                other.remove()
        scheduler.install(job)
    except (SchedulerError, OSError) as error:
        return _fail(f"{scheduler.name} didn't take the job: {error}")

    remember_clean_schedule(every)
    _say(f"✅ sot clean now runs [{c.ok}]{every}[/] through {scheduler.name}")
    idle = "" if args.force else f", and only clears what's idle for {IDLE_DAYS} days"
    _say(f"[{c.muted}]It leaves the Trash and Mail attachments alone{idle}.[/]")
    if args.force or args.privacy:
        _say(f"[{c.warn}]⚠  Every run includes what you added with flags.[/]")
    _say(
        f"[{c.muted}]See what a run would do: sot clean --scheduled --dry-run\n"
        "Check on it: sot clean -d status\nTurn it off: sot clean -d stop[/]"
    )
    return 0


def _installed() -> list[Scheduler]:
    return [scheduler for scheduler in schedulers() if scheduler.installed()]


def _stop(args) -> int:
    c = theme().colors
    try:
        installed = _installed()
        if not installed:
            _say(f"[{c.muted}]Nothing is scheduled.[/]")
            return 0
        if args.dry_run:
            for scheduler in installed:
                _say(f"Would remove {escape(scheduler.location())}")
            _say(f"[{c.warn}]Dry run mode - nothing was changed[/]")
            return 0
        for scheduler in installed:
            scheduler.remove()
    except (SchedulerError, OSError) as error:
        return _fail(f"Couldn't stop it: {error}")
    _say("✅ Scheduled cleaning is off")
    return 0


def _last_run() -> str | None:
    """The newest summary line: the log's only lines with no indent."""
    try:
        lines = _log_lines()
    except OSError:
        return None
    return next((line for line in reversed(lines) if not line.startswith(" ")), None)


def _status() -> int:
    c = theme().colors
    try:
        installed = _installed()
        if not installed:
            _say(f"[{c.muted}]Nothing is scheduled. Start with: sot clean -d[/]")
            return 0
        scheduler = installed[0]
        active = scheduler.active()
    except (SchedulerError, OSError) as error:
        return _fail(f"Couldn't check on it: {error}")

    every = remembered_clean_schedule() or "on a schedule"
    if active:
        _say(f"✅ sot clean runs [{c.ok}]{every}[/] through {scheduler.name}")
    else:
        _say(
            f"[{c.warn}]⚠  {scheduler.name} has the job but won't run it. "
            "Turn it on again with: sot clean -d[/]"
        )
    _say(f"Job:      [{c.muted}]{escape(scheduler.location())}[/]")
    _say(f"Log:      [{c.muted}]{escape(str(clean_log_path()))}[/]")
    _say(f"Last run: [{c.muted}]{escape(_last_run() or 'not yet')}[/]")
    return 0


def daemon_command(args, configured: str | None = None) -> int:
    """Handle ``--daemon``; a schedule from the flag beats ``configured``."""
    if args.daemon == "status":
        return _status()
    if _is_elevated():
        return _fail("Run this without sudo: the job runs as you, not as root.")
    if args.daemon == "stop":
        return _stop(args)
    every = args.daemon if args.daemon in SCHEDULES else None
    return _start(args, every or configured or DEFAULT_SCHEDULE)
