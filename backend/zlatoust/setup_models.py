"""Скачивает модели заранее, чтобы первый анализ не ждал загрузки. Запускается из setup.ps1."""
from __future__ import annotations

import sys

from .analysis.transcribe import _add_cuda_dll_dirs, cuda_available
from .analysis.video import ensure_models
from .paths import models_dir


def main() -> None:
    print("Модели для видео (MediaPipe)…", flush=True)
    ensure_models()
    _add_cuda_dll_dirs()
    gpu = cuda_available()
    print(f"Видеокарта с CUDA: {'да' if gpu else 'нет, будет процессор'}", flush=True)
    from faster_whisper.utils import download_model

    names = ["large-v3", "small"] if gpu else ["small"]
    for n in names:
        print(f"Модель распознавания речи {n}…", flush=True)
        download_model(n, cache_dir=str(models_dir() / "whisper"))
    if gpu:
        print("Проверяю запуск на видеокарте…", flush=True)
        from .analysis.transcribe import Transcriber

        t = Transcriber("auto")
        t._load()
        print(f"Распознавание будет работать на: {t.device}", flush=True)
    print("Готово.", flush=True)


if __name__ == "__main__":
    sys.exit(main())
