"""Command-line interface for disk benchmarking."""

import json
import tempfile
from pathlib import Path
from typing import Dict, List

import psutil
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .._helpers import iops_fmt, latency_fmt, sizeof_fmt, throughput_fmt
from .._theme import theme
from .core import BenchmarkResult, DiskBenchmark

console = Console()


def get_physical_disks() -> List[Dict]:
    """
    Get physical disks grouped by disk identifier.

    Returns:
            List of dicts with keys:
            - disk_id: Physical disk identifier (e.g., /dev/disk3)
            - partitions: List of partition info dicts
            - largest_partition: The partition with most free space
            - total_bytes: Total disk capacity
            - free_bytes: Available space on largest partition
    """
    import re

    # Get all partitions
    partitions = [
        p for p in psutil.disk_partitions() if not p.device.startswith("/dev/loop")
    ]

    # Group partitions by disk identifier
    disks_dict: Dict[str, List] = {}

    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            partition_info = {
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "total_bytes": usage.total,
                "free_bytes": usage.free,
                "used_bytes": usage.used,
            }

            # Extract disk identifier (base device)
            # macOS: /dev/disk3s1 -> /dev/disk3, Linux: /dev/sda1 -> /dev/sda
            match = re.match(r"^(.*?[a-z])(\d+)[s\d]*$", partition.device)
            if match:
                disk_id = match.group(1) + match.group(2)
            else:
                disk_id = partition.device
            if disk_id not in disks_dict:
                disks_dict[disk_id] = []
            disks_dict[disk_id].append(partition_info)

        except (PermissionError, FileNotFoundError):
            continue

    # Convert to list of physical disks
    physical_disks = []
    for disk_id, partitions_list in sorted(disks_dict.items()):
        # Find largest partition by free space
        largest_partition = max(partitions_list, key=lambda p: p["free_bytes"])

        disk_info = {
            "disk_id": disk_id,
            "partitions": partitions_list,
            "largest_partition": largest_partition,
            "total_bytes": largest_partition["total_bytes"],
            "free_bytes": largest_partition["free_bytes"],
        }
        physical_disks.append(disk_info)

    return physical_disks


def display_disk_selection(physical_disks: List[Dict]) -> int:
    """
    Display available physical disks and let user select interactively.

    Args:
            physical_disks: List of physical disk information dicts

    Returns:
            Index of selected disk, or -1 if cancelled
    """
    c = theme().colors
    if not physical_disks:
        console.print(f"[{c.danger}]No accessible disks found[/]")
        return -1

    from .._helpers import sizeof_fmt

    # Display disk table
    table = Table(
        title="Available Disks",
        show_header=True,
        header_style=f"bold {c.accent}",
        box=theme().design.app_box,
    )
    table.add_column("#", style=c.primary)
    table.add_column("Disk", style=c.accent)
    table.add_column("Volume", style=c.accent)
    table.add_column("Total", style=c.info)
    table.add_column("Free", style=c.ok)
    table.add_column("Partitions", style=c.muted)

    for i, disk in enumerate(physical_disks):
        total_str = sizeof_fmt(disk["total_bytes"], fmt=".1f")
        free_str = sizeof_fmt(disk["free_bytes"], fmt=".1f")
        partition_count = len(disk["partitions"])

        # Extract volume name from mountpoint
        largest_partition = disk["largest_partition"]
        mountpoint = largest_partition["mountpoint"]
        volume_name = Path(mountpoint).name or mountpoint
        if not volume_name or volume_name == "/":
            volume_name = "System"

        table.add_row(
            str(i),
            disk["disk_id"],
            volume_name,
            total_str,
            free_str,
            str(partition_count),
        )

    console.print(table)

    # Interactive selection (inline, no screen clearing)
    selected_index = _select_with_arrows(physical_disks)

    if selected_index >= 0:
        selected_disk = physical_disks[selected_index]
        largest_partition = selected_disk["largest_partition"]
        # Extract volume name
        mountpoint = largest_partition["mountpoint"]
        volume_name = Path(mountpoint).name or mountpoint
        if not volume_name or volume_name == "/":
            volume_name = "System"
        console.print(
            f"\n[{c.ok}]✓ Selected: {volume_name}[/]\n"
            f"  Using partition: {largest_partition['device']} ({largest_partition['mountpoint']})\n"
        )

    return selected_index


