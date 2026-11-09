import os
import plistlib
import subprocess
import time
from argparse import Namespace
from pathlib import Path

import pytest

from sot import _config
from sot._app import build_parser, run
from sot.clean import cli, daemon, schedule, targets
from sot.clean.agents import expand_paths, resolve_roots, without_consent_roots
from sot.clean.apps import APP_DIRS, app_caches
from sot.clean.devtools import DEV_CACHES, REVIEW
from sot.clean.schedule import SCHEDULES, Cron, Job, Launchd, SchedulerError, Systemd
from sot.clean.system import SYSTEM
from sot.clean.targets import CleanTarget, idle_paths

OLD = time.time() - 30 * 86400
JOB = Job("daily", ["/bin/sot", "clean", "--scheduled"], {"PATH": "/bin"})


def args(**overrides) -> Namespace:
    defaults = {
        "daemon": "start",
        "dry_run": False,
        "force": False,
        "privacy": False,
        "projects": None,
    }
    return Namespace(**{**defaults, **overrides})


def backdate(path: Path) -> None:
    """Make ``path`` and all it holds look untouched for a month.

    ctime can't be set, so the idle check is pointed past it by ``aged``.
    """
    for item in [path, *path.rglob("*")]:
        os.utime(item, (OLD, OLD), follow_symlinks=False)


class OsView:
    """``os`` as one module sees it, so swapping a call there leaves the rest
    of the process, pathlib included, on the real one."""

    def __getattr__(self, name):
        return getattr(os, name)


@pytest.fixture
def aged(monkeypatch):
    """Judge age by mtime alone, since tests can't backdate a ctime."""
    monkeypatch.setattr(targets, "os", OsView())
    real = os.lstat

    class Stat:
        def __init__(self, st):
            self._st = st

        def __getattr__(self, name):
            return getattr(self._st, name)

        @property
        def st_ctime(self):
            return self._st.st_mtime

    monkeypatch.setattr(targets.os, "lstat", lambda p: Stat(real(p)))
    real_scandir = os.scandir

    class Entry:
        def __init__(self, entry):
            self._entry = entry

        def __getattr__(self, name):
            return getattr(self._entry, name)

        def stat(self, follow_symlinks=True):
            return Stat(self._entry.stat(follow_symlinks=follow_symlinks))

    class Scan:
        def __init__(self, path):
            self._scan = real_scandir(path)

        def __enter__(self):
            return (Entry(entry) for entry in self._scan)

        def __exit__(self, *exc):
            self._scan.close()

    monkeypatch.setattr(targets.os, "scandir", Scan)


def cache_with(tmp_path: Path) -> Path:
    """A cache holding one idle entry and one in use."""
    cache = tmp_path / "cache"
    (cache / "idle").mkdir(parents=True)
    (cache / "idle" / "blob").write_bytes(b"x" * 8192)
    backdate(cache / "idle")
    (cache / "hot").mkdir()
    (cache / "hot" / "old").write_bytes(b"x" * 8192)
    (cache / "hot" / "new").write_bytes(b"x" * 8192)
    os.utime(cache / "hot" / "old", (OLD, OLD))
    return cache


def test_an_entry_goes_only_if_nothing_in_it_changed(tmp_path, aged):
    cache = cache_with(tmp_path)

    assert idle_paths(cache, 3) == [cache / "idle"]


def test_one_new_file_deep_down_keeps_the_whole_entry(tmp_path, aged):
    deep = tmp_path / "cache" / "pkg" / "a" / "b"
    deep.mkdir(parents=True)
    (deep / "old").touch()
    backdate(tmp_path / "cache")
    (deep / "new").touch()
    os.utime(deep, (OLD, OLD))

    assert idle_paths(tmp_path / "cache", 3) == []


def test_ctime_counts_for_files_unpacked_with_old_dates(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "unpacked").touch()
    backdate(cache)

    # mtime says a month, ctime says just now.
    assert idle_paths(cache, 3) == []


def test_a_file_target_is_judged_itself(tmp_path, aged):
    old, new = tmp_path / "old", tmp_path / "new"
    old.touch()
    new.touch()
    os.utime(old, (OLD, OLD))

    assert idle_paths(old, 3) == [old]
    assert idle_paths(new, 3) == []
    assert idle_paths(tmp_path / "missing", 3) == []


