"""Метрики речи по пословным меткам времени: темп, паузы, паразиты, повторы."""
from __future__ import annotations

from statistics import median

from .text import find_fillers, norm_word, syllables
from .transcribe import Word

PAUSE_MIN = 0.35  # короче — это обычная артикуляционная пауза
LONG_PAUSE = 2.0


def speech_metrics(words: list[Word], duration: float) -> dict:
    if not words:
        return {"word_count": 0, "duration": round(duration, 2), "silent": True}

    norm = [norm_word(w.text) for w in words]
    fillers = find_fillers(norm)
    filler_idx = {i for s, L, _ in fillers for i in range(s, s + L)}

    pauses = []
    for a, b in zip(words, words[1:]):
        gap = b.start - a.end
        if gap >= PAUSE_MIN:
            pauses.append({"t": round(a.end, 2), "dur": round(gap, 2)})

    speech_start, speech_end = words[0].start, words[-1].end
    speaking_span = max(0.1, speech_end - speech_start)
    pause_total = sum(p["dur"] for p in pauses)
    articulation_time = max(0.1, speaking_span - pause_total)

    content_words = [w for i, w in enumerate(norm) if i not in filler_idx and w]
    syl = sum(syllables(w) for w in content_words)

    # Повторы: «я я», «мы мы» — признак запинки.
    repeats = [
        {"t": round(words[i].start, 2), "word": norm[i]}
        for i in range(1, len(norm))
        if norm[i] and norm[i] == norm[i - 1] and i not in filler_idx
    ]

    # Темп по окнам 10 с — чтобы видеть, ускоряется ли человек к концу.
    windows = []
    t = 0.0
    while t < speech_end:
        ws = [norm[i] for i, w in enumerate(words) if t <= w.start < t + 10 and i not in filler_idx]
        windows.append({"t": t, "syl_per_sec": round(sum(syllables(x) for x in ws) / 10, 2)})
        t += 10

    minutes = max(1e-6, duration / 60)
    low_conf = [
        {"t": round(w.start, 2), "word": w.text} for w in words if w.prob < 0.45 and norm_word(w.text) not in ("",)
    ]

    return {
        "duration": round(duration, 2),
        "word_count": len(content_words),
        "words_per_min": round(len(content_words) / minutes, 1),
        "syllables_per_sec": round(syl / speaking_span, 2),
        "articulation_rate": round(syl / articulation_time, 2),
        "pause_count": len(pauses),
        "long_pauses": [p for p in pauses if p["dur"] >= LONG_PAUSE],
        "pauses": pauses,
        "pause_ratio": round(pause_total / speaking_span, 3),
        "median_pause": round(median([p["dur"] for p in pauses]), 2) if pauses else 0.0,
        "start_delay": round(speech_start, 2),
        "fillers": [{"t": round(words[s].start, 2), "text": ph} for s, _L, ph in fillers],
        "fillers_per_min": round(len(fillers) / minutes, 2),
        "repeats": repeats,
        "tempo_windows": windows,
        "unclear_words": low_conf[:30],
    }
