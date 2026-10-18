"""Сборка сценария рилза из facts.json и canon.md.

Модель не вызывается: сборка детерминированная, из фактов и шаблона. Смысл в
том, что сборщик физически не может добавить число или утверждение, которого
нет в facts.json, — а это ключевая проверка приёмочного примера 02-рилз.
"""

import json
import re

from . import lens

PAIN = ("теря", "пропада", "не найти", "вручную", "рутин", "тратил", "тратит",
        "уходит", "забыт", "не понима", "барьер", "ошиб", "долго", "недел")
USABLE = ("number", "claim", "action", "quote")
MIN_FACTS = 2

# Рилз меряется секундами речи, а не знаками: канон ограничивает пост в знаках,
# но в тридцать секунд разговорного темпа влезает примерно 75 слов.
WORDS_PER_SEC = 2.5
LIMITS = (("хук", 3.0), ("суть", 19.0), ("cta", 8.0))

# 30 секунд — потолок отказа, а не цель. Внешние источники (docs/reels-craft.md)
# сходятся на 7–15 с как лучшем, с оговоркой про удержание; целевым коридором
# для упаковки статьи берём 15–20 с — там уже есть что сказать, но ролик ещё
# зацикливается.
TARGET = (15.0, 20.0)

# CTA, бьющие по сигналам ранжирования: отправка — самый сильный из названных.
CTA_SHARE = "отправьте это тому, кто делает то же самое руками"
FALLBACK_CTA = "возьмите один процесс из своей недели и опишите его словами"


def seconds(text):
    return round(len(text.split()) / WORDS_PER_SEC, 1)


STOP = {"это", "как", "что", "для", "при", "все", "уже", "его", "она", "они",
        "или", "над", "под", "без", "два", "три", "той", "тот", "чем", "так"}


def numbers_of(fact):
    return set(re.findall(r"\d+",
                          fact.get("text", "") + " " + str(fact.get("value") or "")))


def content_words(fact):
    words = re.findall(r"[а-яёa-z]{3,}", fact.get("text", "").lower())
    return {w for w in words if w not in STOP}


def repeats(fact, seen_numbers, seen_words):
    """Факт уже прозвучал: его числа целиком известны, либо половина значимых
    слов совпадает с уже сказанным. Одних чисел мало — «за 15 минут» и
    «за 15-20 минут» дают разные множества, а для зрителя это один факт."""
    digits = numbers_of(fact)
    if digits and digits <= seen_numbers:
        return True
    words = content_words(fact)
    return bool(words) and len(words & seen_words) / len(words) >= 0.5


class Refusal(Exception):
    """Штатный отказ: сценарий не собирается, причина уходит в отчёт."""


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _pain_score(fact):
    text = fact.get("text", "").lower()
    return sum(1 for marker in PAIN if marker in text)


