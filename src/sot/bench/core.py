"""Core disk benchmarking functionality."""

import os
import random
import statistics
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

    def __init__(self, disk_id: str, mountpoint: str, duration_seconds: float = 30.0):
        """
        Initialize disk benchmark for a given disk.

        Args:
            disk_id: Physical disk identifier (e.g., /dev/disk3)
            mountpoint: Path to the disk/mountpoint (for reference only)
            duration_seconds: Duration for each benchmark test in seconds (default: 30s)
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
                # Write test data (larger file for duration-based testing)
                test_file_size_mb = 512
                test_data = os.urandom(self.large_block_size)
                with open(tmp_path, "wb") as f:
                    for _ in range(test_file_size_mb):
                        f.write(test_data)

                # Perform sequential read benchmark for specified duration
                latencies = []
                bytes_read = 0
                start_time = time.time()
                end_time = start_time + self.duration_seconds

                with open(tmp_path, "rb") as f:
                    while time.time() < end_time:
                        chunk = f.read(self.large_block_size)
                        if not chunk:
                            f.seek(0)  # Restart from beginning
                            continue

                        # Record individual operation latency
                        op_start = time.time()
                        _ = chunk  # Force evaluation
                        op_latency = (time.time() - op_start) * 1000
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

                # Perform sequential write benchmark for specified duration
                start_time = time.time()
                end_time = start_time + self.duration_seconds

                with open(tmp_path, "wb") as f:
                    while time.time() < end_time:
                        op_start = time.time()
                        f.write(test_data)
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
                # Write test file
                file_size_mb = 512
                test_data = os.urandom(self.large_block_size)
                with open(tmp_path, "wb") as f:
                    for _ in range(file_size_mb):
                        f.write(test_data)

                # Get file size
                file_size = os.path.getsize(tmp_path)

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

                        # Timed read
                        op_start = time.time()
                        _ = f.read(self.block_size)
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
                # Create test file
                file_size_mb = 512
                test_data = os.urandom(self.large_block_size)
                with open(tmp_path, "wb") as f:
                    for _ in range(file_size_mb):
                        f.write(test_data)

                # Get file size
                file_size = os.path.getsize(tmp_path)

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

                        # Timed write
                        op_start = time.time()
                        f.write(write_data)
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

        # Calculate percentiles
        result.p50_latency_ms = statistics.median(sorted_latencies)

        # p95 and p99
        p95_index = int(len(sorted_latencies) * 0.95)
        p99_index = int(len(sorted_latencies) * 0.99)

        result.p95_latency_ms = (
            sorted_latencies[p95_index]
            if p95_index < len(sorted_latencies)
            else sorted_latencies[-1]
        )
        result.p99_latency_ms = (
            sorted_latencies[p99_index]
            if p99_index < len(sorted_latencies)
            else sorted_latencies[-1]
        )
