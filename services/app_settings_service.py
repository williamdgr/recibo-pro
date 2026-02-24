import json
from pathlib import Path

from PIL import Image

from database.connection import get_db_path


def _app_root_dir():
    db_path = get_db_path()
    return db_path.parent.parent


def _logo_dir():
    folder = _app_root_dir() / "logo"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _config_dir():
    folder = _app_root_dir() / "config"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _settings_file():
    return _config_dir() / "settings.json"


def _read_settings():
    path = _settings_file()
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_settings(data):
    path = _settings_file()
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_logo_storage_path():
    return _logo_dir() / "logo.png"


def save_logo_file(source_path):
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError("Arquivo de logo não encontrado.")
    allowed_extensions = {".png", ".jpg", ".jpeg"}
    if source.suffix.lower() not in allowed_extensions:
        raise ValueError("A logo deve estar no formato .png, .jpg ou .jpeg")

    target = get_logo_storage_path()

    with Image.open(source) as image:
        image.save(target, format="PNG")

    return str(target)


def get_saved_logo_path():
    target = get_logo_storage_path()
    if target.exists():
        return str(target)
    return ""


def set_saved_logo_path(path):
    if not path:
        target = get_logo_storage_path()
        if target.exists():
            target.unlink()
        return

    save_logo_file(path)


def get_saved_city():
    return str(_read_settings().get("default_city") or "")


def set_saved_city(city):
    clean_city = " ".join(str(city or "").strip().split())
    data = _read_settings()

    if clean_city:
        data["default_city"] = clean_city
    else:
        data.pop("default_city", None)

    _write_settings(data)