def _select_with_arrows(physical_disks: List[Dict]) -> int:
    """Select disk using arrow keys or number input."""
    try:
        import sys
        import termios
        import tty

        # Check if stdin is a TTY for raw input
        if not sys.stdin.isatty():
            # Non-interactive mode - use number input
            return _select_with_numbers(physical_disks)

        current_index = 0
        old_settings = None

        try:
            # Get terminal settings
            old_settings = termios.tcgetattr(sys.stdin)

            # Set raw mode for input capture
            tty.setraw(sys.stdin.fileno())

            # Display options inline as we navigate
            def show_menu():
                # Clear screen and move cursor to home
                sys.stdout.write("\033[2J\033[H")
                sys.stdout.write(
                    "\033[1;33mUse arrow keys (↑↓) to navigate, Enter to select, or 'q' to quit:\033[0m\r\n\r\n"
                )
                sys.stdout.flush()
                for i, disk in enumerate(physical_disks):
                    total_str = sizeof_fmt(disk["total_bytes"], fmt=".1f")
                    free_str = sizeof_fmt(disk["free_bytes"], fmt=".1f")

                    # Extract volume name from mountpoint
                    largest_partition = disk["largest_partition"]
                    mountpoint = largest_partition["mountpoint"]
                    volume_name = Path(mountpoint).name or mountpoint
                    if not volume_name or volume_name == "/":
                        volume_name = "System"

                    disk_info = (
                        f"{volume_name} - " f"{total_str} total, " f"{free_str} free"
                    )

                    if i == current_index:
                        sys.stdout.write(f"  \033[1;36m❯ {i}: {disk_info}\033[0m\r\n")
                    else:
                        sys.stdout.write(f"    {i}: {disk_info}\r\n")
                sys.stdout.flush()

            show_menu()
            while True:
                # Read single character
                ch = sys.stdin.read(1)

                if ch == "q" or ch == "Q":
                    return -1
                elif ch == "\n" or ch == "\r":
                    return current_index
                elif ch == "\x1b":  # Escape sequence for arrow keys
                    next1 = sys.stdin.read(1)
                    if next1 == "[":
                        next2 = sys.stdin.read(1)
                        if next2 == "A":  # Up arrow
                            current_index = (current_index - 1) % len(physical_disks)
                            show_menu()
                        elif next2 == "B":  # Down arrow
                            current_index = (current_index + 1) % len(physical_disks)
                            show_menu()
                elif ch.isdigit():  # Number input
                    index = int(ch)
                    if 0 <= index < len(physical_disks):
                        return index

        finally:
            # Restore terminal settings
            if old_settings:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                sys.stdout.flush()

    except Exception:
        # Fallback to number selection if anything fails
        return _select_with_numbers(physical_disks)


def _select_with_numbers(physical_disks: List[Dict]) -> int:
    """Select disk using number input (fallback)."""
    c = theme().colors
    while True:
        try:
            selection = console.input(
                f"\n[bold {c.warn}]Select disk by number "
                f"(0-{len(physical_disks) - 1}), or 'q' to quit: [/]"
            )

            if selection.lower() == "q":
                return -1

            index = int(selection)
            if 0 <= index < len(physical_disks):
                return index

            console.print(f"[{c.danger}]Invalid selection. Please try again.[/]")

        except ValueError:
            console.print(
                f"[{c.danger}]Invalid input. Please enter a number or 'q'.[/]"
            )


