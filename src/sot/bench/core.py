"""Core disk benchmarking functionality."""

import os
import random
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


def get_bench_cache_dir() -> Path:
    """
    Get the benchmark cache directory, creating it if necessary.

    Returns:
            Path object pointing to ~/.sot/bench/
    """
    cache_dir = Path.home() / ".sot" / "bench"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"Failed to create cache directory {cache_dir}: {e}")
    return cache_dir


def drop_caches() -> None:
    """
    Drop OS disk caches to ensure fair benchmarking.

    Requires elevated privileges (sudo) to work effectively.
    On failure, silently continues - benchmarks will still run but may be cache-affected.
    """
    try:
        if sys.platform == "darwin":
            # macOS: drop caches using purge command
            subprocess.run(["purge"], capture_output=True, timeout=5)
        elif sys.platform.startswith("linux"):
            # Linux: write to /proc/sys/vm/drop_caches (requires root)
            subprocess.run(
                ["sync"],  # Ensure all pending data is written
                capture_output=True,
                timeout=5,
            )
            subprocess.run(
                ["bash", "-c", "echo 3 > /proc/sys/vm/drop_caches"],
                capture_output=True,
                timeout=5,
            )
    except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
        # Cache drop failed or not available - continue anyway
        pass


@dataclass
class BenchmarkResult:
    """Result of a single benchmark test."""

    test_name: str
    throughput_mbps: Optional[float] = None
    iops: Optional[float] = None
    min_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    duration_ms: float = 0.0
    error: Optional[str] = None

    def is_error(self) -> bool:
        """Check if the test had an error."""
        return self.error is not None


