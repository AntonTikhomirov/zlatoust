"""Слой толкования. Код уже посчитал метрики и оценки; здесь из них получается человеческий разбор.

Три провайдера с одним интерфейсом: rules (без LLM), ollama (локально), anthropic (Claude API).
Любая ошибка LLM -> разбор по правилам, отчёт всё равно будет.
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field, ValidationError

from ..exercises import BY_ID, EXERCISES, SKILL_TITLES, pick_for_skill
from ..settings import Settings

log = logging.getLogger(__name__)


class Improvement(BaseModel):
    skill: str
    problem: str
    how_to_fix: str
    t: float | None = None


class Feedback(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    improvements: list[Improvement] = Field(default_factory=list)
    next_exercise_id: str
    next_exercise_why: str = ""


FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "improvements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill": {"type": "string", "enum": list(SKILL_TITLES)},
                    "problem": {"type": "string"},
                    "how_to_fix": {"type": "string"},
                    "t": {"type": ["number", "null"]},
                },
                "required": ["skill", "problem", "how_to_fix", "t"],
                "additionalProperties": False,
            },
        },
        "next_exercise_id": {"type": "string", "enum": [e["id"] for e in EXERCISES]},
        "next_exercise_why": {"type": "string"},
    },
    "required": ["summary", "strengths", "improvements", "next_exercise_id", "next_exercise_why"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """Ты — опытный тренер по ораторскому мастерству и сценической речи. Ты разбираешь короткую видеозапись ученика.

Метрики уже посчитаны программой и точны. Твоя задача — объяснить их по-человечески и дать конкретные советы.