def display_results(results: List[BenchmarkResult], disk_info: Dict):
    """
    Display benchmark results in a formatted table.

    Args:
            results: List of BenchmarkResult objects
            disk_info: Dict with disk information
    """
    from .core import get_bench_cache_dir

    t = theme()
    c = t.colors

    # Extract volume name from mountpoint
    largest_partition = disk_info["largest_partition"]
    mountpoint = largest_partition["mountpoint"]
    volume_name = Path(mountpoint).name or mountpoint
    if not volume_name or volume_name == "/":
        volume_name = "System"

    # Build disk info panel
    partitions_text = "\n".join(
        f"  • {p['device']} → {p['mountpoint']}" for p in disk_info["partitions"]
    )
    cache_dir = get_bench_cache_dir()

    info_text = (
        f"Disk ID: {disk_info['disk_id']} ({volume_name})\n"
        f"Total Capacity: {sizeof_fmt(disk_info['total_bytes'], fmt='.1f')}\n"
        f"Free Space: {sizeof_fmt(disk_info['free_bytes'], fmt='.1f')}\n"
        f"Cache Directory: {cache_dir}\n\n"
        f"Partitions:\n{partitions_text}"
    )

    disk_panel = Panel(
        info_text,
        title=f"[bold]{volume_name}[/]",
        style=c.accent,
        box=t.design.app_box,
    )

    console.print(disk_panel)

    # Results table
    table = Table(
        title="Benchmark Results",
        show_header=True,
        header_style=f"bold {c.accent}",
        box=t.design.app_box,
    )
    table.add_column("Test", style=c.accent)
    table.add_column("Throughput/IOPS", style=c.primary)
    table.add_column("Avg Latency", style=c.info)
    table.add_column("p95 Latency", style=c.info)
    table.add_column("p99 Latency", style=c.info)
    table.add_column("Duration", style=c.ok)

    for result in results:
        if result.is_error():
            table.add_row(
                f"[{c.danger}]{result.test_name}[/]",
                f"[{c.danger}]Error[/]",
                "-",
                "-",
                "-",
                "-",
            )
            continue

        # Determine metric to display
        if result.throughput_mbps is not None:
            metric = throughput_fmt(result.throughput_mbps)
        elif result.iops is not None:
            metric = iops_fmt(result.iops)
        else:
            metric = "-"

        table.add_row(
            f"[{c.ok}]{result.test_name}[/]",
            metric,
            latency_fmt(result.avg_latency_ms),
            latency_fmt(result.p95_latency_ms),
            latency_fmt(result.p99_latency_ms),
            latency_fmt(result.duration_ms),
        )

    console.print(table)

    # Summary
    error_count = sum(1 for r in results if r.is_error())
    success_count = len(results) - error_count

    if error_count == 0:
        summary_text = f"[{c.ok}]✓ Benchmarking completed successfully[/]"
    elif success_count == 0:
        summary_text = f"[{c.danger}]✗ Benchmarking failed - no tests completed[/]"
    else:
        summary_text = f"[{c.warn}]⚠ Benchmarking partially completed ({success_count}/{len(results)} tests)[/]"

    console.print(f"\n{summary_text}\n")


def export_results_json(
    results: List[BenchmarkResult], disk_info: Dict, output_path: str
):
    """
    Export benchmark results to JSON file.

    Args:
            results: List of BenchmarkResult objects
            disk_info: Dict with disk information
            output_path: Path to output JSON file
    """
    from .core import get_bench_cache_dir

    cache_dir = str(get_bench_cache_dir())

    data: dict = {
        "disk": {
            "disk_id": disk_info["disk_id"],
            "partitions": disk_info["partitions"],
            "total_bytes": disk_info["total_bytes"],
            "free_bytes": disk_info["free_bytes"],
            "cache_dir": cache_dir,
        },
        "benchmarks": [],
    }

    for result in results:
        bench_data = {
            "test_name": result.test_name,
            "throughput_mbps": result.throughput_mbps,
            "iops": result.iops,
            "min_latency_ms": result.min_latency_ms,
            "avg_latency_ms": result.avg_latency_ms,
            "max_latency_ms": result.max_latency_ms,
            "p50_latency_ms": result.p50_latency_ms,
            "p95_latency_ms": result.p95_latency_ms,
            "p99_latency_ms": result.p99_latency_ms,
            "duration_ms": result.duration_ms,
            "error": result.error,
        }
        data["benchmarks"].append(bench_data)

    try:
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"[{theme().colors.ok}]✓ Results exported to {output_path}[/]")
    except Exception as e:
        console.print(f"[{theme().colors.danger}]✗ Failed to export results: {e}[/]")