def pick(facts, title=""):
    """Хук, 2-3 факта в суть, действие для CTA."""
    usable = [f for f in facts if f.get("kind") in USABLE]
    if len(usable) < MIN_FACTS:
        raise Refusal(
            f"в сырье {len(usable)} пригодных фактов, нужно минимум {MIN_FACTS}")

    actions = [f for f in usable if f.get("kind") == "action"]
    rest = [f for f in usable if f not in actions]

    # Хук — про боль и обязан влезть в свои три секунды: длинный хук зритель
    # не дослушивает. Из подходящих берём самый короткий.
    hook_limit = LIMITS[0][1]

    # Хук, пересказывающий заголовок статьи, — это титульная карточка: тот самый
    # slow intro, который источники называют антипаттерном прямым текстом.
    title_words = {w for w in re.findall(r"[а-яёa-z]{3,}", title.lower())
                   if w not in STOP}

    def is_title_card(fact):
        words = content_words(fact)
        return bool(words) and len(words & title_words) / len(words) >= 0.5

    fresh = [f for f in rest if not is_title_card(f)] or rest
    painful = [f for f in fresh if _pain_score(f) > 0] or \
              [f for f in fresh if f.get("kind") == "number"] or fresh or usable
    # сначала ищем среди болевых, потом среди любых свежих — короткий хук
    # важнее идеального: первые три секунды решают, досмотрят ли вообще
    def usable_hook(fact):
        # «Шаг 3» влезает в лимит, но хуком не является: в хуке должно быть
        # сказано что-то, а не подписан пункт списка
        return seconds(fact["text"]) <= hook_limit and len(content_words(fact)) >= 3

    fitting = ([f for f in painful if usable_hook(f)] or
               [f for f in fresh if usable_hook(f)])
    hook = (max(fitting, key=lambda f: (_pain_score(f), -seconds(f["text"])))
            if fitting else min(painful, key=lambda f: seconds(f["text"])))

    candidates = [f for f in fresh if f["id"] != hook["id"]]
    candidates.sort(key=lambda f: (f.get("kind") != "number", f["id"]))

    # Факт, чьи числа целиком уже прозвучали, ничего не добавляет: три пункта
    # про одни и те же 80 уроков читаются как повтор, а не как три факта.
    # Бюджет сути считается от целевого коридора, а не от собственного лимита:
    # цель — уложить ролик в 15-20 секунд целиком, а не набить суть под потолок.
    seen, seen_words = numbers_of(hook), content_words(hook)
    reserve = seconds(fit_hook(hook["text"])) + seconds(FALLBACK_CTA)
    body, budget = [], min(LIMITS[1][1], TARGET[1] - reserve)
    for fact in candidates:
        if repeats(fact, seen, seen_words):
            continue
        cost = seconds(fact["text"])
        if body and budget - cost < 0:      # в суть больше не влезает
            break
        seen |= numbers_of(fact)
        seen_words |= content_words(fact)
        budget -= cost
        body.append(fact)
        if len(body) == 3:
            break
    if not body:
        raise Refusal("после выбора хука не осталось фактов для сути")

    return hook, body, (actions[0] if actions else None)


def fit_hook(text, limit=None):
    """Укоротить хук до лимита, отрезая по границе части предложения.

    Слова берутся только из самого факта, ничего не дописывается — то есть
    гарантия «сборщик не выдумывает» не нарушается. Если укоротить нечем,
    возвращаем как есть: превышение честнее подрезанной бессмыслицы.
    """
    limit = LIMITS[0][1] if limit is None else limit
    if seconds(text) <= limit:
        return text
    parts = re.split(r"\s*[,;—–-]\s+", text)
    best = ""
    for part in parts:
        candidate = (best + ", " + part) if best else part
        if seconds(candidate) > limit:
            break
        best = candidate
    return best if len(best.split()) >= 3 else text


def _with_source(line, source_id, need_source):
    if need_source and re.search(r"\d", line) and not re.search(r"\([^)]*\)", line):
        return f"{line} ({source_id})"
    return line


def render(data, canon):
    facts = data.get("facts", [])
    source = data.get("source", {})
    source_id = source.get("id", "источник")
    hook, body, action = pick(facts, source.get("title", ""))

    # заголовок начинается со слова «сценарий», поэтому строчная буква по п.2
    # обеспечена и без порчи имён собственных внутри названия статьи
    title = (source.get("title") or "рилз").strip()

    lines = [f"# сценарий: {title}", ""]
    lines += ["## хук (0–3 с)", "",
              _with_source(fit_hook(hook["text"].rstrip(".")), source_id,
                           lens.needs_number_source(canon)) + ".",
              ""]
    # Суть — речь, а не список. Маркированные пункты читаются как перечисление,
    # и заказчик такой текст переписывает: это провал теста на голос. Факты те
    # же и в том же порядке, меняется только форма подачи.
    lines += ["## суть (3–22 с)", ""]
    said = [_with_source(fact["text"].rstrip("."), source_id,
                         lens.needs_number_source(canon)) for fact in body]
    lines.append(". ".join(s[0].upper() + s[1:] if s else s for s in said) + ".")
    lines += ["", "## cta (22–30 с)", ""]
    cta = action["text"].rstrip(".") if action else FALLBACK_CTA
    # призыв к отправке добавляем, только если ролик остаётся в целевом коридоре:
    # сильный сигнал ранжирования не стоит того, чтобы вылезти за 20 секунд
    spent = seconds(" ".join(lines[2:]))
    if spent + seconds(cta + " " + CTA_SHARE) <= TARGET[1]:
        cta = cta + ". " + CTA_SHARE
    lines += [cta + ".", ""]
    used = [hook["id"]] + [f["id"] for f in body] + ([action["id"]] if action else [])
    lines += ["## использованные факты", "", ", ".join(used), ""]

    script = "\n".join(lines)
    return script, used, (action is None)


