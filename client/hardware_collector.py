import ipaddress
import json
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


def _to_float(value) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip().replace(",", ".")
            if not value:
                return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> int | None:
    parsed = _to_float(value)
    if parsed is None:
        return None
    return int(round(parsed))


def _temperature_from_milli_celsius(raw_value: float | None) -> float | None:
    if raw_value is None:
        return None
    if raw_value > 200:  # e.g. 42000 millidegrees
        return round(raw_value / 1000, 2)
    return round(raw_value, 2)


def _temperature_from_tenths_kelvin(raw_value: float | None) -> float | None:
    if raw_value is None:
        return None
    celsius = (raw_value / 10.0) - 273.15
    if -40 <= celsius <= 160:
        return round(celsius, 2)
    return None


def _valid_temperature_values(values: list[float | None]) -> list[float]:
    return [round(value, 2) for value in values if value is not None and -40 <= value <= 160]


def _extract_temperatures_from_sensor_json(data) -> list[float]:
    temps: list[float] = []
    if isinstance(data, dict):
        for key, value in data.items():
            lower_key = str(key).lower()
            if lower_key.endswith("_input") and "temp" in lower_key:
                parsed = _to_float(value)
                if parsed is not None:
                    if parsed > 200:
                        parsed = parsed / 1000
                    temps.append(parsed)
            else:
                temps.extend(_extract_temperatures_from_sensor_json(value))
    elif isinstance(data, list):
        for item in data:
            temps.extend(_extract_temperatures_from_sensor_json(item))
    return _valid_temperature_values(temps)


def _extract_fans_from_sensor_json(data) -> list[int]:
    fans: list[int] = []
    if isinstance(data, dict):
        for key, value in data.items():
            lower_key = str(key).lower()
            if lower_key.endswith("_input") and "fan" in lower_key:
                parsed = _to_int(value)
                if parsed is not None and parsed > 0:
                    fans.append(parsed)
            else:
                fans.extend(_extract_fans_from_sensor_json(value))
    elif isinstance(data, list):
        for item in data:
            fans.extend(_extract_fans_from_sensor_json(item))
    return fans


def _linux_cpu_temperature_from_sysfs() -> float | None:
    candidates: list[float] = []

    # Thermal zones expose various sensors, often CPU package values.
    thermal_root = Path("/sys/class/thermal")
    for zone in thermal_root.glob("thermal_zone*"):
        temp_path = zone / "temp"
        type_path = zone / "type"
        temp_raw = _to_float(_read_text_file(temp_path))
        temp_value = _temperature_from_milli_celsius(temp_raw)
        if temp_value is None:
            continue
        zone_type = (_read_text_file(type_path) or "").lower()
        if any(
            marker in zone_type
            for marker in ("cpu", "x86_pkg_temp", "package", "core", "tctl", "k10temp", "soc")
        ):
            candidates.append(temp_value)

    hwmon_root = Path("/sys/class/hwmon")
    fallback_candidates: list[float] = []
    for hwmon in hwmon_root.glob("hwmon*"):
        chip_name = (_read_text_file(hwmon / "name") or "").lower()
        for temp_input in hwmon.glob("temp*_input"):
            temp_raw = _to_float(_read_text_file(temp_input))
            temp_value = _temperature_from_milli_celsius(temp_raw)
            if temp_value is None:
                continue
            label_path = temp_input.with_name(temp_input.name.replace("_input", "_label"))
            label = (_read_text_file(label_path) or "").lower()
            if any(
                marker in f"{chip_name} {label}"
                for marker in ("cpu", "package", "core", "tctl", "k10temp", "soc")
            ):
                candidates.append(temp_value)
            else:
                fallback_candidates.append(temp_value)

    all_values = _valid_temperature_values(candidates or fallback_candidates)
    if all_values:
        return max(all_values)
    return None


def _linux_fan_speed_from_sysfs() -> int | None:
    speeds: list[int] = []
    for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
        for fan_input in hwmon.glob("fan*_input"):
            value = _to_int(_read_text_file(fan_input))
            if value is not None and value > 0:
                speeds.append(value)
    if speeds:
        return max(speeds)
    return None


def _windows_open_hardware_sensor_values(sensor_type: str) -> tuple[list[float], str | None]:
    values: list[float] = []
    source: str | None = None
    for namespace in ("root/OpenHardwareMonitor", "root/LibreHardwareMonitor"):
        raw = _run_powershell(
            (
                f"Get-CimInstance -Namespace '{namespace}' -ClassName Sensor "
                f"| Where-Object {{$_.SensorType -eq '{sensor_type}'}} "
                "| Select-Object Name,Value | ConvertTo-Json -Compress"
            )
        )
        for record in _parse_json_output(raw):
            value = _to_float(record.get("Value"))
            if value is not None:
                values.append(value)
        if values:
            source = f"windows-open-hardware:{namespace}"
            return values, source
    return values, source


