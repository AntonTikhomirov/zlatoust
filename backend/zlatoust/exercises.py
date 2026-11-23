"""Библиотека упражнений. Каждое упражнение привязано к навыку, который оно тренирует."""
from __future__ import annotations

import random

EXERCISES: list[dict] = [
    # Дикция: читаем эталонный текст, сравниваем с распознанным.
    {"id": "tw-karl", "kind": "tongue_twister", "skill": "diction", "title": "Карл и Клара",
     "text": "Карл у Клары украл кораллы, а Клара у Карла украла кларнет.",
     "how": "Сначала медленно и чётко, на каждом согласном. Потом три раза подряд в обычном темпе."},
    {"id": "tw-sasha", "kind": "tongue_twister", "skill": "diction", "title": "Саша и шоссе",
     "text": "Шла Саша по шоссе и сосала сушку.",
     "how": "Разделяйте С и Ш: губы вперёд на Ш, улыбка на С."},
    {"id": "tw-dvor", "kind": "tongue_twister", "skill": "diction", "title": "Трава и дрова",
     "text": "На дворе трава, на траве дрова. Не руби дрова на траве двора.",
     "how": "Чёткое Р и раскатистое Д‑Р. Не глотайте окончания."},
    {"id": "tw-byk", "kind": "tongue_twister", "skill": "diction", "title": "Тупогубый бычок",
     "text": "Бык тупогуб, тупогубенький бычок, у быка бела губа была тупа.",
     "how": "Активные губы на Б и П. Сначала шёпотом, потом в голос."},
    {"id": "tw-greka", "kind": "tongue_twister", "skill": "diction", "title": "Грека через реку",
     "text": "Ехал Грека через реку, видит Грека — в реке рак. Сунул Грека руку в реку, рак за руку Греку цап!",
     "how": "Держите ровный темп, ударения не съезжают."},
    {"id": "tw-kopyta", "kind": "tongue_twister", "skill": "diction", "title": "Топот копыт",
     "text": "От топота копыт пыль по полю летит.",
     "how": "Короткие взрывные П и Т. Ускоряйтесь, только когда всё чисто."},
    {"id": "tw-korabli", "kind": "tongue_twister", "skill": "diction", "title": "Корабли лавировали",
     "text": "Корабли лавировали, лавировали, да не вылавировали.",
     "how": "Следите за Л и В, не смазывайте длинное слово."},
    # Свободная речь на тему.
    {"id": "talk-intro", "kind": "topic", "skill": "fluency", "title": "Самопрезентация",
     "text": "Расскажите о себе за минуту: кто вы, чем занимаетесь и почему это важно.",
     "how": "Начните с сильной первой фразы. Закончите выводом, а не «ну вот, как-то так»."},
    {"id": "talk-object", "kind": "topic", "skill": "fluency", "title": "Предмет рядом",
     "text": "Возьмите любой предмет рядом и продайте его зрителю за минуту.",
     "how": "Три выгоды, один пример, призыв в конце."},
    {"id": "talk-opinion", "kind": "topic", "skill": "pauses", "title": "Мнение с аргументами",
     "text": "Выберите спорный тезис и защитите его: тезис, два аргумента, вывод.",
     "how": "Делайте паузу перед каждым аргументом вместо «ну» и «вот»."},
    {"id": "talk-story", "kind": "topic", "skill": "intonation", "title": "Короткая история",
     "text": "Расскажите случай из жизни, который вас чему-то научил.",
     "how": "Меняйте высоту и громкость голоса в кульминации. Улыбайтесь там, где смешно."},
    # Чтение с суфлёра — интонация и взгляд.
    {"id": "read-intonation", "kind": "reading", "skill": "intonation", "title": "Чтение с выражением",
     "text": "Знаете, что самое трудное в выступлении? Не текст. И не страх. Самое трудное — первые десять секунд. "
             "Именно тогда зал решает, слушать вас или смотреть в телефон. Поэтому начните с вопроса. Или с факта, который удивляет. "
             "А потом — пауза. Дайте людям секунду, чтобы они захотели услышать продолжение.",
     "how": "Подчёркивайте голосом ключевые слова, держите паузы на тире и точках. Поднимайте взгляд в камеру в конце каждой фразы."},
    {"id": "gesture-numbers", "kind": "topic", "skill": "gestures", "title": "Жесты для чисел",
     "text": "Назовите три причины заниматься спортом и покажите каждую жестом: «во-первых», «во-вторых», «в-третьих».",
     "how": "Руки в кадре, жесты выше пояса, от плеча, а не от кисти."},
    {"id": "eye-contact", "kind": "topic", "skill": "eye_contact", "title": "Разговор с объективом",
     "text": "Представьте, что за камерой сидит близкий друг. Расскажите ему, как прошла ваша неделя.",
     "how": "Смотрите в объектив, а не на своё изображение. Можно наклеить стикер рядом с камерой."},
]

BY_ID = {e["id"]: e for e in EXERCISES}

SKILL_TITLES = {
    "tempo": "Темп",
    "pauses": "Паузы",
    "fluency": "Чистота речи",
    "intonation": "Интонация",
    "loudness": "Громкость",
    "diction": "Дикция",
    "eye_contact": "Взгляд",
    "gestures": "Жесты",
    "posture": "Осанка",
    "face": "Мимика",
}

# Что делать, если навык проседает.
SKILL_TO_EXERCISES = {
    "tempo": ["read-intonation", "talk-opinion"],
    "pauses": ["talk-opinion", "read-intonation"],
    "fluency": ["talk-intro", "talk-object", "talk-opinion"],
    "intonation": ["read-intonation", "talk-story"],
    "loudness": ["read-intonation", "talk-object"],
    "diction": ["tw-karl", "tw-sasha", "tw-dvor", "tw-byk", "tw-greka", "tw-kopyta", "tw-korabli"],
    "eye_contact": ["eye-contact", "talk-intro"],
    "gestures": ["gesture-numbers", "talk-object"],
    "posture": ["talk-intro", "gesture-numbers"],
    "face": ["talk-story", "eye-contact"],
}


def pick_for_skill(skill: str, exclude: str | None = None) -> dict:
    ids = [i for i in SKILL_TO_EXERCISES.get(skill, ["talk-intro"]) if i != exclude] or ["talk-intro"]
    return BY_ID[random.choice(ids)]
