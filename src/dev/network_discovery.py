#!/usr/bin/env python3
"""
Network interface discovery utility for SOT.
"""

import socket

import psutil
from rich.console import Console
from rich.table import Table


def discover_network_interfaces():
    """Discover and display all available network interfaces."""
    console = Console()
    
    console.print("🔍 [bold blue]SOT Network Interface Discovery[/bold blue]")
    console.print()
    
    try:
        # Get interface statistics
        if_stats = psutil.net_if_stats()
        if_addrs = psutil.net_if_addrs()
        if_counters = psutil.net_io_counters(pernic=True)
        
        # Create table
        table = Table(title="📡 Available Network Interfaces")
        table.add_column("Interface", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("IPv4 Address", style="blue")
        table.add_column("IPv6 Address", style="purple")
        table.add_column("Bytes Sent", style="yellow", justify="right")
        table.add_column("Bytes Recv", style="aquamarine3", justify="right")
        table.add_column("Recommendation", style="dim")
        
        # Auto-selection scoring (same as in NetworkWidget)
        recommendations = {}
        for name, stats in if_stats.items():
            if not stats.isup:
                recommendations[name] = "❌ Down"
            elif (
                name.startswith("lo")
                or name.lower().startswith("loopback")
                or name.lower().startswith("docker")
                or name.lower().startswith("anpi")
            ):
                recommendations[name] = "🔄 Loopback/Virtual"
            elif name.lower().startswith("fw") or name.lower().startswith("bluetooth"):
                recommendations[name] = "📶 Wireless/FW"
            elif name.lower().startswith("en"):
                recommendations[name] = "⭐ Ethernet (Recommended)"
            else:
                recommendations[name] = "✅ Available"
        
        # Find the auto-selected interface
        auto_selected = None
        best_score = 0
        for name, stats in if_stats.items():
            if not stats.isup:
                score = 0
            elif (
                name.startswith("lo")
                or name.lower().startswith("loopback")
                or name.lower().startswith("docker")
                or name.lower().startswith("anpi")
            ):
                score = 1
            elif name.lower().startswith("fw") or name.lower().startswith("bluetooth"):
                score = 2
            elif name.lower().startswith("en"):
                score = 4
            else:
                score = 3
            
            if score > best_score:
                best_score = score
                auto_selected = name
        
        # Populate table
        for interface_name in sorted(if_stats.keys()):
            stats = if_stats[interface_name]
            status = "🟢 UP" if stats.isup else "🔴 DOWN"
            
            # Get IPv4 address
            ipv4_addr = "None"
            ipv6_addr = "None"
            if interface_name in if_addrs:
                for addr in if_addrs[interface_name]:
                    if addr.family == socket.AF_INET:
                        ipv4_addr = addr.address
                    elif addr.family == socket.AF_INET6 and not addr.address.startswith("fe80"):
                        ipv6_addr = addr.address[:30] + "..." if len(addr.address) > 30 else addr.address
            
            # Get traffic stats
            bytes_sent = "0"
            bytes_recv = "0"
            if interface_name in if_counters:
                counters = if_counters[interface_name]
                bytes_sent = f"{counters.bytes_sent:,}"
                bytes_recv = f"{counters.bytes_recv:,}"
            
            # Add special marking for auto-selected interface
            recommendation = recommendations.get(interface_name, "❓ Unknown")
            if interface_name == auto_selected:
                recommendation += " [bold](AUTO-SELECTED)[/bold]"
            
            table.add_row(
                interface_name,
                status,
                ipv4_addr,
                ipv6_addr,
                bytes_sent,
                bytes_recv,
                recommendation
            )
        
        console.print(table)
        console.print()
        
        # Show usage examples
        console.print("💡 [bold yellow]Usage Examples:[/bold yellow]")
        console.print(f"   sot                    # Use auto-selected: {auto_selected}")
        console.print(f"   sot --net {auto_selected}        # Explicitly specify auto-selected")
        
        # Show first few available interfaces as examples
        available_interfaces = [name for name, stats in if_stats.items() if stats.isup]
        for interface in available_interfaces[:3]:
            if interface != auto_selected:
                console.print(f"   sot --net {interface}        # Use {interface}")
        
        console.print()
        console.print("🔧 [bold]Current Network Interface Check:[/bold]")
        console.print(f"   Auto-selected interface: [green]{auto_selected}[/green]")
        console.print(f"   Status: {status}")
        console.print(f"   IPv4: {ipv4_addr}")
        
    except Exception as e:
        console.print(f"❌ [red]Error discovering interfaces: {e}[/red]")
        return False
    
    return True


def main():
    success = discover_network_interfaces()
    if not success:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
