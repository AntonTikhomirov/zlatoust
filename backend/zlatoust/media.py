"""Декодирование записи (webm/mp4 из браузера) через PyAV — ffmpeg внутри пакета, ставить отдельно не нужно."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import av
import numpy as np

SAMPLE_RATE = 16_000


@dataclass
class Frame:
    t: float  # секунды от начала
    rgb: np.ndarray  # HxWx3 uint8


def load_audio(path: Path) -> np.ndarray:
    """Моно float32, 16 кГц. Пустой массив, если звуковой дорожки нет."""
    with av.open(str(path)) as c:
        if not c.streams.audio:
            return np.zeros(0, dtype=np.float32)
        stream = c.streams.audio[0]
        resampler = av.AudioResampler(format="flt", layout="mono", rate=SAMPLE_RATE)
        chunks: list[np.ndarray] = []
        for frame in c.decode(stream):
            for rf in resampler.resample(frame):
                chunks.append(rf.to_ndarray().reshape(-1))
        for rf in resampler.resample(None):
            chunks.append(rf.to_ndarray().reshape(-1))
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32)


def has_video(path: Path) -> bool:
    with av.open(str(path)) as c:
        return bool(c.streams.video)


def iter_frames(path: Path, fps: float = 10.0, max_width: int = 640) -> Iterator[Frame]:
    """Кадры с шагом 1/fps. Браузерный webm часто без длительности и с переменным fps — опираемся на pts."""
    with av.open(str(path)) as c:
        if not c.streams.video:
            return
        stream = c.streams.video[0]
        stream.thread_type = "AUTO"
        step = 1.0 / fps
        next_t = 0.0
        t0: float | None = None
        for frame in c.decode(stream):
            if frame.pts is None or frame.time_base is None:
                continue
            t = float(frame.pts * frame.time_base)
            if t0 is None:
                t0 = t
            t -= t0
            if t + 1e-6 < next_t:
                continue
            while next_t <= t:
                next_t += step
            w, h = frame.width, frame.height
            if w > max_width:
                h = int(round(h * max_width / w / 2) * 2)
                w = max_width
            yield Frame(t=t, rgb=frame.to_ndarray(format="rgb24", width=w, height=h))