USED_SECTION = re.compile(r"\n## использованные факты.*", re.S)


def spoken(script, source_id=""):
    """Только произносимый текст: без заголовков с тайм-кодами, без списка
    id фактов и без служебной пометки источника. На нём и меряется, не
    добавил ли сборщик числа от себя."""
    text = USED_SECTION.sub("", script)
    text = "\n".join(l for l in text.split("\n") if not l.startswith("#"))
    if source_id:
        text = text.replace(f"({source_id})", "")
    return text


def outside_source(script, facts, source_id=""):
    """Числа в сценарии, которых нет ни в одном факте."""
    haystack = " ".join(
        (f.get("text", "") + " " + str(f.get("value") or "") + " " + f.get("quote", ""))
        for f in facts)
    known = set(re.findall(r"\d+", haystack))
    return [n for n in re.findall(r"\d+", spoken(script, source_id)) if n not in known]


def source_violations(facts, canon):
    """Нарушения канона в исходнике — по дословным цитатам фактов."""
    quotes = "\n\n".join(f.get("quote", "") for f in facts if f.get("quote"))
    return lens.check(quotes, canon, document_level=False)


def timing(script):
    """Секунды речи по блокам. Возвращает [(блок, секунды, лимит)]."""
    blocks, current = {}, None
    for line in USED_SECTION.sub("", script).split("\n"):
        if line.startswith("## "):
            current = line[3:].split("(")[0].strip()
            blocks[current] = []
        elif line.strip() and current and not line.startswith("#"):
            blocks[current].append(line.lstrip("- ").strip())
    return [(name, seconds(" ".join(blocks.get(name, []))), limit)
            for name, limit in LIMITS]


def report(data, canon, script=None, used=None, refusal=None, template_cta=False,
           source_text=None, extractor=""):
    facts = data.get("facts", [])
    source_id = data.get("source", {}).get("id", "")
    out = ["# отчёт", ""]

    where = "по всей статье" if source_text else "по цитатам отобранных фактов"
    out += [f"## нарушения канона в исходнике ({where})", ""]
    src = (lens.check(source_text, canon, document_level=False)
           if source_text else source_violations(facts, canon))
    if src:
        for i, v in enumerate(src, 1):
            out.append(f"{i}. п.{v.point} {v.message} — «{v.quote}»")
    else:
        out.append("нет")
    out.append("")

    out += ["## факты вне источника", ""]
    stray = outside_source(script, facts, source_id) if script else []
    out.append("нет" if not stray else "числа, которых нет в фактах: " + ", ".join(stray))
    out.append("")

    if script is not None:
        out += ["## хронометраж", ""]
        total = 0.0
        for name, secs, limit in timing(script):
            total += secs
            mark = "" if secs <= limit else f" — превышение, лимит {limit} с"
            out.append(f"- {name}: {secs} с{mark}")
        total = round(total, 1)
        low, high = TARGET
        if total < low:
            fit = f" — короче целевого коридора {low}–{high} с"
        elif total > high:
            fit = f" — длиннее целевого коридора {low}–{high} с"
        else:
            fit = f" — в целевом коридоре {low}–{high} с"
        out.append(f"- всего: {total} с{fit}, при темпе {WORDS_PER_SEC} слова в секунду")
        out.append("")

        out += ["## самопроверка сценария", ""]
        own = lens.check(USED_SECTION.sub("", script), canon)
        if own:
            for v in own:
                out.append(f"- п.{v.point} {v.message} — «{v.quote}»")
        else:
            out.append(f"канон пройден, {len(used)} фактов использовано")
        out.append(f"- движок канона: {lens.ENGINE}"
                   + (f" · добытчик фактов: {extractor}" if extractor else ""))
        if template_cta:
            out.append("- CTA шаблонный: в сырье нет факта с kind=action")
        out.append("")

    if lens.unparsed(canon):
        out += ["## пункты канона, которые парсер не понял", ""]
        for num, item in lens.unparsed(canon):
            out.append(f"- п.{num}: {item[:90]}")
        out.append("")

    out += ["## решение", ""]
    out.append("годится" if script is not None else f"контента нет — {refusal}")
    out.append("")
    return "\n".join(out)
