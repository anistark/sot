"""Volume discovery shared by the disk TUI and the plain-text listing."""

from __future__ import annotations

import platform
import re
from typing import Any, Dict, List, NamedTuple, Optional

import psutil


class UsageInfo(NamedTuple):
    """Aggregate usage for a physical disk, mirroring ``psutil``'s usage tuple."""

    total: int
    used: int
    free: int
    percent: float


def usage_style(percent: float) -> str:
    """Rich style name for a usage percentage: green -> yellow -> red."""
    if percent > 95:
        return "red"
    if percent > 80:
        return "yellow"
    return "green"


def extract_disk_id(device: str) -> str:
    """Extract disk identifier from device path."""
    # macOS: /dev/disk3s1 -> disk3
    # Linux: /dev/sda1 -> sda
    match = re.search(r"disk\d+", device)
    if match:
        return match.group(0)
    # Linux: extract base device name (sda from sda1)
    match = re.search(r"([sh]d[a-z]+)", device)
    if match:
        return match.group(1)
    return device


def extract_partition_id(device: str) -> str:
    """Extract full partition identifier from device path."""
    # macOS: /dev/disk3s1 -> disk3s1 or /dev/disk3s1s1 -> disk3s1s1
    # Linux: /dev/sda1 -> sda1
    match = re.search(r"(disk\d+s\d+(?:s\d+)?|[a-z]+\d+)", device)
    if match:
        return match.group(1)
    return device.split("/")[-1]  # Fallback to just the device name


def disk_name_for_io(device: str) -> Optional[str]:
    """Get disk name for I/O statistics lookup."""
    system = platform.system()

    if system == "Darwin":
        # macOS: /dev/disk3s1 -> disk3
        match = re.search(r"disk\d+", device)
        return match.group(0) if match else None
    elif system == "Linux":
        # Linux: /dev/sda1 -> sda
        match = re.search(r"([a-z]+)\d*$", device)
        return match.group(1) if match else None

    return None


def get_volume_info() -> List[Dict]:
    """Get information about all volumes, grouping by physical disk."""
    # First, collect all partitions by physical disk
    disks_dict: Dict[str, Dict[str, Any]] = {}
    partitions_list = [
        p for p in psutil.disk_partitions() if not p.device.startswith("/dev/loop")
    ]

    for partition in partitions_list:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_id = extract_disk_id(partition.device)

            partition_info = {
                "partition_id": extract_partition_id(partition.device),
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "opts": partition.opts,
                "usage": usage,
            }

            if disk_id not in disks_dict:
                disks_dict[disk_id] = {
                    "disk_id": disk_id,
                    "partitions": [],
                    "total_size": 0,
                    "total_used": 0,
                    "total_free": 0,
                }

            disks_dict[disk_id]["partitions"].append(partition_info)
            # For APFS containers, volumes share total/free but have individual used space
            # Track the largest total (all volumes report same total in APFS)
            if usage.total > disks_dict[disk_id]["total_size"]:
                disks_dict[disk_id]["total_size"] = usage.total
            # Sum all volumes' used space (each volume has unique data)
            disks_dict[disk_id]["total_used"] += usage.used
            # Track free space (shared across all volumes in APFS, so just keep the latest)
            disks_dict[disk_id]["total_free"] = usage.free

        except (PermissionError, FileNotFoundError):
            continue

    # Now create volumes from disks
    volumes = []
    for disk_id, disk_data in disks_dict.items():
        # Find the primary partition (usually root or first partition)
        primary_partition = None
        for part in disk_data["partitions"]:
            if part["mountpoint"] == "/":
                primary_partition = part
                break
        if not primary_partition and disk_data["partitions"]:
            primary_partition = disk_data["partitions"][0]

        if not primary_partition:
            continue

        # Determine volume name from primary partition
        if primary_partition["mountpoint"] == "/":
            volume_name = "System"
        else:
            volume_name = primary_partition["mountpoint"].split("/")[-1] or disk_id

        # Calculate aggregate usage percentage
        total_size = disk_data["total_size"]
        total_used = disk_data["total_used"]
        usage_percent = (total_used / total_size * 100) if total_size > 0 else 0

        volume = {
            "volume_name": volume_name,
            "disk_id": disk_id,
            "partitions": disk_data["partitions"],
            "usage": UsageInfo(
                total_size, total_used, disk_data["total_free"], usage_percent
            ),
        }

        # Get I/O statistics for this disk
        try:
            io_counters = psutil.disk_io_counters(perdisk=True)
            disk_name = disk_name_for_io(primary_partition["device"])
            if disk_name and disk_name in io_counters:
                io_stat = io_counters[disk_name]
                volume["io_stats"] = {
                    "read_count": io_stat.read_count,
                    "write_count": io_stat.write_count,
                    "read_bytes": io_stat.read_bytes,
                    "write_bytes": io_stat.write_bytes,
                    "read_time": io_stat.read_time,
                    "write_time": io_stat.write_time,
                }
        except Exception:
            pass

        volumes.append(volume)

    return volumes
