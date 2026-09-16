import subprocess
import json
import re

# Các mẫu lệnh nguy hiểm tuyệt đối không cho phép Fairy tự ý thực thi
DANGEROUS_PATTERNS = [
    r"^format\s+[a-zA-Z]:", 
    r"\bdel\s+.*[/\\]\*.*",  
    r"\brmdir\s+.*[/\\][sS].*", 
    r"\bRemove-Item\s+.*-Recurse\b",  
    r"\bdiskpart\b",
    r"\breg\s+delete\b",
    r"[/\\]Windows[/\\]System32",
    r"\b(shutdown|restart-computer)\b",
]

def execute_terminal_command(
    command: str, working_dir: str = None, timeout: int = 15
) -> str:
  cmd_clean = command.strip()

  # SỬA TẠI ĐÂY: Ép chuỗi rỗng về None để không làm crash subprocess
  actual_cwd = working_dir.strip() if working_dir and working_dir.strip() else None

  # Quét bảo mật...
  for pattern in DANGEROUS_PATTERNS:
    if re.search(pattern, cmd_clean, re.IGNORECASE):
      return json.dumps({
          "status": "blocked",
          "message": (
              f"Security Alert: Command '{cmd_clean}' matches dangerous pattern"
              " and was blocked."
          ),
      })

  try:
    process = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd_clean],
        cwd=actual_cwd,  # Dùng actual_cwd thay vì working_dir
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )

    stdout = process.stdout.strip()
    stderr = process.stderr.strip()

    return json.dumps({
      "status": "success" if process.returncode == 0 else "failed",
      "returncode": process.returncode,
      "stdout": stdout,
      "stderr": stderr,
    })

  except subprocess.TimeoutExpired:
    return json.dumps({
        "status": "timeout",
        "message": f"Command timed out after {timeout} seconds.",
    })
  except Exception as e:
    return json.dumps({"status": "error", "message": str(e)})