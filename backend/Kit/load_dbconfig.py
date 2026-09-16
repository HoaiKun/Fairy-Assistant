import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "dbconfig.json"

def get_db_config()->dict:
  if not CONFIG_PATH.exists():
    raise FileNotFoundError("NO DBCONFIG FOUND")

  with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
  return data.get("database", {})