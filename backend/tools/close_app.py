import difflib
import json
import psutil

# Danh sách alias map tên gọi thường ngày sang tên process (.exe)
CLOSE_ALIASES = {
    "vscode": "code.exe",
    "vs code": "code.exe",
    "code": "code.exe",
    "cmd": "cmd.exe",
    "terminal": "windowsterminal.exe",
    "ps": "powershell.exe",
    "powershell": "powershell.exe",
    "calc": "calculatorapp.exe",
    "calculator": "calculatorapp.exe",
    "notepad": "notepad.exe",
    "ue5": "unrealeditor.exe",
    "unreal": "unrealeditor.exe",
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "task manager": "taskmgr.exe",
}


def close_application(app_name: str, force: bool = False) -> str:
    query = app_name.strip().lower()
    if not query:
        return json.dumps({"status": "error", "message": "App name cannot be empty."}, ensure_ascii=False)

    target_exe = CLOSE_ALIASES.get(query, query)
    if not target_exe.endswith(".exe"):
        target_name_no_ext = target_exe
        target_exe_with_ext = f"{target_exe}.exe"
    else:
        target_name_no_ext = target_exe[:-4]
        target_exe_with_ext = target_exe

    # Thu thập tất cả process đang chạy để đối soát
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

    # 1. Khớp chính xác (exact match)
    matched_pids = [
        p for p, name in active_procs 
        if name in (target_name_no_ext, target_exe_with_ext)
    ]
    matched_name = target_exe_with_ext if matched_pids else None

    # 2. Khớp chuỗi con (substring match) nếu chưa thấy
    if not matched_pids:
        for p, name in active_procs:
            if target_name_no_ext in name:
                matched_pids.append(p)
                if not matched_name:
                    matched_name = name

    # 3. Fuzzy match nếu vẫn không tìm ra
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

    # Đóng tất cả process liên quan (bao gồm cả đa tiến trình như Chrome, VS Code)
    killed_count = 0
    errors = []

    for proc in matched_pids:
        try:
            if force:
                proc.kill()
            else:
                proc.terminate()
            killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            errors.append(str(e))

    return json.dumps({
        "status": "success",
        "matched_process": matched_name,
        "instances_closed": killed_count,
        "forced": force,
        "message": f"Successfully closed {killed_count} instance(s) of '{matched_name}'."
    }, ensure_ascii=False)