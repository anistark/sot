from types import SimpleNamespace

from sot import _collectors


def _proc(pid, name, read=0, cmdline=None, ports=None, cpu=1.0, rss=1024 * 1024):
    return {
        "pid": pid,
        "name": name,
        "cmdline": cmdline or [name],
        "cpu_percent": cpu,
        "memory_info": SimpleNamespace(rss=rss),
        "listen_ports": ports or [],
        "io_read_bytes": read,
        "io_write_bytes": 0,
    }


def test_dev_environments_group_by_ecosystem():
    envs = _collectors.dev_environments(
        [
            _proc(1, "node", ports=[3000]),
            _proc(2, "vite", cmdline=["node", "vite"], ports=[5173]),
            _proc(3, "python3", cmdline=["python3", "-m", "uvicorn"]),
            _proc(4, "launchd"),
        ]
    )
    by_type = {env["type"]: env for env in envs}
    assert set(by_type) == {"node", "python"}
    assert by_type["node"]["count"] == 2
    assert by_type["node"]["ports"] == [3000, 5173]
    assert by_type["node"]["memory_mb"] == 2.0


def test_sampler_reuses_recent_samples_and_computes_io_rates(monkeypatch):
    clock = iter([100.0, 100.5, 102.0])
    samples = iter([[_proc(7, "a", read=1000)], [_proc(7, "a", read=5000)]])
    monkeypatch.setattr(_collectors.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(_collectors, "get_process_list", lambda: next(samples))

    sampler = _collectors.ProcessSampler(max_age=1.0)
    first = sampler.sample()
    assert first[0]["io_read_rate"] == 0
    assert sampler.sample() is first

    second = sampler.sample()
    assert second[0]["io_read_rate"] == 2000.0


def _conn(status, pid=None, raddr=None):
    return SimpleNamespace(status=status, pid=pid, raddr=raddr)


def test_inet_connections_falls_back_to_own_processes(monkeypatch):
    def denied(kind="inet"):
        raise _collectors.psutil.AccessDenied()

    class Proc:
        def __init__(self, name, conns):
            self.info = {"name": name}
            self._conns = conns

        def net_connections(self, kind="inet"):
            if self._conns is None:
                raise _collectors.psutil.AccessDenied()
            return self._conns

    procs = [
        Proc("node", [_conn("ESTABLISHED", raddr=SimpleNamespace(ip="1.2.3.4"))]),
        Proc("launchd", None),
        Proc("mDNSResponder", [_conn("")]),
    ]
    monkeypatch.setattr(_collectors.psutil, "net_connections", denied)
    monkeypatch.setattr(_collectors.psutil, "process_iter", lambda attrs: procs)

    conns, complete = _collectors.inet_connections()
    assert not complete
    assert conns == [
        {"status": "ESTABLISHED", "name": "node", "remote": "1.2.3.4"},
        {"status": "NONE", "name": "mDNSResponder", "remote": None},
    ]


def test_inet_connections_names_system_wide_sockets(monkeypatch):
    monkeypatch.setattr(
        _collectors.psutil,
        "net_connections",
        lambda kind="inet": [_conn("LISTEN", pid=7), _conn("LISTEN")],
    )
    monkeypatch.setattr(
        _collectors.psutil,
        "Process",
        lambda pid: SimpleNamespace(name=lambda: "sshd"),
    )
    conns, complete = _collectors.inet_connections()
    assert complete
    assert [c["name"] for c in conns] == ["sshd", "system"]