def test_what_cant_be_read_is_left_alone(tmp_path, aged, monkeypatch):
    cache = tmp_path / "cache"
    (cache / "locked").mkdir(parents=True)
    (cache / "open").mkdir()
    backdate(cache)
    allowed = targets.os.scandir

    def refuse(path):
        if str(path).endswith("locked"):
            raise PermissionError(path)
        return allowed(path)

    monkeypatch.setattr(targets.os, "scandir", refuse)

    # Listing the cache still works, so only the locked entry drops out.
    assert idle_paths(cache, 3) == [cache / "open"]


def test_unattended_drops_what_needs_a_person(tmp_path):
    keep = CleanTarget("Keep", tmp_path, "test")
    targets = [
        CleanTarget("Trash", tmp_path, "test", attended=True),
        CleanTarget("Sudo", tmp_path, "test", requires_sudo=True),
        CleanTarget("Review", tmp_path, "test", review=True),
        keep,
    ]

    assert [t.name for t in daemon.unattended(targets)] == ["Keep"]
    assert [t.name for t in daemon.unattended(targets, force=True)] == ["Keep"]


def test_unattended_narrows_paths_to_idle_entries(tmp_path, aged):
    cache = cache_with(tmp_path)

    (target,) = daemon.unattended([CleanTarget("Cache", cache, "test")])

    assert target.path == [cache / "idle"]


def test_force_lifts_the_idle_check(tmp_path):
    cache = cache_with(tmp_path)

    (target,) = daemon.unattended([CleanTarget("Cache", cache, "test")], force=True)

    assert target.path == cache


def test_actions_and_age_limits_keep_their_own_rules(tmp_path):
    temp = CleanTarget("Temp", tmp_path, "test", older_than=3)
    tool = CleanTarget("Tool", tmp_path, "test", action=lambda: [])

    assert daemon.unattended([temp, tool]) == [temp, tool]


def test_a_skipped_row_stays_out_of_the_folder_around_it(tmp_path, aged):
    """``User Caches`` must not delete the Go cache its row just dropped."""
    caches = tmp_path / "Caches"
    go = caches / "go-build"
    go.mkdir(parents=True)
    (go / "blob").write_bytes(b"x" * 8192)
    backdate(caches)
    targets = [
        CleanTarget("User Caches", caches, "test"),
        CleanTarget("Go Cache", go, "test", attended=True),
    ]

    (target,) = daemon.unattended(cli._separate(targets))
    freed, _ = cli.clean_target(target, False)

    assert freed == 0
    assert (go / "blob").exists()


def test_irreplaceable_targets_are_marked_attended(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".Trash").mkdir()
    (tmp_path / "go" / "pkg" / "mod").mkdir(parents=True)

    assert {spec.name for spec in SYSTEM if spec.attended} == {
        "Trash",
        "Mail Downloads",
    }
    macos = {t.name: t for t in cli._get_macos_targets()}
    assert macos["Trash"].attended
    assert macos["Go Cache"].attended
    assert not macos["User Caches"].attended


