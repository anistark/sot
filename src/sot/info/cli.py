"""Command-line interface for system information display."""

import getpass
import platform
import subprocess
import time
from datetime import timedelta
from typing import List, Optional, Tuple

import distro
import psutil
from rich.console import Console

from .._helpers import sizeof_fmt
from .logos import get_logo_for_os

console = Console()


def get_uptime() -> str:
    """Get system uptime as formatted string."""
    boot_time = psutil.boot_time()
    uptime = timedelta(seconds=time.time() - boot_time)

    days = uptime.days
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds // 60) % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or len(parts) == 0:
        parts.append(f"{minutes}m")

    return " ".join(parts)


def get_os_info() -> str:
    """Get OS information."""
    system = platform.system()

    if system == "Darwin":
        version = platform.mac_ver()[0]
        # Map version to release name
        major_version = int(version.split(".")[0])
        version_names = {
            15: "Sequoia",
            14: "Sonoma",
            13: "Ventura",
            12: "Monterey",
            11: "Big Sur",
            10: "Catalina",
        }
        name = version_names.get(major_version, "")
        if name:
            return f"macOS {version} {name}"
        return f"macOS {version}"
    elif system == "Linux":
        return f"{distro.name()} {distro.version()}"
    else:
        return f"{system} {platform.release()}"


def get_kernel_version() -> str:
    """Get kernel version."""
    return platform.release()


def get_hostname() -> str:
    """Get hostname."""
    return platform.node()


def get_machine_model() -> Optional[str]:
    """Get machine model identifier (macOS specific)."""
    system = platform.system()

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.model"], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

    return None


def get_model_name() -> Optional[str]:
    """Get user-friendly model name (e.g., 'MacBook Pro')."""
    system = platform.system()

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "Model Name:" in line:
                        return line.split("Model Name:")[1].strip()
        except Exception:
            pass

    return None


def get_model_number() -> Optional[str]:
    """Get model number/SKU (e.g., 'MKGR3HN/A')."""
    system = platform.system()

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "Model Number:" in line:
                        return line.split("Model Number:")[1].strip()
        except Exception:
            pass

    return None


def get_serial_number() -> Optional[str]:
    """Get system serial number."""
    system = platform.system()

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "Serial Number (system):" in line:
                        return line.split("Serial Number (system):")[1].strip()
        except Exception:
            pass

    return None


def get_chip_details() -> Optional[str]:
    """Get chip details with performance/efficiency core breakdown."""
    system = platform.system()

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                chip_name = None
                total_cores = None
                perf_cores = None
                eff_cores = None

                for line in result.stdout.split("\n"):
                    if "Chip:" in line:
                        chip_name = line.split("Chip:")[1].strip()
                    elif "Total Number of Cores:" in line:
                        # Extract format like "8 (6 performance and 2 efficiency)"
                        core_info = line.split("Total Number of Cores:")[1].strip()
                        # Parse the core breakdown
                        import re

                        match = re.search(
                            r"(\d+)\s*\((\d+)\s+performance\s+and\s+(\d+)\s+efficiency\)",
                            core_info,
                        )
                        if match:
                            total_cores = match.group(1)
                            perf_cores = match.group(2)
                            eff_cores = match.group(3)
                        else:
                            total_cores = core_info

                if chip_name:
                    if perf_cores and eff_cores:
                        return f"{chip_name} ({perf_cores}P + {eff_cores}E cores)"
                    elif total_cores:
                        return f"{chip_name} ({total_cores} cores)"
                    else:
                        return chip_name
        except Exception:
            pass

    return None


def get_firmware_version() -> Optional[str]:
    """Get system firmware version."""
    system = platform.system()

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "System Firmware Version:" in line:
                        return line.split("System Firmware Version:")[1].strip()
        except Exception:
            pass

    return None


def get_de_wm_info() -> Tuple[Optional[str], Optional[str]]:
    """Get Desktop Environment and Window Manager."""
    system = platform.system()

    if system == "Darwin":
        return "Aqua", "Quartz Compositor"
    elif system == "Linux":
        # Try to detect DE and WM from environment variables
        import os

        de = os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION")
        wm = os.environ.get("XDG_SESSION_TYPE")
        return de, wm

    return None, None


def get_shell_info() -> str:
    """Get shell information."""
    import os

    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        return shell_path.split("/")[-1]
    return "Unknown"


def get_terminal_info() -> Optional[str]:
    """Get terminal emulator information."""
    import os

    # Check common terminal environment variables
    term_program = os.environ.get("TERM_PROGRAM")
    if term_program:
        version = os.environ.get("TERM_PROGRAM_VERSION", "")
        if version:
            return f"{term_program} ({version})"
        return term_program

    # Check for iTerm2
    if "ITERM_SESSION_ID" in os.environ:
        return "iTerm2"

    # Fallback to TERM variable
    return os.environ.get("TERM")