class DiskBenchmark:
    """Disk benchmarking utility for sequential and random I/O tests."""

    def __init__(self, disk_id: str, mountpoint: str, duration_seconds: float = 10.0):
        """
        Initialize disk benchmark for a given disk.

        Args:
            disk_id: Physical disk identifier (e.g., /dev/disk3)
            mountpoint: Path to the disk/mountpoint (for reference only)
            duration_seconds: Duration for each benchmark test in seconds (default: 10s)
        """
        self.disk_id = disk_id
        self.mountpoint = mountpoint
        self.cache_dir = get_bench_cache_dir()
        self.duration_seconds = duration_seconds
        self.block_size = 4096
        self.large_block_size = 1024 * 1024  # 1 MB for sequential tests

    def sequential_read_test(self) -> BenchmarkResult:
        """
        Measure sequential read throughput.

        Runs for the duration specified in self.duration_seconds.

        Returns:
            BenchmarkResult with throughput and latency metrics
        """
        result = BenchmarkResult(test_name="Sequential Read")

        try:
            # Create temporary test file
            with tempfile.NamedTemporaryFile(
                dir=str(self.cache_dir), delete=False, prefix="sot_bench_"
            ) as tmp:
                tmp_path = tmp.name

            try:
                # Write test data (4GB to avoid cache loop-back)
                test_file_size_mb = 4096
                test_data = os.urandom(self.large_block_size)
                with open(tmp_path, "wb") as f:
                    for _ in range(test_file_size_mb):
                        f.write(test_data)
                    f.flush()
                    os.fsync(f.fileno())

                # Drop caches before benchmark
                drop_caches()
                time.sleep(0.5)  # Brief delay after cache drop

                # Warmup phase: read some data to warm up the disk
                with open(tmp_path, "rb") as f:
                    warmup_end = time.time() + 2.0  # 2 second warmup
                    while time.time() < warmup_end:
                        _ = f.read(self.large_block_size)
                    f.seek(0)

                # Perform sequential read benchmark for specified duration
                latencies = []
                bytes_read = 0
                start_time = time.time()
                end_time = start_time + self.duration_seconds

                with open(tmp_path, "rb") as f:
                    while time.time() < end_time:
                        # Time the actual read operation
                        op_start = time.time()
                        chunk = f.read(self.large_block_size)
                        op_latency = (time.time() - op_start) * 1000

                        if not chunk:
                            # End of file - don't loop back
                            break

                        latencies.append(op_latency)
                        bytes_read += len(chunk)

                duration = time.time() - start_time
                result.duration_ms = duration * 1000

                # Calculate metrics
                result.throughput_mbps = (bytes_read / duration) / (1024 * 1024)

                if latencies:
                    self._calculate_latency_stats(latencies, result)

            finally:
                # Clean up
                if Path(tmp_path).exists():
                    os.remove(tmp_path)

        except Exception as e:
            result.error = str(e)

        return result

    def sequential_write_test(self) -> BenchmarkResult:
        """
        Measure sequential write throughput.

        Runs for the duration specified in self.duration_seconds.

        Returns:
            BenchmarkResult with throughput and latency metrics
        """
        result = BenchmarkResult(test_name="Sequential Write")

        try:
            with tempfile.NamedTemporaryFile(
                dir=str(self.cache_dir), delete=False, prefix="sot_bench_"
            ) as tmp:
                tmp_path = tmp.name

            try:
                # Create test data
                test_data = os.urandom(self.large_block_size)
                latencies = []
                bytes_written = 0

                # Drop caches before benchmark
                drop_caches()
                time.sleep(0.5)  # Brief delay after cache drop

                # Warmup phase: write some data to warm up the disk
                with open(tmp_path, "wb") as f:
                    warmup_end = time.time() + 2.0  # 2 second warmup
                    while time.time() < warmup_end:
                        f.write(test_data)
                        f.flush()
                        os.fsync(f.fileno())

                # Perform sequential write benchmark for specified duration
                start_time = time.time()
                end_time = start_time + self.duration_seconds

                with open(tmp_path, "wb") as f:
                    while time.time() < end_time:
                        # Time the actual write and sync operation
                        op_start = time.time()
                        f.write(test_data)
                        f.flush()
                        os.fsync(f.fileno())
                        op_latency = (time.time() - op_start) * 1000
                        latencies.append(op_latency)
                        bytes_written += self.large_block_size

                duration = time.time() - start_time
                result.duration_ms = duration * 1000

                # Calculate metrics
                result.throughput_mbps = (bytes_written / duration) / (1024 * 1024)

                if latencies:
                    self._calculate_latency_stats(latencies, result)

            finally:
                # Clean up
                if Path(tmp_path).exists():
                    os.remove(tmp_path)

        except Exception as e:
            result.error = str(e)

        return result

    def random_read_test(self) -> BenchmarkResult:
        """
        Measure random read IOPS.

        Runs for the duration specified in self.duration_seconds.

        Returns:
            BenchmarkResult with IOPS and latency metrics
        """
        result = BenchmarkResult(test_name="Random Read IOPS")

        try:
            # Create temporary test file (512 MB for random access)
            with tempfile.NamedTemporaryFile(
                dir=str(self.cache_dir), delete=False, prefix="sot_bench_"
            ) as tmp:
                tmp_path = tmp.name

            try:
                # Write test file (4GB for good random distribution)
                file_size_mb = 4096
                test_data = os.urandom(self.large_block_size)
                with open(tmp_path, "wb") as f:
                    for _ in range(file_size_mb):
                        f.write(test_data)
                    f.flush()
                    os.fsync(f.fileno())

                # Get file size
                file_size = os.path.getsize(tmp_path)

                # Drop caches before benchmark
                drop_caches()
                time.sleep(0.5)  # Brief delay after cache drop

                # Warmup phase: perform random reads to warm up the disk
                with open(tmp_path, "rb") as f:
                    warmup_end = time.time() + 2.0  # 2 second warmup
                    while time.time() < warmup_end:
                        max_offset = max(0, file_size - self.block_size)
                        offset = random.randint(0, max_offset)
                        f.seek(offset)
                        _ = f.read(self.block_size)

                # Perform random read benchmark for specified duration
                latencies = []
                num_ops = 0
                start_time = time.time()
                end_time = start_time + self.duration_seconds

                with open(tmp_path, "rb") as f:
                    while time.time() < end_time:
                        # Random position
                        max_offset = max(0, file_size - self.block_size)
                        offset = random.randint(0, max_offset)
                        f.seek(offset)

                        # Time the actual read operation
                        op_start = time.time()
                        chunk = f.read(self.block_size)
                        op_latency = (time.time() - op_start) * 1000
                        if chunk:  # Only count successful reads
                            latencies.append(op_latency)
                            num_ops += 1

                duration = time.time() - start_time
                result.duration_ms = duration * 1000

                # Calculate metrics
                result.iops = num_ops / duration

                if latencies:
                    self._calculate_latency_stats(latencies, result)

            finally:
                # Clean up
                if Path(tmp_path).exists():
                    os.remove(tmp_path)

        except Exception as e:
            result.error = str(e)

        return result

    def random_write_test(self) -> BenchmarkResult:
        """
        Measure random write IOPS.

        Runs for the duration specified in self.duration_seconds.

        Returns:
            BenchmarkResult with IOPS and latency metrics
        """
        result = BenchmarkResult(test_name="Random Write IOPS")

        try:
            with tempfile.NamedTemporaryFile(
                dir=str(self.cache_dir), delete=False, prefix="sot_bench_"
            ) as tmp:
                tmp_path = tmp.name

            try:
                # Create test file (4GB for good random distribution)
                file_size_mb = 4096
                test_data = os.urandom(self.large_block_size)
                with open(tmp_path, "wb") as f:
                    for _ in range(file_size_mb):
                        f.write(test_data)
                    f.flush()
                    os.fsync(f.fileno())

                # Get file size
                file_size = os.path.getsize(tmp_path)

                # Drop caches before benchmark
                drop_caches()
                time.sleep(0.5)  # Brief delay after cache drop

                # Warmup phase: perform random writes to warm up the disk
                write_data = os.urandom(self.block_size)
                with open(tmp_path, "r+b") as f:
                    warmup_end = time.time() + 2.0  # 2 second warmup
                    while time.time() < warmup_end:
                        max_offset = max(0, file_size - self.block_size)
                        offset = random.randint(0, max_offset)
                        f.seek(offset)
                        f.write(write_data)
                        f.flush()
                        os.fsync(f.fileno())

                # Perform random write benchmark for specified duration
                latencies = []
                write_data = os.urandom(self.block_size)
                num_ops = 0
                start_time = time.time()
                end_time = start_time + self.duration_seconds

                with open(tmp_path, "r+b") as f:
                    while time.time() < end_time:
                        # Random position
                        max_offset = max(0, file_size - self.block_size)
                        offset = random.randint(0, max_offset)
                        f.seek(offset)

                        # Time the actual write and sync operation
                        op_start = time.time()
                        f.write(write_data)
                        f.flush()
                        os.fsync(f.fileno())
                        op_latency = (time.time() - op_start) * 1000
                        latencies.append(op_latency)
                        num_ops += 1

                duration = time.time() - start_time
                result.duration_ms = duration * 1000

                # Calculate metrics
                result.iops = num_ops / duration

                if latencies:
                    self._calculate_latency_stats(latencies, result)

            finally:
                # Clean up
                if Path(tmp_path).exists():
                    os.remove(tmp_path)

        except Exception as e:
            result.error = str(e)

        return result

    def run_benchmarks(self) -> List[BenchmarkResult]:
        """
        Run all benchmark tests on the disk.

        Returns:
            List of BenchmarkResult objects for each test
        """
        results = []

        # Run all tests
        results.append(self.sequential_read_test())
        results.append(self.sequential_write_test())
        results.append(self.random_read_test())
        results.append(self.random_write_test())

        return results

    @staticmethod
    def _calculate_latency_stats(latencies: List[float], result: BenchmarkResult):
        """
        Calculate latency statistics and update the result.

        Args:
            latencies: List of individual operation latencies in ms
            result: BenchmarkResult object to update
        """
        if not latencies:
            return

        sorted_latencies = sorted(latencies)
        result.min_latency_ms = sorted_latencies[0]
        result.max_latency_ms = sorted_latencies[-1]
        result.avg_latency_ms = statistics.mean(latencies)

        # Calculate percentiles using linear interpolation (nearest rank method)
        n = len(sorted_latencies)
        result.p50_latency_ms = statistics.median(sorted_latencies)

        # p95 and p99 using proper percentile calculation
        # Use (N * percentile) to get the index (rounding up to nearest element)
        p95_index = min(int(n * 0.95), n - 1)
        p99_index = min(int(n * 0.99), n - 1)

        result.p95_latency_ms = sorted_latencies[p95_index]
        result.p99_latency_ms = sorted_latencies[p99_index]
