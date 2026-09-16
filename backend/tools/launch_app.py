import difflib
import json
import os
import winreg
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

BUILTIN_ALIASES = {
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "cmd": "Command Prompt",
    "terminal": "Windows Terminal",
    "ps": "PowerShell",
    "powershell": "Windows PowerShell",
    "calc": "Calculator",
    "calculator": "Calculator",
    "notepad": "Notepad",
    "ue5": "Unreal Editor",
    "unreal": "Unreal Editor",
    "chrome": "Google Chrome",
    "edge": "Microsoft Edge",
    "task manager": "Task Manager",
}

# Khởi tạo Windows Script Host Shell qua Win32 COM
_shell = win32com.client.Dispatch("WScript.Shell")


def _get_shortcut_target_exe(lnk_path: str) -> str:
    """Use Win32 COM to read the contents of a .lnk file and retrieve the actual path to the .exe file."""
    try:
        shortcut = _shell.CreateShortCut(lnk_path)
        target = shortcut.TargetPath
        if target and target.lower().endswith(".exe") and os.path.exists(target):
            return target
    except Exception:
        pass
    return ""


def _index_start_menu_shortcuts() -> dict:
    """
   Recursively scan the Start Menu directory:
    - Skip junk files (uninstall, docs).
    - Map both display names (.lnk) and executable filenames (.exe) extracted via Win32.
    """
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

                # Bỏ qua shortcut phụ / gỡ cài đặt
                if any(bad_word in lower_name for bad_word in IGNORE_KEYWORDS):
                    continue

                full_lnk_path = os.path.join(root, file)
                parent_folder = os.path.basename(root).strip().lower()

                # 1. Map tên file shortcut hiển thị (vd: 'maya 2026')
                if lower_name not in shortcuts:
                    shortcuts[lower_name] = full_lnk_path

                # 2. Map tên folder cha (nếu nằm trong folder riêng của phần mềm)
                if parent_folder and parent_folder != "programs" and parent_folder not in shortcuts:
                    shortcuts[parent_folder] = full_lnk_path

                # 3. DÙNG WIN32: Trích xuất tên file .exe thật bên trong shortcut
                target_exe = _get_shortcut_target_exe(full_lnk_path)
                if target_exe:
                    exe_name = os.path.splitext(os.path.basename(target_exe))[0].strip().lower()
                    if exe_name and exe_name not in shortcuts:
                        shortcuts[exe_name] = full_lnk_path

    return shortcuts


def _check_app_paths_registry(app_query: str) -> str | None:
    """Look up Windows App Paths via the Registry."""
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


def launch_application(app_name: str) -> str:
    """Launch the application using a four-tier optimization check."""
    query = app_name.strip()
    query_lower = query.lower()

    # 0. Ánh xạ alias phổ biến
    if query_lower in BUILTIN_ALIASES:
        query_lower = BUILTIN_ALIASES[query_lower].lower()

    # TẦNG 1: Tra cứu trực tiếp từ Database PostgreSQL của app_tracker
    try:
        cached_exe = app_tracker.find_app_path(query)
        if cached_exe and os.path.exists(cached_exe):
            os.startfile(cached_exe)
            return json.dumps({
                "status": "success",
                "source": "database_history",
                "matched_path": cached_exe,
                "message": f"Successfully launched '{os.path.basename(cached_exe)}' from usage history."
            }, ensure_ascii=False)
    except Exception:
        pass

    # TẦNG 2: Tra cứu Windows App Paths Registry
    reg_path = _check_app_paths_registry(query_lower)
    if reg_path:
        try:
            os.startfile(reg_path)
            return json.dumps({
                "status": "success",
                "source": "windows_app_paths",
                "matched_path": reg_path,
                "message": f"Successfully launched '{query}' via Registry."
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

    # TẦNG 3: Quét Start Menu Shortcuts (kết hợp Win32 COM Target Resolution)
    shortcuts = _index_start_menu_shortcuts()
    all_shortcut_names = list(shortcuts.keys())

    target_path = shortcuts.get(query_lower)
    matched_label = query_lower

    # So khớp substring nếu không khớp 100%
    if not target_path:
        for name in all_shortcut_names:
            if query_lower in name:
                target_path = shortcuts[name]
                matched_label = name
                break

    # So khớp mờ (Fuzzy matching)
    if not target_path:
        fuzzy_matches = difflib.get_close_matches(query_lower, all_shortcut_names, n=1, cutoff=0.5)
        if fuzzy_matches:
            matched_label = fuzzy_matches[0]
            target_path = shortcuts[matched_label]

    if target_path and os.path.exists(target_path):
        try:
            os.startfile(target_path)
            return json.dumps({
                "status": "success",
                "source": "start_menu_shortcut",
                "matched_label": matched_label,
                "message": f"Successfully launched '{matched_label}' via Start Menu shortcut."
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

    # TẦNG 4: Fallback thực thi lệnh hệ thống trực tiếp (calc, notepad, explorer...)
    try:
        os.startfile(query_lower)
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