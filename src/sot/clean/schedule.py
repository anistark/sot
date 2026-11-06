"""Register a job with the scheduler the OS already has.

A process sleeping in a loop dies with the next reboot, so a monthly run would
hardly ever happen. launchd and systemd keep the job across reboots and catch
up on a run the machine slept through; cron covers Linux without a user
systemd. Nothing of sot stays resident between runs.
"""

from __future__ import annotations

import os
import platform
import plistlib
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple

from .._config import config_path
from .targets import capture, run

LABEL = "dev.anirudha.sot.clean"
UNIT = "sot-clean"
CRON_TAG = "# sot clean --daemon"

DEFAULT_SCHEDULE = "hourly"

# Each name to its cron fields and launchd calendar. systemd takes the name as is.
SCHEDULES: dict[str, tuple[str, dict[str, int]]] = {
    "hourly": ("0 * * * *", {"Minute": 0}),
    "daily": ("0 0 * * *", {"Hour": 0, "Minute": 0}),
    "weekly": ("0 0 * * 1", {"Weekday": 1, "Hour": 0, "Minute": 0}),
    "monthly": ("0 0 1 * *", {"Day": 1, "Hour": 0, "Minute": 0}),
}


class SchedulerError(Exception):
    """The scheduler refused the job; the message says why."""


class Job(NamedTuple):
    every: str
    command: list[str]
    env: dict[str, str]


def _must(*commands: tuple[str, ...]) -> None:
    warnings = run(*commands, timeout=30)
    if warnings:
        raise SchedulerError(warnings[0])


class Scheduler:
    name = ""

    def usable(self) -> bool:
        raise NotImplementedError

    def location(self) -> str:
        """Where the job lives, to point people at it."""
        raise NotImplementedError

    def preview(self, job: Job) -> str:
        """What ``install`` would write."""
        raise NotImplementedError

    def install(self, job: Job) -> None:
        """Add the job, replacing the one already there."""
        raise NotImplementedError

    def remove(self) -> None:
        raise NotImplementedError

    def installed(self) -> bool:
        raise NotImplementedError

    def active(self) -> bool:
        """Whether the scheduler will really run it, not just has it on file."""
        raise NotImplementedError


class Launchd(Scheduler):
    name = "launchd"

    @property
    def path(self) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"

    @property
    def domain(self) -> str:
        return f"gui/{os.getuid()}"

    def usable(self) -> bool:
        return platform.system() == "Darwin"

    def location(self) -> str:
        return str(self.path)

    def preview(self, job: Job) -> str:
        return plistlib.dumps(
            {
                "Label": LABEL,
                "ProgramArguments": job.command,
                "EnvironmentVariables": job.env,
                "StartCalendarInterval": SCHEDULES[job.every][1],
                # ProcessType Background throttles disk reads, and a run is mostly
                # those: it took far longer than this and still hadn't finished.
                "Nice": 19,
            }
        ).decode()

    def _unload(self) -> None:
        # Fails when it isn't loaded, which is what's wanted anyway.
        run(("launchctl", "bootout", f"{self.domain}/{LABEL}"), timeout=30)

    def install(self, job: Job) -> None:
        self._unload()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.preview(job))
        try:
            _must(("launchctl", "bootstrap", self.domain, str(self.path)))
        except SchedulerError:
            # Left here it would load at the next login, after we reported failure.
            self.path.unlink(missing_ok=True)
            raise

    def remove(self) -> None:
        self._unload()
        self.path.unlink(missing_ok=True)

    def installed(self) -> bool:
        return self.path.exists()

    def active(self) -> bool:
        return capture("launchctl", "print", f"{self.domain}/{LABEL}") is not None


def _unit_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + escaped.replace("%", "%%") + '"'


