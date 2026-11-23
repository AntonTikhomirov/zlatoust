"""Настоящее окно приложения (WebView2 через pywebview), без браузера.

Порядок: окно сразу показывает заставку «Запускаю…», ядро стартует в этом же процессе,
и только когда оно ответило, окно переходит на интерфейс. Закрыли окно — процесс завершается.
"""
from __future__ import annotations

import html
import logging
import sys
import threading
import time
from pathlib import Path

from .paths import data_dir, log_path

log = logging.getLogger("zlatoust")
ICON = Path(__file__).resolve().parents[2] / "assets" / "icon.ico"

SPLASH = """<!doctype html><html lang=ru><meta charset=utf-8>
<style>
html,body{margin:0;height:100%;font-family:'Segoe UI Variable Text','Segoe UI',sans-serif;background:#f6f4ef;color:#1d1b18}
@media (prefers-color-scheme:dark){html,body{background:#141311;color:#f1ede5}}
.c{height:100%;display:grid;place-items:center;text-align:center}
.r{width:36px;height:36px;border-radius:50%;border:4px solid #c8962e;border-top-color:transparent;margin:18px auto 0;animation:s .9s linear infinite}
@keyframes s{to{transform:rotate(360deg)}}
h1{font-size:28px;margin:0 0 6px;font-weight:650}p{margin:0;opacity:.7}
</style><div class=c><div><h1>Златоуст</h1><p>Запускаю…</p><div class=r></div></div></div>"""


def _error_html(msg: str) -> str:
    try:
        tail = "".join(log_path().read_text(encoding="utf-8", errors="replace").splitlines(True)[-30:])
    except OSError:
        tail = ""
    return (
        "<!doctype html><meta charset=utf-8><body style=\"font-family:'Segoe UI',sans-serif;max-width:760px;"
        "margin:40px auto;padding:0 16px\"><h1>Златоуст не запустился</h1>"
        f"<p>{html.escape(msg)}</p><p>Закройте окно и запустите приложение ещё раз. Если не поможет, "
        f"пришлите этот текст.</p><p style='opacity:.7'>Журнал: {html.escape(str(log_path()))}</p>"
        f"<pre style='white-space:pre-wrap;background:#f3f1ec;padding:12px;font-size:12px'>{html.escape(tail)}</pre>"
    )


def _allow_media(window, origin: str) -> None:
    """Разрешаем камеру и микрофон своему же интерфейсу без лишнего вопроса. Не вышло — WebView2 спросит сам."""
    try:
        from Microsoft.Web.WebView2.Core import CoreWebView2PermissionState  # type: ignore

        core = window.native.browser.web_view.CoreWebView2

        def on_perm(_sender, args):
            if str(args.Uri).startswith(origin):
                args.State = CoreWebView2PermissionState.Allow

        core.PermissionRequested += on_perm
        log.info("Доступ к камере и микрофону для интерфейса разрешён")
    except Exception as e:  # noqa: BLE001
        log.warning("Не удалось настроить разрешения WebView2: %s", e)


def _set_icon(window) -> None:
    """WinForms разрешает менять форму только из её UI-потока, поэтому идём через Invoke."""
    try:
        import System  # type: ignore
        import System.Drawing  # type: ignore

        form = window.native
        icon = System.Drawing.Icon(str(ICON))

        def apply() -> None:
            form.Icon = icon

        if form.InvokeRequired:
            form.Invoke(System.Action(apply))
        else:
            apply()
        log.info("Иконка окна установлена")
    except Exception as e:  # noqa: BLE001
        log.warning("Не удалось поставить иконку окна: %s", e)


def run(start_server, url: str, already_running: bool) -> None:
    """start_server() -> (ok: bool, сообщение, ожидание_анализа: callable)."""
    import webview

    if sys.platform == "win32":
        try:
            import ctypes

            # Своя группа на панели задач и иконка ярлыка, а не Python.
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Zlatoust.App")
        except Exception:
            pass

    window = webview.create_window(
        "Златоуст", html=SPLASH, width=1280, height=860, min_size=(900, 640), background_color="#f6f4ef",
        text_select=True,
    )
    state: dict = {}

    window.events.shown += lambda: _set_icon(window)

    def boot() -> None:
        if already_running:
            ok, msg = True, ""
        else:
            ok, msg, state["drain"] = start_server()
        if ok:
            _allow_media(window, url.rstrip("/"))
            window.load_url(url)
        else:
            window.load_html(_error_html(msg))

    webview.start(boot, private_mode=False, storage_path=str(data_dir() / "webview"), gui="edgechromium" if sys.platform == "win32" else None)
    # Окно закрыто. Если идёт анализ — даём ему закончиться, иначе выходим.
    drain = state.get("drain")
    if drain:
        drain()
