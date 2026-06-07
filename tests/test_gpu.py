from sot import _gpu


def test_parse_apple_ioreg():
    # Trimmed real output from `ioreg -c IOAccelerator` on Apple Silicon.
    text = (
        '"gpu-core-count" = 14\n'
        '"PerformanceStatistics" = {"In use system memory (driver)"=0,'
        '"Alloc system memory"=2453848064,"Tiler Utilization %"=21,'
        '"Renderer Utilization %"=20,"Device Utilization %"=37,'
        '"In use system memory"=344702976}'
    )
    sample = _gpu._parse_apple_ioreg(text)
    assert sample is not None
    assert sample.util_percent == 37.0
    assert sample.mem_used == 344702976
    # Unified memory has no dedicated VRAM total.
    assert sample.mem_total is None
    assert sample.mem_alloc == 2453848064
    assert sample.cores == 14
    assert sample.renderer_util_percent == 20.0
    assert sample.tiler_util_percent == 21.0


def test_parse_apple_ioreg_ignores_driver_memory():
    # The "(driver)" variant must not be mistaken for in-use memory.
    text = '"In use system memory (driver)"=0,"In use system memory"=512'
    sample = _gpu._parse_apple_ioreg(text)
    assert sample is not None
    assert sample.mem_used == 512


def test_parse_apple_ioreg_no_match():
    assert _gpu._parse_apple_ioreg("nothing useful here") is None


def test_parse_nvidia_csv():
    text = "NVIDIA GeForce RTX 4090, 42, 1024, 24576, 55, 120.5\n"
    sample = _gpu._parse_nvidia_csv(text)
    assert sample is not None
    assert sample.name == "NVIDIA GeForce RTX 4090"
    assert sample.util_percent == 42.0
    assert sample.mem_used == 1024 * 1024 * 1024
    assert sample.mem_total == 24576 * 1024 * 1024
    assert sample.temp_c == 55.0
    assert sample.power_w == 120.5


def test_parse_nvidia_csv_handles_na():
    # Power draw is unavailable on some cards and reported as [N/A].
    text = "Tesla T4, 0, 0, 15360, 30, [N/A]"
    sample = _gpu._parse_nvidia_csv(text)
    assert sample is not None
    assert sample.power_w is None
    assert sample.util_percent == 0.0


def test_parse_nvidia_csv_first_gpu_only():
    text = "GPU-0, 10, 100, 8192, 40, 50\nGPU-1, 90, 200, 8192, 70, 90\n"
    sample = _gpu._parse_nvidia_csv(text)
    assert sample is not None
    assert sample.name == "GPU-0"
    assert sample.util_percent == 10.0


def test_parse_nvidia_csv_empty():
    assert _gpu._parse_nvidia_csv("") is None


def test_parse_amd_json():
    text = (
        '{"card0": {"GPU use (%)": "73", '
        '"VRAM Total Memory (B)": "17163091968", '
        '"VRAM Total Used Memory (B)": "1234567", '
        '"Temperature (Sensor edge) (C)": "61.0", '
        '"Average Graphics Package Power (W)": "95.0", '
        '"Card Series": "Radeon RX 7900 XTX"}}'
    )
    sample = _gpu._parse_amd_json(text)
    assert sample is not None
    assert sample.util_percent == 73.0
    assert sample.mem_total == 17163091968
    assert sample.mem_used == 1234567
    assert sample.temp_c == 61.0
    assert sample.power_w == 95.0
    assert sample.name == "Radeon RX 7900 XTX"


def test_parse_amd_json_invalid():
    assert _gpu._parse_amd_json("not json") is None


def test_gpu_sample_is_empty():
    assert _gpu.GpuSample().is_empty()
    assert not _gpu.GpuSample(util_percent=0.0).is_empty()


def test_to_float():
    assert _gpu._to_float("12.5") == 12.5
    assert _gpu._to_float(" 7 ") == 7.0
    assert _gpu._to_float("[N/A]") is None
    assert _gpu._to_float(None) is None
    assert _gpu._to_float("") is None
