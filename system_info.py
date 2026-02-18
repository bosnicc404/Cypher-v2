import psutil
import platform
import datetime

def get_system_summary():
    """Return a short, human‑readable summary of the current system status.
    Includes CPU load, memory usage, disk usage, and uptime.
    """
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else 0
    # Memory
    virtual_mem = psutil.virtual_memory()
    mem_used_gb = virtual_mem.used / (1024 ** 3)
    mem_total_gb = virtual_mem.total / (1024 ** 3)
    mem_percent = virtual_mem.percent
    # Disk (root partition)
    disk = psutil.disk_usage('/')
    disk_used_gb = disk.used / (1024 ** 3)
    disk_total_gb = disk.total / (1024 ** 3)
    disk_percent = disk.percent
    # Uptime
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.datetime.now() - boot_time
    # OS info
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"

    summary = (
        f"🖥️ {os_info} | Uptime: {str(uptime).split('.')[0]}\n"
        f"⚡ CPU: {cpu_percent}% @ {cpu_freq:.0f}MHz\n"
        f"💾 RAM: {mem_used_gb:.1f}/{mem_total_gb:.1f}GB ({mem_percent}%)\n"
        f"📁 Disk: {disk_used_gb:.1f}/{disk_total_gb:.1f}GB ({disk_percent}%)"
    )
    return summary