def benchmark_command(args) -> int:
    """
    Main command handler for disk benchmarking.

    Args:
            args: Parsed command-line arguments

    Returns:
            Exit code (0 for success, 1 for error)
    """
    t = theme()
    c = t.colors
    console.print()
    console.print(
        Panel(
            "SOT Disk Benchmark Tool",
            style=f"bold {c.accent}",
            box=t.design.app_box,
            expand=False,
            padding=(0, 6),
        )
    )
    console.print()

    # Get available physical disks
    physical_disks = get_physical_disks()
    if not physical_disks:
        console.print(
            f"[{c.danger}]No accessible disks found. "
            "Run with elevated privileges if needed.[/]"
        )
        return 1

    # Sort disks by free space (descending)
    physical_disks.sort(key=lambda d: d["free_bytes"], reverse=True)

    # Interactive disk selection
    selected_index = display_disk_selection(physical_disks)
    if selected_index < 0:
        console.print(f"[{c.warn}]Benchmark cancelled.[/]")
        return 0

    selected_disk = physical_disks[selected_index]
    largest_partition = selected_disk["largest_partition"]
    disk_id = selected_disk["disk_id"]
    mountpoint = largest_partition["mountpoint"]

    # Extract volume name from mountpoint
    volume_name = Path(mountpoint).name or mountpoint
    if not volume_name or volume_name == "/":
        volume_name = "System"

    # Verify write permissions and available space on cache directory
    try:
        from .core import get_bench_cache_dir

        cache_dir = get_bench_cache_dir()
        with tempfile.NamedTemporaryFile(
            dir=str(cache_dir), delete=True, prefix="sot_bench_"
        ):
            pass
    except (PermissionError, OSError) as e:
        console.print(
            f"[{c.danger}]✗ Cannot write to cache directory: {e}[/]\n"
            f"[{c.warn}]Try running with elevated privileges (sudo) or check disk space.[/]"
        )
        return 1

    # Run benchmarks with progress
    console.print(f"[bold {c.primary}]Running benchmarks on {volume_name}...[/]\n")
    console.print(f"[{c.muted}]Per-benchmark duration: {args.duration}s[/]\n")

    benchmark = DiskBenchmark(disk_id, mountpoint, duration_seconds=args.duration)
    results = []

    import time

    from rich.progress import BarColumn, Progress, TextColumn

    benchmark_start_time = time.time()

    class ElapsedTimeColumn(TextColumn):
        """Custom column to show elapsed time in HH:MM:SS.CS format."""

        def __init__(self, start_time):
            self.start_time = start_time
            super().__init__("")

        def render(self, task):
            elapsed = time.time() - self.start_time
            hours = int(elapsed // 3600)
            remaining = elapsed % 3600
            minutes = int(remaining // 60)
            seconds = remaining % 60
            centiseconds = int((seconds % 1) * 100)
            return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}.{centiseconds:02d}"

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style=c.ok, finished_style=c.ok),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ElapsedTimeColumn(benchmark_start_time),
    ) as progress:
        tests = [
            ("Sequential Read", benchmark.sequential_read_test),
            ("Sequential Write", benchmark.sequential_write_test),
            ("Random Read IOPS", benchmark.random_read_test),
            ("Random Write IOPS", benchmark.random_write_test),
        ]

        task = progress.add_task(
            f"[{c.accent}]Benchmarking...[/]", total=len(tests), visible=True
        )

        for test_name, test_func in tests:
            result = test_func()
            results.append(result)
            progress.advance(task)

    # Display results
    console.print("\n")
    display_results(results, selected_disk)

    # Export to JSON if requested
    if args.output:
        export_results_json(results, selected_disk, args.output)

    return 0
