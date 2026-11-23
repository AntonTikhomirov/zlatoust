"""Перевод метрик в оценки 0–100 и наблюдения. Пороги — стартовые эвристики, их можно подстраивать.

Принцип: оценку считает код, а не LLM. LLM потом только объясняет и советует.
"""
from __future__ import annotations

from ..exercises import SKILL_TITLES


def band(v: float, good_lo: float, good_hi: float, bad_lo: float, bad_hi: float) -> int:
    """100 внутри [good_lo, good_hi], линейно до 40 к границам bad_*, дальше до 10."""
    if good_lo <= v <= good_hi:
        return 100
    if v < good_lo:
        edge, bad = good_lo, bad_lo
    else:
        edge, bad = good_hi, bad_hi
    span = abs(edge - bad) or 1e-6
    k = abs(v - edge) / span
    return int(max(10, round(100 - 60 * k if k <= 1 else 40 - 30 * min(1, (k - 1)))))


def _obs(skill: str, level: str, text: str, t: float | None = None, fix: str | None = None) -> dict:
    return {"skill": skill, "level": level, "text": text, "t": t, "fix": fix}


def n(x: float, digits: int = 1) -> str:
    """Число по-русски: десятичная запятая."""
    return f"{x:.{digits}f}".replace(".", ",")


