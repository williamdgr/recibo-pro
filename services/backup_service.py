from datetime import datetime
from pathlib import Path
import shutil

from database.connection import get_db_path


def _backup_dir():
    db_path = get_db_path()
    app_root = db_path.parent.parent
    target = app_root / "backup"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _backup_filename(prefix="backup"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.db"


def _list_backup_paths():
    folder = _backup_dir()
    backups = sorted(folder.glob("*.db"), key=lambda item: item.stat().st_mtime, reverse=True)
    return backups


def create_startup_backup(max_files=7):
    db_path = get_db_path()
    if not db_path.exists():
        return None

    destination = _backup_dir() / _backup_filename(prefix="startup")
    shutil.copy2(str(db_path), str(destination))
    _prune_backups(max_files=max_files)
    return str(destination)


def create_manual_backup(max_files=30):
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError("Banco de dados não encontrado para backup.")

    destination = _backup_dir() / _backup_filename(prefix="manual")
    shutil.copy2(str(db_path), str(destination))
    _prune_backups(max_files=max_files)
    return str(destination)


def _prune_backups(max_files):
    backups = _list_backup_paths()
    if max_files <= 0:
        max_files = 1

    for old_backup in backups[max_files:]:
        try:
            old_backup.unlink()
        except Exception:
            pass


def get_latest_backups(limit=20):
    rows = []
    for file_path in _list_backup_paths()[: max(1, int(limit))]:
        stat = file_path.stat()
        rows.append(
            {
                "name": file_path.name,
                "path": str(file_path),
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
            }
        )
    return rows


def restore_backup(backup_path):
    source = Path(backup_path)
    if not source.exists():
        raise FileNotFoundError("Arquivo de backup não encontrado.")

    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(source), str(db_path))
    return str(db_path)
