"""Где приложение хранит данные. Всё локально, в одной папке пользователя."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def data_dir() -> Path:
    override = os.environ.get("ZLATOUST_DATA")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Zlatoust"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "zlatoust"
    base.mkdir(parents=True, exist_ok=True)
    return base


def recordings_dir() -> Path:
    p = data_dir() / "recordings"
    p.mkdir(parents=True, exist_ok=True)
    return p


def models_dir() -> Path:
    p = data_dir() / "models"
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return data_dir() / "zlatoust.sqlite3"


def settings_path() -> Path:
    return data_dir() / "settings.json"


def log_path() -> Path:
    return data_dir() / "zlatoust.log"


def frontend_dist() -> Path:
    # backend/zlatoust/paths.py -> repo root / frontend / dist
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"
