import difflib
import json
import os
import subprocess
import winreg
import psutil
import win32com.client
from extensions.app_tracking import app_tracker

START_MENU_DIRS = [
    os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
    os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
]

IGNORE_KEYWORDS = [
    "uninstall", "remove", "gỡ cài đặt", "setup", "install", 
    "documentation", "docs", "readme", "help", "manual", 
    "website", "release notes", "changelog", "license"
]

# Từ điển ánh xạ chung cho cả mở và đóng ứng dụng
APP_ALIASES = {
    "vscode": {"display": "Visual Studio Code", "proc": "code.exe"},
    "vs code": {"display": "Visual Studio Code", "proc": "code.exe"},
    "code": {"display": "Visual Studio Code", "proc": "code.exe"},
    "cmd": {"display": "Command Prompt", "proc": "cmd.exe"},
    "terminal": {"display": "Windows Terminal", "proc": "windowsterminal.exe"},
    "ps": {"display": "PowerShell", "proc": "powershell.exe"},
    "powershell": {"display": "Windows PowerShell", "proc": "powershell.exe"},
    "calc": {"display": "Calculator", "proc": "calculatorapp.exe"},
    "calculator": {"display": "Calculator", "proc": "calculatorapp.exe"},
    "notepad": {"display": "Notepad", "proc": "notepad.exe"},
    "ue5": {"display": "Unreal Editor", "proc": "unrealeditor.exe"},
    "unreal": {"display": "Unreal Editor", "proc": "unrealeditor.exe"},
    "chrome": {"display": "Google Chrome", "proc": "chrome.exe"},
    "edge": {"display": "Microsoft Edge", "proc": "msedge.exe"},
    "discord": {"display": "Discord", "proc": "discord.exe"},
    "task manager": {"display": "Task Manager", "proc": "taskmgr.exe"},
}

_shell = win32com.client.Dispatch("WScript.Shell")

# Cờ ngắt liên kết tiến trình Win32, ngăn app con thừa kế console/terminal
DETACHED_FLAGS = (
    subprocess.DETACHED_PROCESS 
    | subprocess.CREATE_NEW_PROCESS_GROUP
)