def test_consent_roots_are_withheld_only_inside_the_block(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    template = ("{mac_containers}/app", "{mac_group_containers}/app", "{home}/x")

    with without_consent_roots():
        assert expand_paths(template) == [tmp_path / "x"]

    assert expand_paths(template) == [
        tmp_path / "Library/Containers/app",
        tmp_path / "Library/Group Containers/app",
        tmp_path / "x",
    ]


def test_consent_roots_come_back_after_an_error():
    with pytest.raises(RuntimeError):
        with without_consent_roots():
            raise RuntimeError

    assert "mac_containers" in resolve_roots()


def test_sandboxed_apps_are_found_only_with_consent(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    support = "Library/Containers/app/Data/Library/Application Support/Chat"
    (tmp_path / support / "Code Cache").mkdir(parents=True)

    assert [app.name for app in app_caches()] == ["Chat"]
    with without_consent_roots():
        assert app_caches() == []


def test_a_scheduled_run_stays_out_of_other_apps_sandboxes(monkeypatch):
    seen = {}

    def spy(*_):
        seen.update(resolve_roots())
        return []

    monkeypatch.setattr(daemon, "_get_targets", spy)

    assert daemon.scheduled_clean(args(daemon=None)) == 0

    assert "home" in seen
    assert not {"mac_containers", "mac_group_containers"} & set(seen)


def test_every_sandbox_path_goes_through_its_root():
    """A sandbox spelled out from ``{home}`` would hang scheduled runs again."""
    templates = [
        *APP_DIRS,
        *(path for cache in DEV_CACHES for path in cache.paths),
        *(path for review in REVIEW for path in review.paths),
        *(path for spec in SYSTEM for path in spec.paths),
    ]

    assert not [t for t in templates if "Containers" in t and t.startswith("{home}")]


def scheduled_setup(tmp_path, monkeypatch) -> Path:
    cache = cache_with(tmp_path)
    monkeypatch.setattr(
        daemon,
        "_get_targets",
        lambda force, privacy, projects: [CleanTarget("Cache", cache, "test")],
    )
    return cache


def test_a_scheduled_run_cleans_without_asking_and_logs(tmp_path, monkeypatch, aged):
    cache = scheduled_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "builtins.input", lambda *_: pytest.fail("a scheduled run must not ask")
    )

    assert daemon.scheduled_clean(args(daemon=None)) == 0

    assert not (cache / "idle" / "blob").exists()
    assert (cache / "hot" / "new").exists()
    assert (cache / "hot" / "old").exists()
    log = _config.clean_log_path().read_text()
    assert "freed 8.0KB" in log
    assert "Cache" in log


def test_a_scheduled_dry_run_deletes_and_logs_nothing(
    tmp_path, monkeypatch, aged, capsys
):
    cache = scheduled_setup(tmp_path, monkeypatch)

    assert daemon.scheduled_clean(args(daemon=None, dry_run=True)) == 0

    assert (cache / "idle" / "blob").exists()
    assert not _config.clean_log_path().exists()
    assert "frees up to 8.0KB" in capsys.readouterr().out


def test_a_crashed_run_says_so_in_the_log(monkeypatch):
    def crash(*_):
        raise RuntimeError("boom")

    monkeypatch.setattr(daemon, "_get_targets", crash)

    assert daemon.scheduled_clean(args(daemon=None)) == 1
    assert "failed: RuntimeError('boom')" in _config.clean_log_path().read_text()


def test_the_log_stays_bounded(monkeypatch):
    monkeypatch.setattr(daemon, "LOG_LINES", 3)

    daemon._log(["1", "2", "3"])
    daemon._log(["4", "5"])

    assert _config.clean_log_path().read_text().splitlines() == ["3", "4", "5"]


def test_warnings_are_capped_per_run(tmp_path, monkeypatch):
    target = CleanTarget("Cache", tmp_path, "test")
    monkeypatch.setattr(daemon, "_cleanable", lambda _: [{"target": target, "size": 1}])
    monkeypatch.setattr(
        daemon, "clean_target", lambda *_: (0, [f"Skipped {n}" for n in range(30)])
    )

    daemon.scheduled_clean(args(daemon=None))

    log = _config.clean_log_path().read_text()
    assert "30 skipped" in log
    assert "Skipped 19" in log
    assert "Skipped 20" not in log
    assert "and 10 more" in log


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["clean", "-d"], "start"),
        (["clean", "--daemon"], "start"),
        (["clean", "-d", "weekly"], "weekly"),
        (["clean", "--daemon", "monthly"], "monthly"),
        (["clean", "-d", "stop"], "stop"),
        (["clean", "-d", "status"], "status"),
        (["clean"], None),
    ],
)
def test_daemon_flag(argv, expected):
    assert build_parser().parse_args(argv).daemon == expected


def test_daemon_flag_rejects_other_schedules():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["clean", "-d", "fortnightly"])


class FakeScheduler(schedule.Scheduler):
    name = "fake"

    def __init__(self, is_installed=False, fails=False):
        self.job = None
        self.is_installed = is_installed
        self.fails = fails
        self.removed = False

    def usable(self):
        return True

    def location(self):
        return "/fake/job"

    def preview(self, job):
        return f"PREVIEW {job.every}"

    def install(self, job):
        if self.fails:
            raise SchedulerError("nope")
        self.job = job
        self.is_installed = True

    def remove(self):
        self.removed = True
        self.is_installed = False

    def installed(self):
        return self.is_installed

    def active(self):
        return self.is_installed


@pytest.fixture
def fake(monkeypatch):
    scheduler = FakeScheduler()
    monkeypatch.setattr(daemon, "schedulers", lambda: [scheduler])
    monkeypatch.setattr(daemon, "_is_elevated", lambda: False)
    monkeypatch.setattr(daemon.shutil, "which", lambda _: "/bin/sot")
    return scheduler


