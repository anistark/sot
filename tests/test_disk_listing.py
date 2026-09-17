from rich.console import Console

from sot.disk import listing
from sot.disk.volumes import UsageInfo, usage_style

GIB = 1024**3


def _volume(disk_id: str, mounts: list[tuple[str, int]], total: int) -> dict:
    """A volume dict in the shape ``get_volume_info`` returns."""
    partitions = [
        {
            "partition_id": f"{disk_id}s{i + 1}",
            "device": f"/dev/{disk_id}s{i + 1}",
            "mountpoint": mount,
            "fstype": "apfs",
            "opts": "rw",
            "usage": UsageInfo(total, used, total - used, used / total * 100),
        }
        for i, (mount, used) in enumerate(mounts)
    ]
    used = sum(u for _, u in mounts)
    return {
        "volume_name": disk_id,
        "disk_id": disk_id,
        "partitions": partitions,
        "usage": UsageInfo(total, used, total - used, used / total * 100),
    }


def _render(table, width: int) -> str:
    console = Console(width=width, record=True, file=open("/dev/null", "w"))
    console.print(table)
    return console.export_text()


def test_usage_style_thresholds():
    assert usage_style(50) == "green"
    assert usage_style(81) == "yellow"
    assert usage_style(96) == "red"


def test_table_lists_every_disk_and_partition():
    volumes = [
        _volume(
            "disk3", [("/", 20 * GIB), ("/System/Volumes/Data", 100 * GIB)], 228 * GIB
        ),
        _volume("disk5", [("/Volumes/April", 250 * GIB)], 931 * GIB),
    ]
    out = _render(listing.build_disk_table(volumes, width=130), 130)

    for needle in (
        "disk3",
        "disk3s1",
        "disk3s2",
        "disk5s1",
        "/System/Volumes/Data",
        "apfs",
    ):
        assert needle in out
    # Tree connectors: last partition of each disk closes the branch.
    assert out.count("└─") == 2
    assert out.count("├─") == 1


def test_compact_layout_keeps_mountpoints_readable():
    volumes = [_volume("disk3", [("/System/Volumes/Data", 100 * GIB)], 228 * GIB)]
    out = _render(listing.build_disk_table(volumes, width=80), 80)

    # Narrow terminals drop the FS column and fold the mountpoint onto
    # extra lines rather than truncating it.
    assert "apfs" not in out
    assert "…" not in out
    mount_col = out.index("Mount")
    folded = "".join(line[mount_col:].split()[0] for line in out.splitlines()[1:])
    assert "/System/Volumes/Data" in folded


def test_print_disk_list_reports_no_disks(monkeypatch):
    monkeypatch.setattr(listing, "get_volume_info", lambda: [])
    assert listing.print_disk_list(Console(quiet=True)) == 1


def test_print_disk_list_prints_summary(monkeypatch):
    volumes = [_volume("disk5", [("/Volumes/April", 250 * GIB)], 500 * GIB)]
    monkeypatch.setattr(listing, "get_volume_info", lambda: volumes)

    console = Console(width=130, record=True, file=open("/dev/null", "w"))
    assert listing.print_disk_list(console) == 0
    out = console.export_text()
    assert "1 disk(s)" in out
    assert "Total 500.0 GiB" in out
    assert "50.0%" in out
