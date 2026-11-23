"""Распознавание речи faster-whisper с пословными метками времени.

Сначала пробуем видеокарту (CUDA), при любой ошибке — процессор. Приложение не должно падать
из-за драйверов: худший случай — анализ идёт медленнее.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..paths import models_dir

log = logging.getLogger(__name__)

# Подсказка, чтобы Whisper не «вычищал» слова-паразиты и запинки из текста.
INITIAL_PROMPT = "Ну, э-э, вот, как бы, значит, мм, это самое, короче. Так, ну, в общем, я, э, хотел сказать."


@dataclass
class Word:
    text: str
    start: float
    end: float
    prob: float


@dataclass
class Transcript:
    text: str
    words: list[Word] = field(default_factory=list)
    language: str = "ru"
    device: str = "cpu"
    model: str = ""


def _add_cuda_dll_dirs() -> None:
    """На Windows библиотеки CUDA из pip-пакетов nvidia-* надо явно добавить в путь поиска DLL."""
    if sys.platform != "win32":
        return
    try:
        import nvidia  # type: ignore
    except ImportError:
        return
    for base in getattr(nvidia, "__path__", []):
        for sub in ("cublas", "cudnn", "cuda_runtime", "cuda_nvrtc"):
            d = Path(base) / sub / "bin"
            if d.is_dir():
                os.add_dll_directory(str(d))
                os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")


def cuda_available() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


class Transcriber:
    def __init__(self, model_name: str = "auto"):
        self.requested = model_name
        self._model = None
        self._device = "cpu"
        self._name = ""
        self._lock = threading.Lock()

    def _load(self):
        if self._model is not None:
            return
        _add_cuda_dll_dirs()
        from faster_whisper import WhisperModel

        root = str(models_dir() / "whisper")
        attempts: list[tuple[str, str, str]] = []
        if cuda_available():
            name = "large-v3" if self.requested == "auto" else self.requested
            attempts += [(name, "cuda", "float16"), (name, "cuda", "int8_float16")]
        cpu_name = "small" if self.requested == "auto" else self.requested
        attempts.append((cpu_name, "cpu", "int8"))
        last: Exception | None = None
        for name, device, ctype in attempts:
            try:
                log.info("Загружаю Whisper %s на %s (%s)", name, device, ctype)
                model = WhisperModel(name, device=device, compute_type=ctype, download_root=root)
                if device == "cuda":
                    # Проверочный прогон: ошибки cuDNN всплывают только при первом вызове.
                    list(model.transcribe(np.zeros(16000, dtype=np.float32), language="ru")[0])
                self._model, self._device, self._name = model, device, name
                return
            except Exception as e:  # noqa: BLE001
                log.warning("Не получилось (%s/%s): %s", name, device, e)
                last = e
        raise RuntimeError(f"Не удалось загрузить модель распознавания речи: {last}")

    @property
    def device(self) -> str:
        return self._device

    def transcribe(self, audio: np.ndarray) -> Transcript:
        with self._lock:
            self._load()
            segments, _info = self._model.transcribe(
                audio,
                language="ru",
                word_timestamps=True,
                initial_prompt=INITIAL_PROMPT,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 300},
                condition_on_previous_text=False,
                beam_size=5,
            )
            words: list[Word] = []
            texts: list[str] = []
            for seg in segments:
                texts.append(seg.text.strip())
                for w in seg.words or []:
                    t = w.word.strip()
                    if t:
                        words.append(Word(t, float(w.start), float(w.end), float(w.probability)))
        return Transcript(text=" ".join(texts).strip(), words=words, device=self._device, model=self._name)


_shared: Transcriber | None = None


def get_transcriber(model_name: str) -> Transcriber:
    global _shared
    if _shared is None or _shared.requested != model_name:
        _shared = Transcriber(model_name)
    return _shared