def get_cpu_info() -> Tuple[str, int]:
    """Get CPU information."""
    system = platform.system()
    cpu_name = None

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                cpu_name = result.stdout.strip()
        except Exception:
            pass
    elif system == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        cpu_name = line.split(":")[1].strip()
                        break
        except Exception:
            pass

    if not cpu_name:
        cpu_name = platform.processor() or "Unknown"

    cpu_count = psutil.cpu_count(logical=True)
    return cpu_name, cpu_count


def get_gpu_info() -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Get GPU information (model, cores, VRAM).

    Returns:
        Tuple of (gpu_model, gpu_cores, vram)
    """
    system = platform.system()
    gpu_model = None
    gpu_cores = None
    vram = None

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                lines = result.stdout.split("\n")
                for i, line in enumerate(lines):
                    if "Chipset Model:" in line:
                        gpu_model = line.split("Chipset Model:")[1].strip()
                    elif "Total Number of Cores:" in line:
                        cores_str = line.split("Total Number of Cores:")[1].strip()
                        try:
                            gpu_cores = int(cores_str)
                        except ValueError:
                            pass
                    elif "VRAM" in line or "Memory:" in line:
                        # Try to extract VRAM information
                        mem_info = line.split(":")
                        if len(mem_info) > 1:
                            vram = mem_info[1].strip()
        except Exception:
            pass

    return gpu_model, gpu_cores, vram


def get_cpu_load() -> float:
    """Get CPU load percentage."""
    return psutil.cpu_percent(interval=0.1)


def get_memory_info() -> Tuple[int, int]:
    """Get memory information (used, total)."""
    mem = psutil.virtual_memory()
    return mem.used, mem.total


def get_battery_info() -> Optional[Tuple[float, bool]]:
    """Get battery information (percentage, is_charging)."""
    if hasattr(psutil, "sensors_battery"):
        bat = psutil.sensors_battery()
        if bat:
            return bat.percent, bat.power_plugged
    return None


def get_brightness() -> Optional[int]:
    """Get display brightness (macOS specific)."""
    system = platform.system()

    if system == "Darwin":
        try:
            # Try to get brightness using brightness utility if installed
            result = subprocess.run(
                ["brightness", "-l"], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if lines:
                    # Parse first display brightness
                    for line in lines:
                        if "brightness" in line.lower():
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part == "brightness" and i + 1 < len(parts):
                                    try:
                                        brightness_val = float(parts[i + 1])
                                        return int(brightness_val * 100)
                                    except ValueError:
                                        pass
        except Exception:
            pass

    return None


def get_resolution() -> List[str]:
    """Get screen resolutions with display names."""
    system = platform.system()
    resolutions = []

    if system == "Darwin":
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                lines = result.stdout.split("\n")
                current_display_name = None
                current_res = None

                for i, line in enumerate(lines):
                    # Check for display name (appears before Resolution)
                    stripped = line.strip()
                    if stripped.endswith(":") and "Resolution:" not in line:
                        # This might be a display name like "Color LCD:" or "LG IPS FULLHD:"
                        potential_name = stripped.rstrip(":")
                        # Check if next few lines have Resolution
                        for check_j in range(i + 1, min(i + 5, len(lines))):
                            if "Resolution:" in lines[check_j]:
                                current_display_name = potential_name
                                break

                    if "Resolution:" in line:
                        res = line.split("Resolution:")[1].strip()
                        # Extract just the resolution numbers (e.g., "3024 x 1964")
                        # Remove extra descriptions like "Retina" or "(1080p FHD...)"
                        parts = res.split()
                        if len(parts) >= 3:
                            # Keep just "width x height" and optionally "Retina"
                            current_res = f"{parts[0]} x {parts[2]}"
                            if "Retina" in res:
                                current_res += " Retina"
                        else:
                            current_res = res

                        # Look ahead for refresh rate info
                        # Check next few lines for either "Refresh Rate:" or "UI Looks like:"
                        for j in range(i + 1, min(i + 10, len(lines))):
                            next_line = lines[j]
                            if "Refresh Rate:" in next_line:
                                refresh = (
                                    next_line.split("Refresh Rate:")[1]
                                    .strip()
                                    .split()[0]
                                )
                                current_res += f"@{refresh}Hz"
                                break
                            elif "UI Looks like:" in next_line:
                                # Extract refresh rate from UI Looks like line
                                if "@" in next_line:
                                    try:
                                        refresh_part = next_line.split("@")[1].strip()
                                        refresh = refresh_part.split()[0]
                                        current_res += f"@{refresh}"
                                    except (IndexError, AttributeError):
                                        pass
                                break
                            elif "Resolution:" in next_line or stripped.endswith(":"):
                                # Hit another display
                                break

                        # Add the resolution with display name if available
                        if current_res:
                            if current_display_name:
                                resolutions.append(
                                    f"{current_res} ({current_display_name})"
                                )
                            else:
                                resolutions.append(current_res)
                            current_res = None
                            current_display_name = None

        except Exception:
            pass

    return resolutions


def get_package_counts() -> List[str]:
    """Get installed package counts."""
    system = platform.system()
    packages = []

    if system == "Darwin":
        # Check Homebrew
        try:
            result = subprocess.run(
                ["brew", "list", "--formula"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                count = len(result.stdout.strip().split("\n"))
                packages.append(f"{count} (Homebrew)")
        except Exception:
            pass

        # Check Cargo
        try:
            import os

            cargo_bin = os.path.expanduser("~/.cargo/bin")
            if os.path.exists(cargo_bin):
                count = len(
                    [
                        f
                        for f in os.listdir(cargo_bin)
                        if os.path.isfile(os.path.join(cargo_bin, f))
                    ]
                )
                packages.append(f"{count} (cargo)")
        except Exception:
            pass

    elif system == "Linux":
        # Check various package managers
        package_managers = [
            (["dpkg", "-l"], "dpkg"),
            (["rpm", "-qa"], "rpm"),
            (["pacman", "-Q"], "pacman"),
        ]

        for cmd, name in package_managers:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    count = len(result.stdout.strip().split("\n"))
                    packages.append(f"{count} ({name})")
                    break
            except Exception:
                pass

    return packages


def format_system_info() -> str:
    """Format all system information with logo."""
    system = platform.system()

    # Get distro name for Linux systems
    distro_name = ""
    if system == "Linux":
        distro_name = distro.name()

    # Get logo based on OS and distro
    logo = get_logo_for_os(system, distro_name)

    # Get all system information
    username = getpass.getuser()
    hostname = get_hostname()
    model_name = get_model_name()
    model_number = get_model_number()
    machine = get_machine_model()
    serial = get_serial_number()
    kernel = get_kernel_version()
    os_info = get_os_info()
    chip_details = get_chip_details()
    firmware = get_firmware_version()
    de, wm = get_de_wm_info()
    shell = get_shell_info()
    terminal = get_terminal_info()
    brightness = get_brightness()
    resolutions = get_resolution()
    uptime = get_uptime()
    mem_used, mem_total = get_memory_info()
    battery = get_battery_info()
    gpu_model, gpu_cores, vram = get_gpu_info()

    # Build info lines with proper alignment and categorization
    info_lines = []

    # === SYSTEM INFORMATION ===
    info_lines.append(f"Host        -  {username}@{hostname}")
    if model_name:
        info_lines.append(f"Model       -  {model_name}")
    if model_number:
        info_lines.append(f"SKU         -  {model_number}")
    if machine:
        info_lines.append(f"Identifier  -  {machine}")
    if serial:
        info_lines.append(f"Serial      -  {serial}")

    info_lines.append("")  # Empty line separator

    # === SOFTWARE ===
    info_lines.append(f"OS          -  {os_info}")
    info_lines.append(f"Kernel      -  {kernel}")
    if firmware:
        info_lines.append(f"Firmware    -  {firmware}")
    if de:
        info_lines.append(f"DE          -  {de}")
    if wm:
        info_lines.append(f"WM          -  {wm}")
    info_lines.append(f"Shell       -  {shell}")
    if terminal:
        info_lines.append(f"Terminal    -  {terminal}")

    info_lines.append("")  # Empty line separator

    # === HARDWARE ===
    if chip_details:
        info_lines.append(f"Chip        -  {chip_details}")
    if gpu_model:
        gpu_info = gpu_model
        if gpu_cores:
            gpu_info += f" ({gpu_cores} cores)"
        if vram:
            gpu_info += f", {vram}"
        info_lines.append(f"GPU         -  {gpu_info}")
    info_lines.append(
        f"Memory      -  {sizeof_fmt(mem_used)} / {sizeof_fmt(mem_total)}"
    )

    info_lines.append("")  # Empty line separator

    # === DISPLAYS ===
    if resolutions:
        info_lines.append(f"Displays    -  {resolutions[0]}")
        for res in resolutions[1:]:
            info_lines.append(f"               {res}")
    if brightness is not None:
        info_lines.append(f"Brightness  -  {brightness}%")

    info_lines.append("")  # Empty line separator

    # === STATUS ===
    info_lines.append(f"Uptime      -  {uptime}")
    if battery:
        percent, charging = battery
        status = "Charging" if charging else "Discharging"
        info_lines.append(f"Battery     -  {percent:.0f}% & {status}")

    # Combine logo and info
    output_lines = []
    max_logo_width = max(len(line) for line in logo)

    for i in range(max(len(logo), len(info_lines))):
        logo_part = logo[i] if i < len(logo) else " " * max_logo_width
        info_part = info_lines[i] if i < len(info_lines) else ""
        output_lines.append(f"{logo_part}  {info_part}")

    return "\n".join(output_lines)


def info_command(args) -> int:
    """Display system information with logo."""
    try:
        output = format_system_info()
        console.print(output)
        return 0
    except Exception as e:
        console.print(f"[red]Error displaying system info: {e}[/red]")
        return 1
