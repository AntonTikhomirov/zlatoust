"""Голос: высота тона и её разнообразие, громкость, «проглатывание» концов фраз. Считает Praat (parselmouth)."""
from __future__ import annotations

import numpy as np
import parselmouth

from ..media import SAMPLE_RATE


def _db(x: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.square(x)) + 1e-12))
    return 20 * np.log10(rms + 1e-12)


def prosody_metrics(audio: np.ndarray, phrases: list[tuple[float, float]]) -> dict:
    """phrases — интервалы речи (начало, конец) между заметными паузами."""
    if audio.size < SAMPLE_RATE:
        return {}
    snd = parselmouth.Sound(audio.astype(np.float64), sampling_frequency=SAMPLE_RATE)

    pitch = snd.to_pitch_ac(time_step=0.01, pitch_floor=70, pitch_ceiling=450)
    f0 = pitch.selected_array["frequency"]
    voiced = f0[f0 > 0]
    out: dict = {}
    if voiced.size > 20:
        st = 12 * np.log2(voiced / np.median(voiced))  # полутона от медианы
        out.update(
            pitch_median_hz=round(float(np.median(voiced)), 1),
            pitch_std_st=round(float(np.std(st)), 2),
            pitch_range_st=round(float(np.percentile(st, 95) - np.percentile(st, 5)), 2),
        )
        # Динамика по окнам 10 с: монотонность обычно нарастает к концу.
        times = pitch.xs()
        win = []
        for t0 in np.arange(0, snd.duration, 10.0):
            m = (times >= t0) & (times < t0 + 10) & (f0 > 0)
            if m.sum() > 20:
                s = 12 * np.log2(f0[m] / np.median(voiced))
                win.append({"t": float(t0), "pitch_std_st": round(float(np.std(s)), 2)})
        out["pitch_windows"] = win

    intensity = snd.to_intensity(minimum_pitch=75, time_step=0.02)
    it = intensity.values[0].copy()
    # Шумодав WebView2 отдаёт в паузах точные нули, Praat даёт на них огромные минусы дБ.
    # Всё, что тише 40 дБ от пика записи, считаем тишиной и в расчёт не берём.
    it[~np.isfinite(it)] = -300.0
    loud = it > (np.max(it) - 40)
    itx = intensity.xs()
    speech_mask = np.zeros_like(it, dtype=bool)
    for a, b in phrases:
        speech_mask |= (itx >= a) & (itx <= b)
    speech_mask &= loud
    if speech_mask.sum() > 10:
        sp = it[speech_mask]
        out["loudness_std_db"] = round(float(np.std(sp)), 2)

    # Уровень записи в dBFS — чтобы сказать «микрофон слишком тихий» или «перегруз».
    peak = float(np.max(np.abs(audio)))
    out["level_dbfs"] = round(_db(audio[np.abs(audio) > 0.003]) if np.any(np.abs(audio) > 0.003) else -90.0, 1)
    out["clipping"] = bool(np.mean(np.abs(audio) > 0.98) > 0.001)
    out["peak"] = round(peak, 3)

    # Затухание к концу фразы: громкость последнего слога (~0,4 с) против типичной громкости фразы.
    # Берём только звучащие кадры (не тише фразы на 25 дБ): Whisper часто тянет конец слова в тишину,
    # и без этого фильтра любая фраза «затухала» бы. Естественное понижение тона в конце
    # повествовательной фразы даёт 3–6 дБ, это норма.
    drops = []
    for a, b in phrases:
        if b - a < 1.2:
            continue
        seg = it[(itx >= a) & (itx <= b)]
        if seg.size < 10:
            continue
        ref = float(np.percentile(seg, 75))
        tail = it[(itx >= b - 0.4) & (itx <= b)]
        tail = tail[tail > ref - 25]
        body = seg[seg > ref - 25]
        if tail.size > 3 and body.size > 5:
            drops.append({"t": round(b, 2), "drop_db": round(float(np.median(body) - np.median(tail)), 1)})
    if drops:
        out["phrase_end_drop_db"] = round(float(np.median([d["drop_db"] for d in drops])), 1)
        out["fading_phrases"] = [d for d in drops if d["drop_db"] >= 10]
    return out


def phrases_from_words(words, gap: float = 0.5) -> list[tuple[float, float]]:
    if not words:
        return []
    res = []
    start = words[0].start
    prev_end = words[0].end
    for w in words[1:]:
        if w.start - prev_end >= gap:
            res.append((start, prev_end))
            start = w.start
        prev_end = w.end
    res.append((start, prev_end))
    return res
