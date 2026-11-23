"""Конвейер анализа одной записи и фоновая очередь (по одной записи за раз — видеокарта одна)."""
from __future__ import annotations

import logging
import queue
import threading
import traceback
from pathlib import Path

from . import db, settings
from .analysis.prosody import phrases_from_words, prosody_metrics
from .analysis.scoring import score
from .analysis.speech import speech_metrics
from .analysis.text import diction_compare, find_fillers, norm_word
from .analysis.transcribe import Transcriber, get_transcriber
from .exercises import BY_ID
from .llm import interpret
from .media import SAMPLE_RATE, has_video, load_audio
from .paths import recordings_dir

log = logging.getLogger(__name__)

# Для тестов можно подменить распознавание и видеоанализ.
transcriber_factory = get_transcriber
video_analyzer = None


def _video(path: Path, progress, duration):
    if video_analyzer is not None:
        return video_analyzer(path, progress, duration)
    from .analysis.video import video_metrics

    return video_metrics(path, progress, duration)


def analyze(sid: str) -> None:
    s = db.get(sid)
    if not s:
        return
    cfg = settings.load()
    path = recordings_dir() / s["video_file"]

    def stage(name: str, p: float) -> None:
        db.update(sid, status="processing", stage=name, progress=round(p, 3))

    stage("audio", 0.02)
    audio = load_audio(path)
    duration = audio.size / SAMPLE_RATE
    db.update(sid, duration=round(duration, 2))
    if duration < 3:
        raise ValueError("Запись слишком короткая или без звука.")

    stage("transcribe", 0.08)
    tr: Transcriber = transcriber_factory(cfg.whisper_model)
    transcript = tr.transcribe(audio)

    stage("voice", 0.40)
    sp = speech_metrics(transcript.words, duration)
    pros = prosody_metrics(audio, phrases_from_words(transcript.words))

    diction = None
    ex = BY_ID.get(s["exercise_id"] or "")
    ref = s["reference_text"] or (ex["text"] if ex and ex["kind"] in ("tongue_twister", "reading") else None)
    if ref and s["mode"] in ("tongue_twister", "reading"):
        diction = diction_compare(ref, transcript.text)

    stage("video", 0.50)
    vid: dict = {"video": False}
    if has_video(path):
        try:
            vid = _video(path, lambda p: stage("video", 0.50 + 0.40 * p), duration)
        except Exception as e:  # noqa: BLE001 — видео не должно ломать отчёт по речи
            log.exception("Видеоанализ не удался")
            vid = {"video": False, "error": str(e)[:300]}

    stage("feedback", 0.92)
    metrics = {"speech": sp, "prosody": pros, "video": vid, "diction": diction}
    scored = score(sp, pros, vid, diction, s["mode"])
    feedback, provider, llm_error = interpret(cfg, metrics, scored, transcript.text, s["mode"], s["exercise_id"])

    norm = [norm_word(w.text) for w in transcript.words]
    filler_idx = {i for st, L, _ in find_fillers(norm) for i in range(st, st + L)}
    words_out = [
        {"w": w.text, "s": round(w.start, 2), "e": round(w.end, 2), "f": i in filler_idx, "lc": w.prob < 0.45}
        for i, w in enumerate(transcript.words)
    ]
    report = {
        **scored,
        "feedback": feedback,
        "provider": provider,
        "llm_error": llm_error,
        "transcript": transcript.text,
        "words": words_out,
        "asr": {"device": transcript.device, "model": transcript.model},
    }
    db.update(sid, status="done", stage=None, progress=1.0, metrics=metrics, report=report, error=None)


class Worker:
    def __init__(self) -> None:
        self.q: queue.Queue[str] = queue.Queue()
        self.thread = threading.Thread(target=self._run, name="analysis", daemon=True)

    def start(self) -> None:
        for sid in db.queued_ids():
            self.q.put(sid)
        self.thread.start()

    def submit(self, sid: str) -> None:
        self.q.put(sid)

    def _run(self) -> None:
        while True:
            sid = self.q.get()
            try:
                analyze(sid)
            except Exception as e:  # noqa: BLE001
                log.error("Анализ %s упал: %s\n%s", sid, e, traceback.format_exc())
                db.update(sid, status="error", stage=None, error=str(e)[:500])