def test_hourly_is_the_default(fake):
    assert daemon.daemon_command(args()) == 0
    assert fake.job.every == "hourly"


def test_config_changes_the_default(fake):
    daemon.daemon_command(args(), "weekly")
    assert fake.job.every == "weekly"


def test_the_flag_beats_the_config(fake):
    daemon.daemon_command(args(daemon="monthly"), "weekly")
    assert fake.job.every == "monthly"


def test_config_reaches_the_daemon_through_run(fake):
    path = _config.config_path()
    path.parent.mkdir(parents=True)
    path.write_text('[clean]\nevery = "daily"\n')

    assert run(["clean", "-d"]) == 0
    assert fake.job.every == "daily"


def test_scheduled_flag_reaches_a_run(monkeypatch):
    calls = []
    monkeypatch.setattr(daemon, "_clean", calls.append)

    assert run(["clean", "--scheduled"]) == 0
    assert len(calls) == 1


def test_bad_config_schedule_is_reported():
    path = _config.config_path()
    path.parent.mkdir(parents=True)
    path.write_text('[clean]\nevery = "sometimes"\n')

    config = _config.load_config()

    assert config.clean_every is None
    assert "clean.every" in config.warnings[0]


def test_the_job_calls_a_scheduled_run_with_the_flags_given(fake, monkeypatch):
    monkeypatch.setenv("CARGO_HOME", "/elsewhere/cargo")
    monkeypatch.setenv("UNRELATED", "secret")

    daemon.daemon_command(args(force=True, privacy=True))

    assert fake.job.command == [
        "/bin/sot",
        "clean",
        "--scheduled",
        "--force",
        "--privacy",
    ]
    assert fake.job.env["CARGO_HOME"] == "/elsewhere/cargo"
    assert "PATH" in fake.job.env
    assert "UNRELATED" not in fake.job.env