def _spawn_detached_app(target_path: str):
    """Khởi chạy ứng dụng tách biệt hoàn toàn khỏi terminal console hiện tại."""
    # 1. Nếu là shortcut (.lnk), dùng explorer.exe để Windows Shell tự giải quyết
    if target_path.lower().endswith(".lnk"):
        subprocess.Popen(
            ["explorer.exe", target_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=DETACHED_FLAGS,
            close_fds=True,
        )
    # 2. Nếu là file thực thi .exe
    elif target_path.lower().endswith(".exe") and os.path.exists(target_path):
        work_dir = os.path.dirname(target_path)
        subprocess.Popen(
            [target_path],
            cwd=work_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=DETACHED_FLAGS,
            close_fds=True,
        )
    # 3. Fallback cho lệnh hệ thống (notepad, calc, cmd...)
    else:
        subprocess.Popen(
            f'start "" "{target_path}"',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=DETACHED_FLAGS,
            close_fds=True,
        )


def _get_shortcut_target_exe(lnk_path: str) -> str:
    try:
        shortcut = _shell.CreateShortCut(lnk_path)
        target = shortcut.TargetPath
        if target and target.lower().endswith(".exe") and os.path.exists(target):
            return target
    except Exception:
        pass
    return ""


def _index_start_menu_shortcuts() -> dict:
    shortcuts = {}
    for base_dir in START_MENU_DIRS:
        if not os.path.exists(base_dir):
            continue

        for root, _, files in os.walk(base_dir):
            for file in files:
                if not file.lower().endswith(".lnk"):
                    continue

                name_no_ext = os.path.splitext(file)[0].strip()
                lower_name = name_no_ext.lower()

                if any(bad_word in lower_name for bad_word in IGNORE_KEYWORDS):
                    continue

                full_lnk_path = os.path.join(root, file)
                parent_folder = os.path.basename(root).strip().lower()

                if lower_name not in shortcuts:
                    shortcuts[lower_name] = full_lnk_path

                if parent_folder and parent_folder != "programs" and parent_folder not in shortcuts:
                    shortcuts[parent_folder] = full_lnk_path

                target_exe = _get_shortcut_target_exe(full_lnk_path)
                if target_exe:
                    exe_name = os.path.splitext(os.path.basename(target_exe))[0].strip().lower()
                    if exe_name and exe_name not in shortcuts:
                        shortcuts[exe_name] = full_lnk_path

    return shortcuts


def _check_app_paths_registry(app_query: str) -> str | None:
    reg_roots = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
    sub_key = r"Software\Microsoft\Windows\CurrentVersion\App Paths"
    variants = [app_query, f"{app_query}.exe"]

    for root in reg_roots:
        for variant in variants:
            try:
                full_key_path = f"{sub_key}\\{variant}"
                with winreg.OpenKey(root, full_key_path) as key:
                    path, _ = winreg.QueryValueEx(key, "")
                    if path and os.path.exists(path):
                        return path
            except OSError:
                continue
    return None


def _launch_app(app_name: str) -> str:
    query = app_name.strip()
    query_lower = query.lower()

    if query_lower in APP_ALIASES:
        query_lower = APP_ALIASES[query_lower]["display"].lower()

    # 1. Tra cứu Database PostgreSQL history cache
    try:
        cached_exe = app_tracker.find_app_path(query)
        if cached_exe and os.path.exists(cached_exe):
            _spawn_detached_app(cached_exe)
            return json.dumps({
                "status": "success",
                "source": "database_history",
                "matched_path": cached_exe,
                "message": f"Successfully launched '{os.path.basename(cached_exe)}' from usage history."
            }, ensure_ascii=False)
    except Exception:
        pass

    # 2. Tra cứu Windows App Paths Registry
    reg_path = _check_app_paths_registry(query_lower)
    if reg_path:
        try:
            _spawn_detached_app(reg_path)
            return json.dumps({
                "status": "success",
                "source": "windows_app_paths",
                "matched_path": reg_path,
                "message": f"Successfully launched '{query}' via Registry."
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

    # 3. Start Menu Shortcuts + Win32 COM Resolution
    shortcuts = _index_start_menu_shortcuts()
    all_shortcut_names = list(shortcuts.keys())

    target_path = shortcuts.get(query_lower)
    matched_label = query_lower

    if not target_path:
        for name in all_shortcut_names:
            if query_lower in name:
                target_path = shortcuts[name]
                matched_label = name
                break

    if not target_path:
        fuzzy_matches = difflib.get_close_matches(query_lower, all_shortcut_names, n=1, cutoff=0.5)
        if fuzzy_matches:
            matched_label = fuzzy_matches[0]
            target_path = shortcuts[matched_label]

    if target_path and os.path.exists(target_path):
        try:
            _spawn_detached_app(target_path)
            return json.dumps({
                "status": "success",
                "source": "start_menu_shortcut",
                "matched_label": matched_label,
                "message": f"Successfully launched '{matched_label}' via Start Menu shortcut."
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

    # 4. System command fallback
    try:
        _spawn_detached_app(query_lower)
        return json.dumps({
            "status": "success",
            "source": "system_command",
            "message": f"Successfully executed system command '{query_lower}'."
        }, ensure_ascii=False)
    except Exception:
        pass

    return json.dumps({
        "status": "not_found",
        "message": f"Could not find or launch any application matching '{app_name}'."
    }, ensure_ascii=False)


def _close_app(app_name: str, force: bool = False) -> str:
    query = app_name.strip().lower()
    if not query:
        return json.dumps({"status": "error", "message": "App name cannot be empty."}, ensure_ascii=False)

    if query in APP_ALIASES:
        target_exe = APP_ALIASES[query]["proc"]
    else:
        target_exe = query

    if not target_exe.endswith(".exe"):
        target_name_no_ext = target_exe
        target_exe_with_ext = f"{target_exe}.exe"
    else:
        target_name_no_ext = target_exe[:-4]
        target_exe_with_ext = target_exe

    active_procs = []
    proc_names = set()

    for p in psutil.process_iter(["pid", "name"]):
        try:
            p_name = p.info["name"]
            if p_name:
                active_procs.append((p, p_name.lower()))
                proc_names.add(p_name.lower())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # 1. Exact match
    matched_pids = [
        p for p, name in active_procs 
        if name in (target_name_no_ext, target_exe_with_ext)
    ]
    matched_name = target_exe_with_ext if matched_pids else None

    # 2. Substring match
    if not matched_pids:
        for p, name in active_procs:
            if target_name_no_ext in name:
                matched_pids.append(p)
                if not matched_name:
                    matched_name = name

    # 3. Fuzzy match
    if not matched_pids and proc_names:
        fuzzy_matches = difflib.get_close_matches(target_name_no_ext, list(proc_names), n=1, cutoff=0.6)
        if fuzzy_matches:
            matched_name = fuzzy_matches[0]
            matched_pids = [p for p, name in active_procs if name == matched_name]

    if not matched_pids:
        return json.dumps({
            "status": "not_found",
            "message": f"No running process found matching '{app_name}'."
        }, ensure_ascii=False)

    killed_count = 0
    for proc in matched_pids:
        try:
            if force:
                proc.kill()
            else:
                proc.terminate()
            killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return json.dumps({
        "status": "success",
        "matched_process": matched_name,
        "instances_closed": killed_count,
        "forced": force,
        "message": f"Successfully closed {killed_count} instance(s) of '{matched_name}'."
    }, ensure_ascii=False)


def manage_application(action: str, app_name: str, force: bool = False) -> str:
    """Hàm wrapper điều phối vòng đời ứng dụng: mở hoặc đóng."""
    action_clean = action.lower().strip()
    if action_clean == "launch":
        return _launch_app(app_name=app_name)
    elif action_clean == "close":
        return _close_app(app_name=app_name, force=force)
    
    return json.dumps({
        "status": "error",
        "message": f"Unsupported action '{action}'. Use 'launch' or 'close'."
    }, ensure_ascii=False)