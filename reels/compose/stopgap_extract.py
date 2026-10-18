"""Запасной добытчик фактов — чтобы конвейер был целым до готового экстрактора.

Это не замена `reels/extract/` (ведёт `meta1ex`, извлечение через модель с
машинной сверкой цитат). Здесь дешёвый разбор по предложениям: он беднее и
берёт только то, что видно регулярным выражением. Как только `reels.extract`
появляется, `run.py` берёт его, а этот модуль не вызывается.

Правило контракта соблюдается и здесь: `quote` — всегда точная подстрока
исходника, `text` не содержит ничего, чего нет в `quote`.
"""

import io
import os
import re

# числительные словами: «две недели», «за три дня» — их regex по цифрам теряет
WORD_NUMBERS = ("один", "одна", "одно", "два", "две", "три", "четыре", "пять",
                "шесть", "семь", "восемь", "девять", "десять", "сотня", "тысяч")
# только повелительное наклонение в начале предложения: «нужно» и «достаточно»
# ловили описательные фразы, и в CTA попадало предложение без действия вовсе
ACTION = ("укажи", "опиши", "начни", "попробуй", "возьми", "поставь", "выбери",
          "запусти", "сделай", "проверь", "сформулируй")
PAIN = ("теря", "пропада", "не найти", "вручную", "рутин", "тратил", "тратит",
        "уходит", "забыт", "барьер", "ошиб", "долго")
SENTENCE = re.compile(r"[^.!?\n]+[.!?]")
MAX_FACTS = 20
MIN_WORDS, MAX_WORDS = 5, 40


def _kind(sentence):
    low = sentence.lower()
    if re.search(r"\d", sentence) or any(w in low for w in WORD_NUMBERS):
        return "number"
    if any(low.startswith(w) for w in ACTION):
        return "action"
    return "claim"


def _text(sentence):
    text = " ".join(sentence.split()).rstrip(".!?")
    return text[0].lower() + text[1:] if text else text


def extract(path):
    source = io.open(path, encoding="utf-8").read()
    title = ""
    for line in source.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break
    article_id = os.path.splitext(os.path.basename(path))[0]

    facts, seen_numbers = [], set()
    for m in SENTENCE.finditer(source):
        sentence = m.group(0).strip()
        words = sentence.split()
        if not (MIN_WORDS <= len(words) <= MAX_WORDS):
            continue
        if sentence.startswith("#") or sentence.startswith("-"):
            continue
        kind = _kind(sentence)
        digits = set(re.findall(r"\d+", sentence))
        # факт, чьи числа уже встречались, не добавляет нового
        if digits and digits <= seen_numbers:
            continue
        if kind == "claim" and not any(w in sentence.lower() for w in PAIN):
            continue
        seen_numbers |= digits
        value = sorted(digits)[0] if (kind == "number" and digits) else None
        facts.append({
            "id": f"f{len(facts) + 1}",
            "kind": kind,
            "text": _text(sentence),
            "value": value,
            "unit": None,
            "quote": sentence,
        })
        if len(facts) >= MAX_FACTS:
            break

    return {
        "source": {"id": article_id, "title": title, "origin": path,
                   "chars": len(source)},
        "facts": facts,
    }
