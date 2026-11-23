"""SQLite: одна таблица сессий. Метрики и отчёт лежат как JSON — схема ещё будет меняться."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from .paths import db_path

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    exercise_id TEXT,
    title TEXT,
    reference_text TEXT,
    video_file TEXT NOT NULL,
    duration REAL,
    status TEXT NOT NULL,
    stage TEXT,
    progress REAL DEFAULT 0,
    error TEXT,
    metrics_json TEXT,
    report_json TEXT
);
CREATE INDEX IF NOT EXISTS sessions_created ON sessions(created_at DESC);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init() -> None:
    with _lock, _connect() as c:
        c.executescript(SCHEMA)
        # Если приложение закрыли во время анализа — такие записи перезапустим.
        c.execute("UPDATE sessions SET status='queued', stage=NULL, progress=0 WHERE status='processing'")


def create(mode: str, video_file: str, exercise_id: str | None, title: str | None, reference_text: str | None) -> str:
    sid = uuid.uuid4().hex[:12]
    with _lock, _connect() as c:
        c.execute(
            "INSERT INTO sessions(id, created_at, mode, exercise_id, title, reference_text, video_file, status)"
            " VALUES (?,?,?,?,?,?,?, 'queued')",
            (sid, datetime.now(timezone.utc).isoformat(), mode, exercise_id, title, reference_text, video_file),
        )
    return sid


def update(sid: str, **fields: Any) -> None:
    if not fields:
        return
    for k in ("metrics", "report"):
        if k in fields:
            fields[f"{k}_json"] = json.dumps(fields.pop(k), ensure_ascii=False)
    cols = ", ".join(f"{k}=?" for k in fields)
    with _lock, _connect() as c:
        c.execute(f"UPDATE sessions SET {cols} WHERE id=?", (*fields.values(), sid))


def _row(r: sqlite3.Row, full: bool) -> dict:
    d = dict(r)
    m = d.pop("metrics_json")
    rep = d.pop("report_json")
    if full:
        d["metrics"] = json.loads(m) if m else None
        d["report"] = json.loads(rep) if rep else None
    else:
        rep_d = json.loads(rep) if rep else None
        d["overall"] = rep_d.get("overall") if rep_d else None
    return d


def get(sid: str) -> dict | None:
    with _connect() as c:
        r = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    return _row(r, True) if r else None


def list_all(limit: int = 100) -> list[dict]:
    with _connect() as c:
        rows = c.execute("SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_row(r, False) for r in rows]


def queued_ids() -> list[str]:
    with _connect() as c:
        return [r[0] for r in c.execute("SELECT id FROM sessions WHERE status='queued' ORDER BY created_at")]


def delete(sid: str) -> dict | None:
    s = get(sid)
    if s:
        with _lock, _connect() as c:
            c.execute("DELETE FROM sessions WHERE id=?", (sid,))
    return s
