from datetime import datetime
import os
import platform
import threading
import time
import psutil
import pygetwindow as gw
from win32 import win32process
import winreg
try:
  import GPUtil
except ImportError:
  GPUtil = None


class SystemTelemtry:

 
  def __init__(self):

    print("INITATING SYSTEM TELEMTRY")
    
    self.static_specs = self._get_static_hardware_info()
    self.lock = threading.Lock()
    self.state = {
        "hardware": {},
        "active_window": "",
        "app_durations": {},
        "system_flags": [],
        "last_active_time": time.time(),
        "is_idle": False,
    }
    self.running = True

  def _get_static_hardware_info(self) -> dict:
    gpu_name = "N/A"
    gpu_vram = 0
    if GPUtil:
      try:
        gpus = GPUtil.getGPUs()
        if gpus:
          gpu_name = gpus[0].name
          gpu_vram = int(gpus[0].memoryTotal)
      except Exception:
        pass

    try:
      build = int(platform.version().split(".")[-1])
    except Exception:
      pass
    try:
      key = winreg.OpenKey(
      winreg.HKEY_LOCAL_MACHINE,
      r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
      )
      cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
      winreg.CloseKey(key)
      cpu_name = cpu_name.strip()
    except Exception:
      pass

    

    ram = psutil.virtual_memory()
    return {
        "os": f"{platform.system()} {platform.release()} build: {build}",
        "cpu": platform.processor() or "Unknown CPU",
        "total_ram_gb": round(ram.total / (1024**3), 1),
        "gpu_name": gpu_name,
        "gpu_vram_mb": gpu_vram,
    }

  def start(self):
    worker = threading.Thread(target=self._monitor_loop, daemon=True)
    worker.start()

  def _get_gpu_metrics(self):
    if not GPUtil:
      return None
    try:
      gpus = GPUtil.getGPUs()
      if gpus:
        gpu = gpus[0]
        return {
            "name": gpu.name,
            "load_percent": round(gpu.load * 100, 1),
            "temp_c": gpu.temperature,
            "vram_used_mb": int(gpu.memoryUsed),
            "vram_total_mb": int(gpu.memoryTotal),
        }
    except Exception:
      pass
    return None

  def _get_battery_metrics(self):
    battery = psutil.sensors_battery()
    if not battery:
      return None
    return {
        "percent": battery.percent,
        "power_plugged": battery.power_plugged,
        "secs_left": (
            battery.secsleft
            if battery.secsleft != psutil.POWER_TIME_UNLIMITED
            else -1
        ),
    }

  def _get_active_process_info(self):
    try:
      win = gw.getActiveWindow()
      if not win or not win.title.strip():
        return {"name": "Desktop", "title": "Desktop"}
      title = win.title.strip()

      _, pid = win32process.GetWindowThreadProcessId(win._hWnd)
      proc = psutil.Process(pid)
      app_name = proc.name()

      return {"name": app_name, "title": title}
    except Exception:
      title = win.title.strip() if (win and win.title) else "Desktop"
      return {"name": title.split(" - ")[-1], "title": title}

  def _monitor_loop(self):
    while self.running:
      cpu_percent = psutil.cpu_percent(interval=1)
      ram = psutil.virtual_memory()
      disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/")
      gpu = self._get_gpu_metrics()
      battery = self._get_battery_metrics()

      focus_info = self._get_active_process_info()
      current_app = focus_info["title"]
      app_process = focus_info["name"]

      flags = []
      if cpu_percent > 85:
        flags.append(f"CPU overloading: {cpu_percent}%")
      if ram.percent > 90:
        flags.append(f"RAM running out: {ram.percent}%")
      if gpu and gpu.get("temp_c") and gpu["temp_c"] > 85:
        flags.append(f"GPU Overheating: {gpu['temp_c']}°C")
      if battery and not battery["power_plugged"] and battery["percent"] < 20:
        flags.append(f"Low battery: {battery['percent']}%")
      if disk.percent > 92:
        flags.append(f"Disk running out: {disk.percent}%")

      with self.lock:
        self.state["hardware"] = {
            "cpu_percent": cpu_percent,
            "ram_percent": ram.percent,
            "ram_used_gb": round((ram.total - ram.available) / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "gpu": gpu,
            "battery": battery,
        }
        self.state["active_window"] = current_app
        self.state["system_flags"] = flags

        if app_process not in ["Desktop", "Taskmgr.exe", ""]:
          self.state["app_durations"][app_process] = (
              self.state["app_durations"].get(app_process, 0) + (2 / 60)
          )

      time.sleep(2)

  def get_live_metrics_summary(self) -> dict:
    """Capture system load snapshots and real-time alerts."""
    with self.lock:
      hw = self.state.get("hardware", {})
      flags = self.state.get("system_flags", [])
      active_window = self.state.get("active_window", "Desktop")

    return {
        "cpu_usage_percent": hw.get("cpu_percent", 0),
        "ram_usage_percent": hw.get("ram_percent", 0),
        "ram_used_gb": hw.get("ram_used_gb", 0),
        "disk_free_gb": hw.get("disk_free_gb", 0),
        "gpu": hw.get("gpu"),
        "battery": hw.get("battery"),
        "critical_alerts": flags,
        "active_window": active_window,
    }

  def get_static_specs_summary(self) -> dict:
      """Retrieve the computer's fixed configuration"""
      return self.static_specs



system_tracker = SystemTelemtry()
system_tracker.start()