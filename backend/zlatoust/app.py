"""HTTP-сервер на 127.0.0.1 и запуск окна приложения."""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db, settings
from .analysis.transcribe import cuda_available
from .exercises import EXERCISES, SKILL_TITLES
from .paths import data_dir, frontend_dist, log_path, recordings_dir

log = logging.getLogger("zlatoust")
HOST = "127.0.0.1"
PORT = int(os.environ.get("ZLATOUST_PORT", "8765"))

_last_ping = time.monotonic()


class SettingsIn(BaseModel):
    llm_provider: settings.LlmProvider | None = None
    anthropic_api_key: str | None = None  # пустая строка = удалить ключ, None = не менять
    anthropic_model: str | None = None
    ollama_url: str | None = None
    ollama_model: str | None = None
    whisper_model: str | None = None
    record_seconds: int | None = None


def create_app(start_worker: bool = True) -> FastAPI:
    from .pipeline import Worker

    db.init()
    worker = Worker()
    if start_worker:
        worker.start()
    app = FastAPI(title="Златоуст", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.worker = worker

    @app.get("/api/health")
    def health():
        global _last_ping
        _last_ping = time.monotonic()
        from .analysis.video import models_ready

        s = settings.load()
        return {"ok": True, "gpu": cuda_available(), "video_models": models_ready(), "llm": s.llm_provider, "data_dir": str(data_dir())}

    @app.get("/api/exercises")
    def exercises():
        return {"exercises": EXERCISES, "skills": SKILL_TITLES}

    @app.post("/api/sessions")
    async def create_session(
        file: UploadFile = File(...),
        mode: str = Form("free"),
        exercise_id: str | None = Form(None),
        title: str | None = Form(None),
        reference_text: str | None = Form(None),
    ):
        if mode not in ("free", "topic", "reading", "tongue_twister"):
            raise HTTPException(400, "Неизвестный режим")
        ext = ".mp4" if (file.content_type or "").startswith("video/mp4") else ".webm"
        name = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}{ext}"
        dest = recordings_dir() / name
        with dest.open("wb") as f:
            while chunk := await file.read(1 << 20):
                f.write(chunk)
        if dest.stat().st_size < 1000:
            dest.unlink(missing_ok=True)
            raise HTTPException(400, "Запись пустая. Проверьте камеру и микрофон.")
        sid = db.create(mode, name, exercise_id or None, title or None, (reference_text or "").strip() or None)
        app.state.worker.submit(sid)
        return {"id": sid}

    @app.get("/api/sessions")
    def list_sessions():
        return {"sessions": db.list_all()}

    @app.get("/api/sessions/{sid}")
    def get_session(sid: str):
        s = db.get(sid)
        if not s:
            raise HTTPException(404, "Запись не найдена")
        return s

    @app.post("/api/sessions/{sid}/retry")
    def retry(sid: str):
        s = db.get(sid)
        if not s:
            raise HTTPException(404, "Запись не найдена")
        db.update(sid, status="queued", error=None, progress=0, stage=None)
        app.state.worker.submit(sid)
        return {"ok": True}

    @app.get("/api/sessions/{sid}/video")
    def video(sid: str):
        s = db.get(sid)
        if not s:
            raise HTTPException(404, "Запись не найдена")
        p = recordings_dir() / s["video_file"]
        return FileResponse(p, media_type="video/mp4" if p.suffix == ".mp4" else "video/webm")

    @app.delete("/api/sessions/{sid}")
    def delete(sid: str):
        s = db.delete(sid)
        if s:
            (recordings_dir() / s["video_file"]).unlink(missing_ok=True)
        return {"ok": True}

    @app.get("/api/settings")
    def get_settings():
        return settings.public_view(settings.load())

    @app.put("/api/settings")
    def put_settings(body: SettingsIn):
        cur = settings.load()
        upd = {k: v for k, v in body.model_dump().items() if v is not None}
        if "anthropic_api_key" in upd:
            upd["anthropic_api_key"] = upd["anthropic_api_key"].strip()
        new = cur.model_copy(update=upd)
        settings.Settings.model_validate(new.model_dump())
        settings.save(new)
        return settings.public_view(new)

    @app.post("/api/settings/test-llm")
    def test_llm():
        from .llm import test_connection

        try:
            return {"ok": True, "message": test_connection(settings.load())}
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "authentication" in msg.lower() or "401" in msg:
                msg = "Ключ API не подошёл. Проверьте, что скопировали его целиком."
            elif "connect" in msg.lower():
                msg = "Нет соединения. Для Ollama проверьте, что она запущена."
            return JSONResponse({"ok": False, "message": msg[:300]}, status_code=200)

    @app.post("/api/shutdown")
    def shutdown():
        threading.Timer(0.3, lambda: os._exit(0)).start()
        return {"ok": True}

    dist = frontend_dist()
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            f = dist / path
            if path and f.is_file() and dist in f.resolve().parents:
                return FileResponse(f)
            return FileResponse(dist / "index.html")

    return app


def _setup_logging() -> None:
    h = RotatingFileHandler(log_path(), maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(h)
    if sys.stderr is not None:
        root.addHandler(logging.StreamHandler())


def _server_running() -> bool:
    import httpx

    try:
        return httpx.get(f"http://{HOST}:{PORT}/api/health", timeout=1).json().get("ok") is True
    except Exception:
        return False


def _find_edge() -> str | None:
    cands = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        shutil.which("msedge") or "",
        shutil.which("chromium") or "",
        shutil.which("google-chrome") or "",
    ]
    return next((c for c in cands if c and Path(c).exists()), None)


def _open_window(url: str) -> subprocess.Popen | None:
    """Отдельное окно без адресной строки, со своим профилем (разрешение на камеру запоминается)."""
    exe = _find_edge()
    if not exe:
        webbrowser.open(url)
        return None
    profile = data_dir() / "window-profile"
    return subprocess.Popen([
        exe, f"--app={url}", f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
        "--window-size=1280,860", "--disable-features=Translate",
    ])


def main() -> None:
    _setup_logging()
    url = f"http://{HOST}:{PORT}/"
    if "--server" not in sys.argv and _server_running():
        _open_window(url)  # приложение уже запущено — просто ещё одно окно
        return

    import uvicorn

    app = create_app()
    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=PORT, log_level="warning", log_config=None))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    log.info("Златоуст запущен: %s, данные в %s", url, data_dir())

    if "--server" in sys.argv:
        t.join()
        return
    proc = _open_window(url)
    if proc is not None:
        proc.wait()
        # Закрыли окно — закрываемся. Если идёт анализ, даём ему закончиться.
        while not app.state.worker.q.empty() or any(s["status"] == "processing" for s in db.list_all(5)):
            time.sleep(2)
    else:
        # Открыто в обычном браузере: живём, пока вкладка присылает пинги.
        while time.monotonic() - _last_ping < 120:
            time.sleep(5)
    server.should_exit = True
    t.join(timeout=5)


if __name__ == "__main__":
    main()
