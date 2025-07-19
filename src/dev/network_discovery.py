#!/usr/bin/env python3
"""
Network Discovery Tool

Discovers and lists available network interfaces with their properties.
"""

import socket
from typing import List, Optional

import psutil


class NetworkInterfaceInfo:
    """Data class for network interface information."""

    def __init__(self, name: str):
        self.name = name
        self.is_up = False
        self.has_ipv4 = False
        self.has_ipv6 = False
        self.ipv4_addresses = []
        self.ipv6_addresses = []
        self.bytes_sent = 0
        self.bytes_recv = 0
        self.score = 0
        self.interface_type = "unknown"


def get_interface_basic_info(name: str) -> Optional[NetworkInterfaceInfo]:
    """Get basic interface information (up/down status, type classification)."""
    try:
        stats = psutil.net_if_stats().get(name)
        if not stats:
            return None

        info = NetworkInterfaceInfo(name)
        info.is_up = stats.isup
        info.interface_type = classify_interface_type(name)
        return info
    except Exception:
        return None


def classify_interface_type(name: str) -> str:
    """Classify the interface type based on its name."""
    name_lower = name.lower()

    if name_lower.startswith(("lo", "loopback")):
        return "loopback"
    elif name_lower.startswith(("docker", "anpi", "veth")):
        return "virtual"
    elif name_lower.startswith(("fw", "bluetooth")):
        return "special"
    elif name_lower.startswith(("en", "eth")):
        return "ethernet"
    elif name_lower.startswith(("wl", "wifi", "wlan")):
        return "wireless"
    else:
        return "other"


def get_interface_addresses(name: str, info: NetworkInterfaceInfo) -> None:
    """Populate IP address information for the interface."""
    try:
        addrs = psutil.net_if_addrs().get(name, [])

        for addr in addrs:
            if addr.family == socket.AF_INET:
                info.has_ipv4 = True
                info.ipv4_addresses.append(f"{addr.address}/{addr.netmask}")
            elif addr.family == socket.AF_INET6:
                info.has_ipv6 = True
                info.ipv6_addresses.append(addr.address)
    except Exception:
        pass


def get_interface_stats(name: str, info: NetworkInterfaceInfo) -> None:
    """Get traffic statistics for the interface."""
    try:
        counters = psutil.net_io_counters(pernic=True).get(name)
        if counters:
            info.bytes_sent = counters.bytes_sent
            info.bytes_recv = counters.bytes_recv
    except Exception:
        pass


def calculate_interface_score(info: NetworkInterfaceInfo) -> int:
    """Calculate priority score for interface selection."""
    if not info.is_up:
        return 0

    type_scores = {
        "loopback": 1,
        "virtual": 1,
        "special": 2,
        "other": 3,
        "wireless": 4,
        "ethernet": 5,
    }

    base_score = type_scores.get(info.interface_type, 1)

    # Bonus points for having IP addresses
    if info.has_ipv4:
        base_score += 2
    if info.has_ipv6:
        base_score += 1

    # Bonus for traffic (indicates active usage)
    if info.bytes_sent > 0 or info.bytes_recv > 0:
        base_score += 1

    return base_score


def format_interface_display(info: NetworkInterfaceInfo) -> str:
    """Format interface information for display."""
    status = "UP" if info.is_up else "DOWN"
    type_display = info.interface_type.upper()

    addresses = []
    if info.ipv4_addresses:
        addresses.extend(info.ipv4_addresses[:2])
    if info.ipv6_addresses:
        addresses.append(info.ipv6_addresses[0][:30] + "...")

    addr_display = ", ".join(addresses) if addresses else "No IP"

    traffic = ""
    if info.bytes_sent > 0 or info.bytes_recv > 0:
        traffic = (
            f" (↑{_format_bytes(info.bytes_sent)} ↓{_format_bytes(info.bytes_recv)})"
        )

    return f"{info.name:<12} [{status:<4}] {type_display:<8} {addr_display}{traffic}"


def _format_bytes(bytes_val: int) -> str:
    """Format bytes in human readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f}TB"


def discover_network_interfaces() -> List[NetworkInterfaceInfo]:
    """
    Discover all network interfaces with their properties.

    Returns:
        List of NetworkInterfaceInfo objects sorted by priority score.
    """
    interfaces = []

    try:
        interface_names = list(psutil.net_if_stats().keys())
    except Exception:
        return interfaces

    for name in interface_names:
        info = get_interface_basic_info(name)
        if not info:
            continue

        get_interface_addresses(name, info)
        get_interface_stats(name, info)

        info.score = calculate_interface_score(info)

        interfaces.append(info)

    # Sort by score (highest first), then by name
    interfaces.sort(key=lambda x: (-x.score, x.name))

    return interfaces


def print_interface_summary(interfaces: List[NetworkInterfaceInfo]) -> None:
    """Print a summary of discovered interfaces."""
    if not interfaces:
        print("❌ No network interfaces found")
        return

    print(f"📡 Found {len(interfaces)} network interfaces:")
    print("-" * 80)

    for info in interfaces:
        score_indicator = "⭐" * min(info.score, 5)
        print(f"{score_indicator:<6} {format_interface_display(info)}")

    best_interface = next((i for i in interfaces if i.is_up and i.score > 1), None)
    if best_interface:
        print(
            f"\n🎯 Recommended: {best_interface.name} (score: {best_interface.score})"
        )


def get_best_interface() -> Optional[str]:
    """Get the name of the best available interface."""
    interfaces = discover_network_interfaces()
    best = next((i for i in interfaces if i.is_up and i.score > 1), None)
    return best.name if best else None


def main():
    """Main entry point for the network discovery tool."""
    print("🔍 Discovering network interfaces...\n")

    interfaces = discover_network_interfaces()
    print_interface_summary(interfaces)

    print("\n📊 Interface type breakdown:")
    type_counts = {}
    for info in interfaces:
        type_counts[info.interface_type] = type_counts.get(info.interface_type, 0) + 1

    for iface_type, count in sorted(type_counts.items()):
        print(f"  {iface_type}: {count}")


if __name__ == "__main__":
    main()
