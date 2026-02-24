import sqlite3
import os
from pathlib import Path

def get_connection():
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def get_db_path():
    local_app_data = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    app_folder = Path(local_app_data) / "ReciboPro"
    db_folder = app_folder / "database"

    db_folder.mkdir(parents=True, exist_ok=True)

    return db_folder / "recibo.db"