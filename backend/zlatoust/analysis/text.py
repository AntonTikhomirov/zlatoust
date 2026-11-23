"""Работа с русским текстом: нормализация, слоги, слова-паразиты, сравнение с эталоном."""
from __future__ import annotations

import re

VOWELS = set("аеёиоуыэюя")
_word_re = re.compile(r"[а-яёa-z0-9]+(?:-[а-яёa-z0-9]+)*", re.IGNORECASE)


def norm_word(w: str) -> str:
    return w.lower().replace("ё", "е").strip(".,!?;:«»\"'()—–-… ")


def tokens(text: str) -> list[str]:
    return [m.group(0).lower().replace("ё", "е") for m in _word_re.finditer(text)]


def syllables(word: str) -> int:
    """В русском число слогов = число гласных. Точно и без словарей."""
    return sum(1 for ch in word.lower() if ch in VOWELS)


# Однословные паразиты всегда считаем; «вот», «так», «значит» — только как вставку (см. ниже).
FILLER_SOUNDS = {"э", "ээ", "эээ", "э-э", "э-э-э", "м", "мм", "ммм", "эм", "эмм", "а-а", "ааа", "хм"}
FILLER_WORDS = {"ну", "типа", "короче", "вот", "значит", "собственно", "блин", "кстати", "щас"}
FILLER_PHRASES = [
    ("как", "бы"),
    ("это", "самое"),
    ("в", "общем"),
    ("в", "принципе"),
    ("так", "сказать"),
    ("на", "самом", "деле"),
    ("скажем", "так"),
    ("то", "есть"),
    ("как", "говорится"),
]


def find_fillers(words: list[str]) -> list[tuple[int, int, str]]:
    """Возвращает (начальный индекс, число слов, фраза). words — нормализованные слова."""
    out: list[tuple[int, int, str]] = []
    i = 0
    n = len(words)
    while i < n:
        matched = False
        for ph in FILLER_PHRASES:
            L = len(ph)
            if tuple(words[i : i + L]) == ph:
                out.append((i, L, " ".join(ph)))
                i += L
                matched = True
                break
        if matched:
            continue
        w = words[i]
        if w in FILLER_SOUNDS or re.fullmatch(r"(э+|м+|эм+|а-а+)", w):
            out.append((i, 1, w))
        elif w in FILLER_WORDS:
            # «вот» в «вот этот пример» — не паразит; эвристика: паразит стоит в начале фразы или рядом с другим паразитом.
            if w in {"вот", "значит"}:
                prev_is_filler = bool(out) and out[-1][0] + out[-1][1] == i
                if i == 0 or prev_is_filler or (i + 1 < n and words[i + 1] in FILLER_WORDS):
                    out.append((i, 1, w))
            else:
                out.append((i, 1, w))
        i += 1
    return out


def levenshtein_ops(ref: list[str], hyp: list[str]) -> list[tuple[str, str | None, str | None]]:
    """Выравнивание ref↔hyp: список (op, ref_token, hyp_token), op ∈ ok/sub/del/ins."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
    ops: list[tuple[str, str | None, str | None]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1):
            ops.append(("ok" if ref[i - 1] == hyp[j - 1] else "sub", ref[i - 1], hyp[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("del", ref[i - 1], None))
            i -= 1
        else:
            ops.append(("ins", None, hyp[j - 1]))
            j -= 1
    return ops[::-1]


def edit_distance(a: list | str, b: list | str) -> int:
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return prev[-1]


def diction_compare(reference: str, spoken: str) -> dict:
    ref = [t for t in tokens(reference)]
    hyp = tokens(spoken)
    # Паразиты считаются отдельно и не должны портить оценку дикции.
    drop = {i for st, L, _ in find_fillers(hyp) for i in range(st, st + L)}
    hyp = [t for i, t in enumerate(hyp) if i not in drop]
    if not ref:
        return {}
    ops = levenshtein_ops(ref, hyp)
    wer = sum(1 for o in ops if o[0] != "ok") / len(ref)
    correct = sum(1 for o in ops if o[0] == "ok")
    ref_chars = " ".join(ref)
    cer = edit_distance(ref_chars, " ".join(hyp)) / max(1, len(ref_chars))
    return {
        "wer": round(wer, 3),
        "cer": round(cer, 3),
        "accuracy": round(correct / len(ref), 3),
        "ops": [{"op": o, "ref": r, "hyp": h} for o, r, h in ops],
        "problem_words": sorted({r for o, r, _ in ops if o in ("sub", "del") and r}),
    }