def test_a_relative_projects_folder_is_pinned_down(fake, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    daemon.daemon_command(args(projects="."))

    assert fake.job.command[-2:] == ["--projects", str(tmp_path.resolve())]


def test_a_dry_run_installs_nothing_and_shows_the_job(fake, capsys):
    assert daemon.daemon_command(args(dry_run=True)) == 0

    assert fake.job is None
    assert "PREVIEW hourly" in capsys.readouterr().out
    assert _config.remembered_clean_schedule() is None


def test_a_dry_run_stop_removes_nothing(fake):
    fake.is_installed = True

    assert daemon.daemon_command(args(daemon="stop", dry_run=True)) == 0

    assert not fake.removed


def test_stop_removes_the_job(fake, capsys):
    fake.is_installed = True

    assert daemon.daemon_command(args(daemon="stop")) == 0

    assert fake.removed
    assert "off" in capsys.readouterr().out


def test_stop_with_nothing_scheduled_is_fine(fake, capsys):
    assert daemon.daemon_command(args(daemon="stop")) == 0
    assert "Nothing is scheduled" in capsys.readouterr().out


def test_status_reports_the_schedule_and_last_run(fake, capsys):
    daemon.daemon_command(args(daemon="weekly"))
    daemon._log(["2026-11-05 10:00:00 freed 1.0MB", "      1.0MB  Cache"])
    capsys.readouterr()

    assert daemon.daemon_command(args(daemon="status")) == 0

    out = capsys.readouterr().out
    assert "weekly" in out
    assert "2026-11-05 10:00:00 freed 1.0MB" in out
    assert "/fake/job" in out


def test_status_says_when_the_scheduler_wont_run_it(fake, capsys, monkeypatch):
    fake.is_installed = True
    monkeypatch.setattr(fake, "active", lambda: False)

    daemon.daemon_command(args(daemon="status"))

    assert "won't run it" in capsys.readouterr().out


def test_status_with_nothing_scheduled(fake, capsys):
    assert daemon.daemon_command(args(daemon="status")) == 0
    assert "Nothing is scheduled" in capsys.readouterr().out


def test_a_refused_job_is_an_error_and_isnt_remembered(fake, capsys):
    fake.fails = True

    assert daemon.daemon_command(args()) == 1

    assert "didn't take the job: nope" in capsys.readouterr().out
    assert _config.remembered_clean_schedule() is None


def test_it_refuses_sudo(fake, monkeypatch, capsys):
    monkeypatch.setattr(daemon, "_is_elevated", lambda: True)

    assert daemon.daemon_command(args()) == 1

    assert fake.job is None
    assert "without sudo" in capsys.readouterr().out


@pytest.mark.parametrize("manager", ["uvx", "pipx run"])
def test_it_refuses_a_cached_copy(fake, monkeypatch, manager):
    monkeypatch.setattr(daemon, "detect_install", lambda: Namespace(manager=manager))

    assert daemon.daemon_command(args()) == 1
    assert fake.job is None


def test_no_scheduler_is_an_error(monkeypatch, capsys):
    monkeypatch.setattr(daemon, "schedulers", lambda: [])
    monkeypatch.setattr(daemon, "_is_elevated", lambda: False)

    assert daemon.daemon_command(args()) == 1
    assert "needs launchd, systemd or cron" in capsys.readouterr().out


def test_moving_to_a_better_scheduler_removes_the_old_job(fake, monkeypatch):
    old = FakeScheduler(is_installed=True)
    monkeypatch.setattr(daemon, "schedulers", lambda: [fake, old])

    daemon.daemon_command(args())

    assert old.removed
    assert fake.job is not None


@pytest.fixture
def commands(monkeypatch):
    """Record what would be run, succeeding unless told otherwise."""
    ran = []
    failing = []

    def fake_run(*cmds, timeout=900, env=None):
        ran.extend(cmds)
        return [f"{c[1]} failed" for c in cmds if c[1] in failing]

    monkeypatch.setattr(schedule, "run", fake_run)
    monkeypatch.setattr(schedule.os, "getuid", lambda: 501, raising=False)
    ran_and_failing = Namespace(ran=ran, failing=failing)
    return ran_and_failing


@pytest.mark.parametrize("every", list(SCHEDULES))
def test_launchd_plist(every, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    plist = plistlib.loads(Launchd().preview(JOB._replace(every=every)).encode())

    assert plist["Label"] == schedule.LABEL
    assert plist["ProgramArguments"] == JOB.command
    assert plist["EnvironmentVariables"] == JOB.env
    assert plist["StartCalendarInterval"] == SCHEDULES[every][1]


def test_launchd_replaces_the_job(monkeypatch, tmp_path, commands):
    monkeypatch.setenv("HOME", str(tmp_path))
    launchd = Launchd()

    launchd.install(JOB)

    assert launchd.path.exists()
    assert commands.ran == [
        ("launchctl", "bootout", f"gui/501/{schedule.LABEL}"),
        ("launchctl", "bootstrap", "gui/501", str(launchd.path)),
    ]


def test_launchd_leaves_no_file_when_refused(monkeypatch, tmp_path, commands):
    monkeypatch.setenv("HOME", str(tmp_path))
    commands.failing.append("bootstrap")
    launchd = Launchd()

    with pytest.raises(SchedulerError):
        launchd.install(JOB)

    assert not launchd.installed()


def test_launchd_remove(monkeypatch, tmp_path, commands):
    monkeypatch.setenv("HOME", str(tmp_path))
    launchd = Launchd()
    launchd.install(JOB)

    launchd.remove()

    assert not launchd.installed()
    assert commands.ran[-1] == ("launchctl", "bootout", f"gui/501/{schedule.LABEL}")


def test_systemd_units():
    text = Systemd().preview(JOB._replace(every="weekly"))

    assert "OnCalendar=weekly" in text
    assert "Persistent=true" in text
    assert 'ExecStart="/bin/sot" "clean" "--scheduled"' in text
    assert 'Environment="PATH=/bin"' in text


def test_systemd_escapes_what_it_would_expand():
    job = Job("daily", ["/a b/100%/$x"], {"X": 'say "hi" 5%'})

    text = Systemd().preview(job)

    assert 'ExecStart="/a b/100%%/$$x"' in text
    assert 'Environment="X=say \\"hi\\" 5%%"' in text


def test_systemd_restarts_a_running_timer(commands):
    systemd = Systemd()

    systemd.install(JOB)

    assert systemd.installed()
    assert commands.ran == [
        ("systemctl", "--user", "daemon-reload"),
        ("systemctl", "--user", "enable", "sot-clean.timer"),
        ("systemctl", "--user", "restart", "sot-clean.timer"),
    ]
    systemd.remove()
    assert not systemd.installed()
    assert not systemd.service.exists()


class FakeCrontab:
    """Stands in for ``crontab -l`` and ``crontab -``."""

    def __init__(self, text=None, read_error=None):
        self.text = text
        self.read_error = read_error

    def __call__(self, command, input=None, **_):
        assert command[0] == "crontab"
        if command[1] == "-":
            self.text = input
            return subprocess.CompletedProcess(command, 0, "", "")
        if self.read_error:
            return subprocess.CompletedProcess(command, 1, "", self.read_error)
        if self.text is None:
            return subprocess.CompletedProcess(command, 1, "", "no crontab for ani")
        return subprocess.CompletedProcess(command, 0, self.text, "")


def crontab(monkeypatch, **kwargs) -> FakeCrontab:
    fake_crontab = FakeCrontab(**kwargs)
    monkeypatch.setattr(schedule.subprocess, "run", fake_crontab)
    return fake_crontab


def test_cron_keeps_what_else_is_in_the_crontab(monkeypatch):
    table = crontab(monkeypatch, text="MAILTO=me\n5 4 * * * backup\n")
    cron = Cron()

    cron.install(JOB)

    lines = table.text.splitlines()
    assert lines[:2] == ["MAILTO=me", "5 4 * * * backup"]
    assert lines[2].startswith("0 0 * * * nice -n 19 env PATH=/bin /bin/sot clean")
    assert cron.installed()


def test_cron_replaces_its_own_line(monkeypatch):
    table = crontab(monkeypatch, text="5 4 * * * backup\n")
    cron = Cron()

    cron.install(JOB)
    cron.install(JOB._replace(every="monthly"))

    lines = table.text.splitlines()
    assert len(lines) == 2
    assert lines[1].startswith("0 0 1 * * ")


def test_cron_starts_a_crontab_when_there_is_none(monkeypatch):
    table = crontab(monkeypatch)

    Cron().install(JOB)

    assert len(table.text.splitlines()) == 1


def test_cron_remove_leaves_the_rest(monkeypatch):
    table = crontab(monkeypatch, text="5 4 * * * backup\n")
    cron = Cron()
    cron.install(JOB)

    cron.remove()

    assert table.text == "5 4 * * * backup\n"
    assert not cron.installed()


def test_cron_wont_overwrite_a_crontab_it_cant_read(monkeypatch):
    table = crontab(monkeypatch, read_error="permission denied")

    with pytest.raises(SchedulerError):
        Cron().install(JOB)

    assert table.text is None


def test_cron_escapes_percent_signs():
    line = Cron().preview(Job("daily", ["/a%b/sot"], {}))

    assert "/a\\%b/sot" in line


def test_a_crontab_that_wont_run_is_a_scheduler_error(monkeypatch):
    def hang(*_, **__):
        raise subprocess.TimeoutExpired("crontab", 30)

    monkeypatch.setattr(schedule.subprocess, "run", hang)

    with pytest.raises(SchedulerError):
        Cron().installed()


def test_only_usable_schedulers_are_offered(monkeypatch):
    monkeypatch.setattr(schedule.platform, "system", lambda: "Windows")
    monkeypatch.setattr(schedule, "capture", lambda *_: None)
    monkeypatch.setattr(schedule.shutil, "which", lambda _: None)

    assert schedule.schedulers() == []


def test_macos_uses_launchd_alone(monkeypatch):
    monkeypatch.setattr(schedule.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(schedule, "capture", lambda *_: None)

    assert [s.name for s in schedule.schedulers()] == ["launchd"]


def test_linux_prefers_systemd_over_cron(monkeypatch):
    monkeypatch.setattr(schedule.platform, "system", lambda: "Linux")
    monkeypatch.setattr(schedule, "capture", lambda *_: "")
    monkeypatch.setattr(schedule.shutil, "which", lambda _: "/usr/bin/crontab")

    assert [s.name for s in schedule.schedulers()] == ["systemd", "cron"]


def test_linux_without_a_user_bus_falls_back_to_cron(monkeypatch):
    monkeypatch.setattr(schedule.platform, "system", lambda: "Linux")
    monkeypatch.setattr(schedule, "capture", lambda *_: None)
    monkeypatch.setattr(schedule.shutil, "which", lambda _: "/usr/bin/crontab")

    assert [s.name for s in schedule.schedulers()] == ["cron"]
