import ipaddress
import json
import locale
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
            text=False,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    output = _decode_command_output(completed.stdout).strip()
    return output or None


def _decode_command_output(raw_output: bytes) -> str:
    if not raw_output:
        return ""

    # Some Windows commands emit UTF-16; prefer it when null bytes are prevalent.
    if raw_output.startswith((b"\xff\xfe", b"\xfe\xff")) or raw_output.count(b"\x00") > len(raw_output) // 4:
        for encoding in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                return raw_output.decode(encoding)
            except UnicodeDecodeError:
                continue

    preferred_encoding = locale.getpreferredencoding(False) or "utf-8"
    encoding_candidates = [preferred_encoding, "utf-8", "cp850", "cp1252", "latin-1"]
    seen: set[str] = set()
    for encoding in encoding_candidates:
        normalized = encoding.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        try:
            return raw_output.decode(encoding)
        except UnicodeDecodeError:
            continue

    # Last-resort fallback to avoid crashes in collector threads.
    return raw_output.decode(preferred_encoding, errors="replace")


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
        "system product name",
        "system version",
        "not applicable",
        "n/a",
        "unknown",
        "none",
    }
    if normalized.lower() in placeholder_values:
        return None
    return normalized


def _parse_json_output(raw_output: str | None) -> list[dict]:
    if not raw_output:
        return []
    try:
        decoded = json.loads(raw_output)
    except json.JSONDecodeError:
        return []
    if isinstance(decoded, dict):
        return [decoded]
    if isinstance(decoded, list):
        return [item for item in decoded if isinstance(item, dict)]
    return []


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
        product = _normalize_vendor(_first_data_line(_run_command(["wmic", "baseboard", "get", "Product"]), ("product",)))
        if vendor and product and product.lower() not in vendor.lower():
            return f"{vendor} ({product})"
        if vendor:
            return vendor
        if product:
            return product

        output = _run_powershell(
            "Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product | ConvertTo-Json -Compress"
        )
        records = _parse_json_output(output)
        if records:
            cim_vendor = _normalize_vendor(str(records[0].get("Manufacturer") or ""))
            cim_product = _normalize_vendor(str(records[0].get("Product") or ""))
            if cim_vendor and cim_product and cim_product.lower() not in cim_vendor.lower():
                return f"{cim_vendor} ({cim_product})"
            if cim_vendor:
                return cim_vendor
            if cim_product:
                return cim_product

        output = _run_powershell(
            "Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model | ConvertTo-Json -Compress"
        )
        records = _parse_json_output(output)
        if records:
            vendor = _normalize_vendor(str(records[0].get("Manufacturer") or ""))
            model = _normalize_vendor(str(records[0].get("Model") or ""))
            if vendor and model and model.lower() not in vendor.lower():
                return f"{vendor} ({model})"
            if vendor:
                return vendor
            if model:
                return model
        return None
    return _normalize_vendor(_read_text_file(Path("/sys/devices/virtual/dmi/id/board_vendor")))


def get_bios_vendor() -> str | None:
    if platform.system().lower() == "windows":
        output = _run_command(["wmic", "bios", "get", "Manufacturer"])
        vendor = _normalize_vendor(_first_data_line(output, ignored_keywords=("manufacturer",)))
        version = _normalize_vendor(
            _first_data_line(_run_command(["wmic", "bios", "get", "SMBIOSBIOSVersion"]), ("smbiosbiosversion",))
        )
        if vendor and version and version.lower() not in vendor.lower():
            return f"{vendor} ({version})"
        if vendor:
            return vendor
        if version:
            return version

        output = _run_powershell(
            "Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,Name | ConvertTo-Json -Compress"
        )
        records = _parse_json_output(output)
        if records:
            cim_vendor = _normalize_vendor(str(records[0].get("Manufacturer") or ""))
            cim_version = _normalize_vendor(str(records[0].get("SMBIOSBIOSVersion") or ""))
            cim_name = _normalize_vendor(str(records[0].get("Name") or ""))
            if cim_vendor and cim_version and cim_version.lower() not in cim_vendor.lower():
                return f"{cim_vendor} ({cim_version})"
            if cim_vendor:
                return cim_vendor
            if cim_name:
                return cim_name
            if cim_version:
                return cim_version
        return None
    return _normalize_vendor(_read_text_file(Path("/sys/devices/virtual/dmi/id/bios_vendor")))


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
    if platform.system().lower() == "windows":
        output = _run_powershell(
            "Get-CimInstance Win32_NetworkAdapterConfiguration | "
            "Where-Object {$_.IPEnabled -eq $true} | "
            "Select-Object Description,MACAddress,IPAddress | ConvertTo-Json -Compress"
        )
        records = _parse_json_output(output)
        if records:
            adapters: list[dict] = []
            for record in records:
                raw_ips = record.get("IPAddress") or []
                if isinstance(raw_ips, str):
                    raw_ips = [raw_ips]
                ipv4: list[str] = []
                ipv6: list[str] = []
                for ip in raw_ips:
                    try:
                        parsed = ipaddress.ip_address(ip.split("%")[0])
                    except ValueError:
                        continue
                    if parsed.version == 4:
                        ipv4.append(str(parsed))
                    else:
                        ipv6.append(str(parsed))
                adapters.append(
                    {
                        "name": record.get("Description") or "Adapter",
                        "ipv4": sorted(set(ipv4)),
                        "ipv6": sorted(set(ipv6)),
                        "mac": record.get("MACAddress"),
                    }
                )
            if adapters:
                return adapters

    adapters = []
    all_interfaces = psutil.net_if_addrs()
    mac_families = {getattr(socket, "AF_PACKET", None), getattr(psutil, "AF_LINK", None), -1}
    for name, addresses in all_interfaces.items():
        adapter = {"name": name, "ipv4": [], "ipv6": [], "mac": None}
        for address in addresses:
            try:
                family = int(address.family)
            except (TypeError, ValueError):
                family = None

            if family == int(socket.AF_INET):
                adapter["ipv4"].append(address.address)
            elif family == int(socket.AF_INET6):
                adapter["ipv6"].append(address.address.split("%")[0])
            elif family in mac_families:
                mac = (address.address or "").strip()
                if mac and mac not in {"00:00:00:00:00:00", "00-00-00-00-00-00"}:
                    adapter["mac"] = mac

        adapter["ipv4"] = sorted(set(adapter["ipv4"]))
        adapter["ipv6"] = sorted(set(adapter["ipv6"]))
        if adapter["ipv4"] or adapter["ipv6"] or adapter["mac"]:
            adapters.append(adapter)

    return adapters


def get_uptime_seconds() -> int:
    return int(time.time() - psutil.boot_time())


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
    }