class Systemd(Scheduler):
    name = "systemd"

    @property
    def folder(self) -> Path:
        return config_path().parent.parent / "systemd" / "user"

    @property
    def service(self) -> Path:
        return self.folder / f"{UNIT}.service"

    @property
    def timer(self) -> Path:
        return self.folder / f"{UNIT}.timer"

    def usable(self) -> bool:
        # Installed isn't enough: containers and bare SSH logins have no user bus.
        return capture("systemctl", "--user", "show-environment") is not None

    def location(self) -> str:
        return str(self.timer)

    def _service_text(self, job: Job) -> str:
        env = [
            f"Environment={_unit_quote(f'{name}={value}')}"
            for name, value in job.env.items()
        ]
        command = " ".join(_unit_quote(a).replace("$", "$$") for a in job.command)
        return "\n".join(
            [
                "[Unit]",
                "Description=sot clean, without asking",
                "",
                "[Service]",
                "Type=oneshot",
                "Nice=19",
                "IOSchedulingClass=idle",
                *env,
                f"ExecStart={command}",
                "",
            ]
        )

    def _timer_text(self, job: Job) -> str:
        return "\n".join(
            [
                "[Unit]",
                f"Description=Run sot clean {job.every}",
                "",
                "[Timer]",
                f"OnCalendar={job.every}",
                "Persistent=true",
                "",
                "[Install]",
                "WantedBy=timers.target",
                "",
            ]
        )

    def preview(self, job: Job) -> str:
        return f"{self._service_text(job)}\n{self._timer_text(job)}"

    def install(self, job: Job) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        self.service.write_text(self._service_text(job))
        self.timer.write_text(self._timer_text(job))
        _must(
            ("systemctl", "--user", "daemon-reload"),
            ("systemctl", "--user", "enable", f"{UNIT}.timer"),
            # A timer already running keeps its old calendar until restarted.
            ("systemctl", "--user", "restart", f"{UNIT}.timer"),
        )

    def remove(self) -> None:
        run(("systemctl", "--user", "disable", "--now", f"{UNIT}.timer"), timeout=30)
        self.service.unlink(missing_ok=True)
        self.timer.unlink(missing_ok=True)
        run(("systemctl", "--user", "daemon-reload"), timeout=30)

    def installed(self) -> bool:
        return self.timer.exists()

    def active(self) -> bool:
        return capture("systemctl", "--user", "is-active", f"{UNIT}.timer") is not None


class Cron(Scheduler):
    name = "cron"

    def usable(self) -> bool:
        return platform.system() != "Darwin" and bool(shutil.which("crontab"))

    def location(self) -> str:
        return "your crontab"

    def _crontab(self, flag: str, text: str | None = None) -> tuple[int, str, str]:
        try:
            done = subprocess.run(
                ["crontab", flag],
                input=text,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise SchedulerError(f"crontab failed: {error}") from error
        return done.returncode, done.stdout, done.stderr.strip()

    def _lines(self) -> list[str]:
        """The crontab now. Anything but "there is none" stops us replacing it."""
        code, out, err = self._crontab("-l")
        if code == 0:
            return out.splitlines()
        if "no crontab" in err.lower():
            return []
        raise SchedulerError(f"Couldn't read your crontab: {err}")

    def _write(self, lines: list[str]) -> None:
        code, _, err = self._crontab("-", "".join(f"{line}\n" for line in lines))
        if code != 0:
            raise SchedulerError(f"Couldn't write your crontab: {err}")

    def preview(self, job: Job) -> str:
        env = [f"{name}={value}" for name, value in job.env.items()]
        command = shlex.join(["nice", "-n", "19", "env", *env, *job.command])
        # Cron reads a bare % as a newline.
        escaped = command.replace("%", "\\%")
        return f"{SCHEDULES[job.every][0]} {escaped} {CRON_TAG}"

    def _others(self) -> list[str]:
        return [line for line in self._lines() if not line.endswith(CRON_TAG)]

    def install(self, job: Job) -> None:
        self._write([*self._others(), self.preview(job)])

    def remove(self) -> None:
        self._write(self._others())

    def installed(self) -> bool:
        return any(line.endswith(CRON_TAG) for line in self._lines())

    def active(self) -> bool:
        return self.installed()


def schedulers() -> list[Scheduler]:
    """The schedulers this machine can use, the preferred one first."""
    return [s for s in (Launchd(), Systemd(), Cron()) if s.usable()]