def _windows_cpu_temperature_fallback() -> tuple[float | None, str | None]:
    # ACPI values are typically in tenth Kelvin.
    acpi_output = _run_powershell(
        "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
        "| Select-Object CurrentTemperature | ConvertTo-Json -Compress"
    )
    acpi_values = [
        _temperature_from_tenths_kelvin(_to_float(record.get("CurrentTemperature")))
        for record in _parse_json_output(acpi_output)
    ]
    valid_acpi = _valid_temperature_values(acpi_values)
    if valid_acpi:
        return max(valid_acpi), "windows-wmi-acpi"

    ohm_values, ohm_source = _windows_open_hardware_sensor_values("Temperature")
    valid_ohm = _valid_temperature_values([_to_float(value) for value in ohm_values])
    if valid_ohm:
        return max(valid_ohm), ohm_source

    return None, None


def _windows_fan_speed_fallback() -> tuple[int | None, str | None]:
    speeds: list[int] = []

    wmi_output = _run_powershell(
        "Get-CimInstance Win32_Fan | Select-Object DesiredSpeed,VariableSpeed | ConvertTo-Json -Compress"
    )
    for record in _parse_json_output(wmi_output):
        desired = _to_int(record.get("DesiredSpeed"))
        if desired is not None and desired > 0:
            speeds.append(desired)

    if speeds:
        return max(speeds), "windows-wmi-win32_fan"

    ohm_values, ohm_source = _windows_open_hardware_sensor_values("Fan")
    ohm_speeds = [_to_int(value) for value in ohm_values]
    valid = [value for value in ohm_speeds if value is not None and value > 0]
    if valid:
        return max(valid), ohm_source

    return None, None


def get_cpu_temperature_with_source() -> tuple[float | None, str | None]:
    try:
        temperatures = psutil.sensors_temperatures()
    except (AttributeError, OSError):
        temperatures = {}
    for entries in temperatures.values():
        for entry in entries:
            if entry.current is not None:
                current = _to_float(entry.current)
                if current is not None:
                    return round(current, 2), "psutil-sensors_temperatures"

    if platform.system().lower() == "windows":
        return _windows_cpu_temperature_fallback()

    sensors_output = _run_command(["sensors", "-j"])
    if sensors_output:
        try:
            parsed = json.loads(sensors_output)
        except json.JSONDecodeError:
            parsed = None
        sensor_temps = _extract_temperatures_from_sensor_json(parsed)
        if sensor_temps:
            return max(sensor_temps), "linux-lm-sensors"

    sysfs_temp = _linux_cpu_temperature_from_sysfs()
    if sysfs_temp is not None:
        return sysfs_temp, "linux-sysfs"
    return None, None


def get_fan_speed_with_source() -> tuple[int | None, str | None]:
    try:
        fans = psutil.sensors_fans()
    except (AttributeError, OSError):
        fans = {}
    for entries in fans.values():
        for entry in entries:
            if entry.current is not None:
                current = _to_int(entry.current)
                if current is not None and current > 0:
                    return current, "psutil-sensors_fans"

    if platform.system().lower() == "windows":
        return _windows_fan_speed_fallback()

    sensors_output = _run_command(["sensors", "-j"])
    if sensors_output:
        try:
            parsed = json.loads(sensors_output)
        except json.JSONDecodeError:
            parsed = None
        fan_values = _extract_fans_from_sensor_json(parsed)
        if fan_values:
            return max(fan_values), "linux-lm-sensors"

    sysfs_fan = _linux_fan_speed_from_sysfs()
    if sysfs_fan is not None:
        return sysfs_fan, "linux-sysfs"
    return None, None


def get_cpu_temperature() -> float | None:
    value, _ = get_cpu_temperature_with_source()
    return value


def get_fan_speed() -> int | None:
    value, _ = get_fan_speed_with_source()
    return value


def collect_snapshot() -> dict:
    cpu_info = get_cpu_info()
    cpu_temperature_c, cpu_temperature_source = get_cpu_temperature_with_source()
    fan_speed_rpm, fan_speed_source = get_fan_speed_with_source()
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
        "cpu_temperature_c": cpu_temperature_c,
        "cpu_temperature_source": cpu_temperature_source,
        "fan_speed_rpm": fan_speed_rpm,
        "fan_speed_source": fan_speed_source,
    }
