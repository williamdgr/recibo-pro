import sys
from pathlib import Path


def is_frozen_app():
    return getattr(sys, "frozen", False)


def get_project_root():
    if is_frozen_app():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_bundle_root():
    if is_frozen_app() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return get_project_root()


def get_asset_path(*parts):
    return get_bundle_root().joinpath("assets", *parts)


def get_app_data_path(*parts):
    return get_project_root().joinpath(*parts)