def fmt_t(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def score(speech: dict, prosody: dict, video: dict, diction: dict | None, mode: str) -> dict:
    scores: dict[str, int] = {}
    obs: list[dict] = []

    if speech.get("silent") or speech.get("word_count", 0) < 5:
        obs.append(_obs("fluency", "bad", "Речь почти не распознана. Проверьте, что выбран нужный микрофон и он не выключен."))
    else:
        # Темп: слоги в секунду на всём отрезке речи. Комфортно для слушателя ~3.5–5.
        sps = speech["syllables_per_sec"]
        scores["tempo"] = band(sps, 3.4, 5.2, 2.4, 6.5)
        if sps > 5.2:
            obs.append(_obs("tempo", "warn", f"Темп высокий: {n(sps)} слога в секунду. Слушателю комфортно до 5. Замедлитесь и добавьте паузы."))
        elif sps < 3.4:
            obs.append(_obs("tempo", "warn", f"Темп медленный: {n(sps)} слога в секунду. Речь может звучать неуверенно."))
        else:
            obs.append(_obs("tempo", "good", f"Темп комфортный: {n(sps)} слога в секунду."))
        w = speech.get("tempo_windows", [])
        if len(w) >= 4:
            first = sum(x["syl_per_sec"] for x in w[: len(w) // 2]) / (len(w) // 2)
            last = sum(x["syl_per_sec"] for x in w[len(w) // 2 :]) / (len(w) - len(w) // 2)
            if first > 0 and last / first > 1.25:
                obs.append(_obs("tempo", "warn", "К концу вы заметно ускорились. Так бывает от волнения, следите за темпом во второй половине.", w[len(w) // 2]["t"]))

        # Паузы: доля пауз 10–30% от времени речи. Слишком мало — «пулемёт», слишком много — зависания.
        pr = speech["pause_ratio"]
        scores["pauses"] = band(pr, 0.10, 0.30, 0.02, 0.50)
        if pr < 0.10:
            obs.append(_obs("pauses", "warn", "Почти нет пауз. Пауза после важной мысли даёт слушателю её усвоить."))
        for p in speech.get("long_pauses", [])[:3]:
            obs.append(_obs("pauses", "warn", f"Долгая пауза {n(p['dur'])} с на {fmt_t(p['t'])}: похоже на потерю мысли.", p["t"]))
        if speech.get("start_delay", 0) > 2.5:
            obs.append(_obs("pauses", "warn", f"Начали говорить только через {speech['start_delay']:.0f} с после старта.", 0))

        # Паразиты.
        fpm = speech["fillers_per_min"]
        reps = len(speech.get("repeats", []))
        scores["fluency"] = max(10, band(fpm, 0, 1.5, 0, 8) - 4 * max(0, reps - 1))
        if speech["fillers"]:
            top: dict[str, int] = {}
            for f in speech["fillers"]:
                top[f["text"]] = top.get(f["text"], 0) + 1
            worst = ", ".join(f"«{k}» ×{v}" for k, v in sorted(top.items(), key=lambda kv: -kv[1])[:3])
            level = "bad" if fpm > 5 else "warn" if fpm > 1.5 else "good"
            obs.append(_obs("fluency", level, f"Слова-паразиты: {n(fpm)} в минуту. Чаще всего {worst}.", speech["fillers"][0]["t"]))
        else:
            obs.append(_obs("fluency", "good", "Слов-паразитов не слышно."))
        if reps >= 2:
            obs.append(_obs("fluency", "warn", f"Запинки с повтором слова: {reps}.", speech["repeats"][0]["t"]))

    if prosody.get("pitch_std_st") is not None:
        st = prosody["pitch_std_st"]
        scores["intonation"] = band(st, 2.5, 6.0, 1.0, 9.0)
        if st < 2.5:
            obs.append(_obs("intonation", "warn", f"Голос звучит монотонно: разброс высоты {n(st)} полутона. Живая речь — от 2,5 и выше."))
        else:
            obs.append(_obs("intonation", "good", f"Интонация живая: разброс высоты {n(st)} полутона."))

    if prosody:
        lvl = prosody.get("level_dbfs", -30)
        drop = prosody.get("phrase_end_drop_db", 0)
        # Оценка — только за навык (договаривает ли человек концы фраз). Уровень микрофона —
        # техническое замечание: он зависит от настроек Windows, а не от голоса, и оценку не снижает.
        s = band(drop, -10, 6, -20, 12)
        if lvl < -45:
            obs.append(_obs("loudness", "warn", f"Микрофон записывает очень тихо ({n(lvl)} дБ). На оценку это не влияет, но точность разбора ниже: поднимите «Громкость ввода» в настройках звука Windows."))
        if prosody.get("clipping"):
            obs.append(_obs("loudness", "warn", "Звук перегружен и хрипит. Снизьте «Громкость ввода» в настройках звука Windows или отодвиньте микрофон."))
        if drop > 6:
            fading = prosody.get("fading_phrases", [])
            obs.append(_obs("loudness", "warn", f"Концы фраз затихают в среднем на {drop:.0f} дБ. Договаривайте последнее слово.", fading[0]["t"] if fading else None))
        scores["loudness"] = s

    if diction:
        acc = diction["accuracy"]
        scores["diction"] = band(acc, 0.95, 1.0, 0.6, 1.0)
        if diction["problem_words"]:
            words = ", ".join(f"«{w}»" for w in diction["problem_words"][:6])
            obs.append(_obs("diction", "warn" if acc > 0.8 else "bad", f"Распознано {acc * 100:.0f}% текста. Нечётко прозвучали: {words}."))
        else:
            obs.append(_obs("diction", "good", "Текст распознан полностью, слова звучат чётко."))

    if video.get("video"):
        fv = video.get("face_visible_ratio", 0)
        if fv < 0.7:
            obs.append(_obs("eye_contact", "warn", f"Лицо было в кадре только {fv * 100:.0f}% времени.",
                            fix="Поставьте камеру на уровень глаз и сядьте так, чтобы лицо было в центре кадра."))
        if "eye_contact_ratio" in video:
            ec = video["eye_contact_ratio"]
            scores["eye_contact"] = band(ec, 0.7, 1.0, 0.3, 1.0)
            if ec < 0.7:
                obs.append(_obs("eye_contact", "warn", f"В камеру вы смотрели {ec * 100:.0f}% времени. Хорошо — от 70%."))
            else:
                obs.append(_obs("eye_contact", "good", f"Хороший контакт с камерой: {ec * 100:.0f}% времени."))
            for r in video.get("look_away", [])[:3]:
                obs.append(_obs("eye_contact", "warn", f"Взгляд в сторону {r['dur']:.0f} с.", r["t"]))
            fr = video.get("framing", {})
            if fr:
                if fr["face_height"] < 0.12:
                    obs.append(_obs("eye_contact", "warn", "Вы далеко от камеры: лицо занимает мало места в кадре."))
                elif fr["face_height"] > 0.5:
                    obs.append(_obs("eye_contact", "warn", "Вы слишком близко к камере."))
                if not 0.3 <= fr["face_center_x"] <= 0.7:
                    obs.append(_obs("eye_contact", "warn", "Вы не по центру кадра."))

        if "expressiveness" in video:
            ex = video["expressiveness"]
            scores["face"] = band(ex, 0.6, 3.0, 0.15, 5.0)
            if ex < 0.6:
                obs.append(_obs("face", "warn", "Лицо малоподвижно. Брови и улыбка помогают передать эмоцию."))
            else:
                obs.append(_obs("face", "good", "Мимика живая."))

        if "sway" in video:
            sway = video["sway"]
            tilt = abs(video.get("shoulder_tilt_deg", 0))
            s = min(band(sway, 0, 0.04, 0, 0.15), band(tilt, 0, 4, 0, 12))
            scores["posture"] = s
            if sway > 0.04:
                obs.append(_obs("posture", "warn", "Вы покачиваетесь. Встаньте устойчиво, вес на обе ноги."))
            if tilt > 4:
                obs.append(_obs("posture", "warn", f"Плечи перекошены на {tilt:.0f}°."))
            if s >= 90:
                obs.append(_obs("posture", "good", "Корпус устойчивый, плечи ровные."))

            hv = video.get("hands_visible_ratio", 0)
            act = video.get("gesture_active_ratio", 0)
            if hv < 0.2:
                scores["gestures"] = 40
                obs.append(_obs("gestures", "warn", "Рук почти не видно в кадре. Отойдите чуть дальше, чтобы жесты попадали в кадр."))
            else:
                scores["gestures"] = band(act, 0.12, 0.5, 0.0, 0.85)
                if act < 0.12:
                    obs.append(_obs("gestures", "warn", "Жестов мало. Жест, который подкрепляет мысль, делает речь убедительнее."))
                elif act > 0.5:
                    obs.append(_obs("gestures", "warn", "Руки двигаются почти всё время. Это отвлекает: оставьте жесты для ключевых мыслей."))
                else:
                    obs.append(_obs("gestures", "good", "Жестикуляция в меру."))
            if video.get("hand_face_touches", 0) >= 2:
                obs.append(_obs("gestures", "warn", f"Руки тянулись к лицу {video['hand_face_touches']} раза. Так часто выглядит волнение."))

    # Общая оценка: среднее по доступным навыкам, дикция весит больше в режиме скороговорки.
    weights = {k: (3 if k == "diction" and mode == "tongue_twister" else 1) for k in scores}
    overall = round(sum(scores[k] * weights[k] for k in scores) / max(1, sum(weights.values()))) if scores else None
    weakest = sorted(scores, key=lambda k: scores[k])[:2]
    return {
        "overall": overall,
        "scores": [{"skill": k, "title": SKILL_TITLES[k], "score": v} for k, v in scores.items()],
        "observations": obs,
        "weakest": weakest,
    }
