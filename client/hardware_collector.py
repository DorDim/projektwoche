import platform
import socket
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psutil


def _run_command(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None


def _run_powershell(command: str) -> str | None:
    return _run_command(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ]
    )


def _first_data_line(output: str | None, ignored_keywords: tuple[str, ...] = ()) -> str | None:
    if not output:
        return None
    for line in output.splitlines():
        value = line.strip()
        if not value:
            continue
        lower_value = value.lower()
        if any(keyword in lower_value for keyword in ignored_keywords):
            continue
        return value
    return None


def _normalize_vendor(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    placeholder_values = {
        "to be filled by o.e.m.",
        "to be filled by oem",
        "default string",
        "system manufacturer",
        "none",
    }
    if normalized.lower() in placeholder_values:
        return None
    return normalized


def get_hostname() -> str:
    return socket.gethostname()


def get_client_uid() -> str:
    # Stable identifier derived from machine-id where possible.
    machine_id_paths = [Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")]
    for path in machine_id_paths:
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return f"{get_hostname()}-{value[:16]}"
    return f"{get_hostname()}-{uuid.getnode()}"


def get_cpu_info() -> dict:
    cpu_freq = psutil.cpu_freq()
    return {
        "cpu_cores": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(logical=True),
        "cpu_max_mhz": round(cpu_freq.max, 2) if cpu_freq and cpu_freq.max else None,
    }


def get_ram_total_mb() -> float:
    memory = psutil.virtual_memory()
    return round(memory.total / 1024 / 1024, 2)


def get_gpu_info() -> list[dict]:
    nvidia_output = _run_command(
        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"]
    )
    if nvidia_output:
        gpus = []
        for line in nvidia_output.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) >= 3:
                gpus.append(
                    {
                        "name": parts[0],
                        "memory_mb": float(parts[1]) if parts[1].replace(".", "", 1).isdigit() else None,
                        "driver": parts[2],
                    }
                )
        if gpus:
            return gpus

    if platform.system().lower() == "windows":
        wmic = _run_command(["wmic", "path", "win32_videocontroller", "get", "name"])
        if wmic:
            names = [line.strip() for line in wmic.splitlines() if line.strip() and "name" not in line.lower()]
            return [{"name": name} for name in names]
        return []

    lspci = _run_command(["lspci"])
    if lspci:
        names = [line for line in lspci.splitlines() if "VGA" in line or "3D controller" in line]
        return [{"name": name} for name in names]
    return []


def _read_text_file(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
        return value or None
    except OSError:
        return None


def get_motherboard_vendor() -> str | None:
    if platform.system().lower() == "windows":
        output = _run_command(["wmic", "baseboard", "get", "Manufacturer"])
        vendor = _normalize_vendor(_first_data_line(output, ignored_keywords=("manufacturer",)))
        if vendor:
            return vendor

        output = _run_powershell(
            "(Get-CimInstance Win32_BaseBoard | Select-Object -ExpandProperty Manufacturer | Select-Object -First 1)"
        )
        vendor = _normalize_vendor(_first_data_line(output))
        if vendor:
            return vendor

        output = _run_powershell(
            "(Get-CimInstance Win32_ComputerSystem | Select-Object -ExpandProperty Manufacturer | Select-Object -First 1)"
        )
        return _normalize_vendor(_first_data_line(output))
    return _read_text_file(Path("/sys/devices/virtual/dmi/id/board_vendor"))


def get_bios_vendor() -> str | None:
    if platform.system().lower() == "windows":
        output = _run_command(["wmic", "bios", "get", "Manufacturer"])
        vendor = _normalize_vendor(_first_data_line(output, ignored_keywords=("manufacturer",)))
        if vendor:
            return vendor

        output = _run_powershell(
            "(Get-CimInstance Win32_BIOS | Select-Object -ExpandProperty Manufacturer | Select-Object -First 1)"
        )
        return _normalize_vendor(_first_data_line(output))
    return _read_text_file(Path("/sys/devices/virtual/dmi/id/bios_vendor"))


def get_disks() -> list[dict]:
    disks: list[dict] = []
    for partition in psutil.disk_partitions(all=False):
        if partition.fstype == "":
            continue
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except OSError:
            continue
        disks.append(
            {
                "mountpoint": partition.mountpoint,
                "filesystem": partition.fstype,
                "total_gb": round(usage.total / 1024 / 1024 / 1024, 2),
                "used_gb": round(usage.used / 1024 / 1024 / 1024, 2),
                "free_gb": round(usage.free / 1024 / 1024 / 1024, 2),
                "free_percent": round(100 - usage.percent, 2),
            }
        )
    return disks


def get_windows_version() -> str:
    return platform.platform()


def get_network_adapters() -> list[dict]:
    adapters = []
    all_interfaces = psutil.net_if_addrs()
    for name, addresses in all_interfaces.items():
        adapter = {"name": name, "ipv4": [], "ipv6": [], "mac": None}
        for address in addresses:
            family = str(address.family)
            if "AddressFamily.AF_INET6" in family:
                adapter["ipv6"].append(address.address.split("%")[0])
            elif "AddressFamily.AF_INET" in family:
                adapter["ipv4"].append(address.address)
            elif "AF_PACKET" in family or "psutil.AF_LINK" in family:
                if address.address and address.address != "00:00:00:00:00:00":
                    adapter["mac"] = address.address
        adapters.append(adapter)
    return adapters


def get_uptime_seconds() -> int:
    return int(time.time() - psutil.boot_time())


def get_cpu_temperature() -> float | None:
    try:
        temperatures = psutil.sensors_temperatures()
    except (AttributeError, OSError):
        return None
    for entries in temperatures.values():
        for entry in entries:
            if entry.current is not None:
                return float(entry.current)
    return None


def get_fan_speed() -> int | None:
    try:
        fans = psutil.sensors_fans()
    except (AttributeError, OSError):
        return None
    for entries in fans.values():
        for entry in entries:
            if entry.current is not None:
                return int(entry.current)
    return None


def collect_snapshot() -> dict:
    cpu_info = get_cpu_info()
    return {
        "hostname": get_hostname(),
        "os_version": get_windows_version(),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "cpu_cores": cpu_info["cpu_cores"],
        "cpu_threads": cpu_info["cpu_threads"],
        "cpu_max_mhz": cpu_info["cpu_max_mhz"],
        "ram_total_mb": get_ram_total_mb(),
        "gpu_info": get_gpu_info(),
        "motherboard_vendor": get_motherboard_vendor(),
        "bios_vendor": get_bios_vendor(),
        "disks": get_disks(),
        "network_adapters": get_network_adapters(),
        "uptime_seconds": get_uptime_seconds(),
        "cpu_temperature_c": get_cpu_temperature(),
        "fan_speed_rpm": get_fan_speed(),
    }