Правила:
- Пиши по-русски, на «вы», коротко и конкретно, без воды и без канцелярита.
- Опирайся ТОЛЬКО на переданные метрики, наблюдения и расшифровку. Не придумывай того, чего в данных нет. Не оценивай внешность.
- summary: 2–3 предложения — главное впечатление и самое важное, над чем работать.
- strengths: 1–3 пункта, что действительно получилось (по данным).
- improvements: 2–4 пункта, самые важные первыми. problem — что не так, с цифрой или примером из речи. how_to_fix — одно конкретное действие или упражнение, которое можно сделать сегодня. t — секунда записи, если проблема привязана ко времени, иначе null.
- next_exercise_id выбирай ТОЛЬКО из списка упражнений, под самый слабый навык. next_exercise_why — одно предложение, зачем оно.
- Расшифровка сделана автоматически и может содержать ошибки распознавания. Не ругай ученика за слова, которые могли быть распознаны неверно, если это не задание на дикцию."""


def _payload(metrics: dict, scored: dict, transcript: str, mode: str, exercise: dict | None) -> str:
    sp = dict(metrics.get("speech", {}))
    for k in ("pauses", "tempo_windows", "unclear_words"):
        sp.pop(k, None)
    data = {
        "режим": mode,
        "упражнение": {"название": exercise["title"], "задание": exercise["text"]} if exercise else None,
        "оценки_0_100": {s["title"]: s["score"] for s in scored["scores"]},
        "общая_оценка": scored["overall"],
        "наблюдения_программы": [o["text"] + (f" (t={o['t']})" if o.get("t") is not None else "") for o in scored["observations"]],
        "речь": sp,
        "голос": {k: v for k, v in metrics.get("prosody", {}).items() if k not in ("pitch_windows", "fading_phrases")},
        "видео": metrics.get("video", {}),
        "дикция": {k: v for k, v in (metrics.get("diction") or {}).items() if k != "ops"} or None,
        "расшифровка": transcript[:4000],
        "упражнения": [{"id": e["id"], "навык": SKILL_TITLES.get(e["skill"], e["skill"]), "название": e["title"]} for e in EXERCISES],
    }
    return json.dumps(data, ensure_ascii=False)


def rules_feedback(scored: dict, exercise_id: str | None) -> Feedback:
    obs = scored["observations"]
    good = [o["text"] for o in obs if o["level"] == "good"][:3]
    bad = sorted([o for o in obs if o["level"] in ("bad", "warn")], key=lambda o: o["level"] != "bad")
    weakest = scored.get("weakest") or ["fluency"]
    nxt = pick_for_skill(weakest[0], exclude=exercise_id)
    tips = {
        "tempo": "Прочитайте текст вслух, отмечая паузы косыми чертами, и держите их.",
        "pauses": "Вместо «ну» и «э» молча выдохните. Пауза в секунду звучит увереннее, чем звук.",
        "fluency": "Запишитесь ещё раз и ставьте паузу каждый раз, когда хочется сказать паразит.",
        "intonation": "Выделяйте голосом одно ключевое слово в каждой фразе: выше или громче.",
        "loudness": "Последнее слово фразы говорите так же громко, как первое, — на опоре дыхания.",
        "diction": "Проговорите проблемные слова медленно, утрированно артикулируя, потом в обычном темпе.",
        "eye_contact": "Наклейте стикер рядом с объективом и обращайтесь к нему.",
        "gestures": "Держите руки над поясом в зоне кадра и подкрепляйте жестом ключевые мысли.",
        "posture": "Встаньте на обе ноги на ширине плеч, колени не зажаты.",
        "face": "Улыбнитесь в начале и в конце. Поднимайте брови на вопросах.",
    }
    seen: set[str] = set()
    imps = []
    for o in bad:
        if o["skill"] in seen:
            continue
        seen.add(o["skill"])
        imps.append(Improvement(skill=o["skill"], problem=o["text"], how_to_fix=tips.get(o["skill"], ""), t=o.get("t")))
        if len(imps) == 4:
            break
    ov = scored.get("overall")
    if ov is None:
        summary = "Не удалось оценить запись: речь почти не распознана."
    else:
        head = "Сильная запись." if ov >= 85 else "Хорошая основа." if ov >= 70 else "Есть над чем поработать."
        focus = SKILL_TITLES.get(weakest[0], "")
        summary = f"{head} Общая оценка — {ov} из 100. Главный фокус на следующую тренировку — {focus.lower()}."
    return Feedback(summary=summary, strengths=good, improvements=imps, next_exercise_id=nxt["id"],
                    next_exercise_why=f"Тренирует навык «{SKILL_TITLES.get(nxt['skill'], '')}», который сейчас слабее остальных.")


def _call_anthropic(s: Settings, user: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=s.anthropic_api_key, timeout=120, max_retries=2)
    resp = client.messages.create(
        model=s.anthropic_model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": FEEDBACK_SCHEMA}},
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("модель отказалась отвечать")
    return next(b.text for b in resp.content if b.type == "text")


def _call_ollama(s: Settings, user: str) -> str:
    import httpx

    r = httpx.post(
        f"{s.ollama_url.rstrip('/')}/api/chat",
        json={
            "model": s.ollama_model,
            "stream": False,
            "format": FEEDBACK_SCHEMA,
            "options": {"temperature": 0.3},
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
        },
        timeout=300,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


def interpret(s: Settings, metrics: dict, scored: dict, transcript: str, mode: str, exercise_id: str | None) -> tuple[dict, str, str | None]:
    """Возвращает (feedback, провайдер, ошибка LLM или None)."""
    base = rules_feedback(scored, exercise_id)
    if s.llm_provider == "none" or (s.llm_provider == "anthropic" and not s.anthropic_api_key):
        return base.model_dump(), "rules", None
    user = _payload(metrics, scored, transcript, mode, BY_ID.get(exercise_id or ""))
    try:
        raw = _call_anthropic(s, user) if s.llm_provider == "anthropic" else _call_ollama(s, user)
        fb = Feedback.model_validate_json(raw)
        if fb.next_exercise_id not in BY_ID:
            fb.next_exercise_id = base.next_exercise_id
        fb.improvements = [i for i in fb.improvements if i.skill in SKILL_TITLES]
        return fb.model_dump(), s.llm_provider, None
    except (ValidationError, Exception) as e:  # noqa: BLE001
        log.warning("LLM недоступна, разбор по правилам: %s", e)
        return base.model_dump(), "rules", str(e)[:300]


def test_connection(s: Settings) -> str:
    if s.llm_provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=s.anthropic_api_key, timeout=30, max_retries=0)
        client.messages.create(model=s.anthropic_model, max_tokens=16, messages=[{"role": "user", "content": "Ответь одним словом: готово"}])
        return "Claude API отвечает."
    if s.llm_provider == "ollama":
        import httpx

        r = httpx.get(f"{s.ollama_url.rstrip('/')}/api/tags", timeout=5)
        r.raise_for_status()
        names = [m["name"] for m in r.json().get("models", [])]
        if not any(n == s.ollama_model or n.split(":")[0] == s.ollama_model.split(":")[0] for n in names):
            raise RuntimeError(f"Ollama работает, но модели {s.ollama_model} нет. Выполните: ollama pull {s.ollama_model}")
        return "Ollama отвечает, модель на месте."
    return "LLM выключена — разбор по правилам."
