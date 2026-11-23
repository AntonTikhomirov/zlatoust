"""Настройки приложения: локальный JSON-файл. Ключ API хранится только здесь и никогда не уходит в репозиторий."""
from __future__ import annotations

import json
import threading
from typing import Literal

from pydantic import BaseModel, Field

from .paths import settings_path

LlmProvider = Literal["none", "ollama", "anthropic"]


class Settings(BaseModel):
    llm_provider: LlmProvider = "none"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    # "auto": large-v3 на видеокарте, small на процессоре
    whisper_model: str = "auto"
    record_seconds: int = Field(default=60, ge=15, le=600)


_lock = threading.Lock()


def load() -> Settings:
    p = settings_path()
    if not p.exists():
        return Settings()
    try:
        return Settings.model_validate_json(p.read_text(encoding="utf-8"))
    except Exception:
        # Испорченный файл не должен ронять приложение: начинаем с умолчаний, старый сохраняем рядом.
        p.replace(p.with_suffix(".broken.json"))
        return Settings()


def save(s: Settings) -> None:
    with _lock:
        p = settings_path()
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(s.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)


def public_view(s: Settings) -> dict:
    d = s.model_dump()
    key = d.pop("anthropic_api_key")
    d["anthropic_key_set"] = bool(key)
    d["anthropic_key_hint"] = f"…{key[-4:]}" if len(key) >= 8 else ""
    return d
