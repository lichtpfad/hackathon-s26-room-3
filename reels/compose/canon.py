"""Разбор canon.md в набор проверок.

Канон меняется без правки кода: правила читаются из файла. Разбирается
нумерованный список — каждый пункт распознаётся по ключевым словам, а списки
запрещённых слов берутся из кавычек «...» самого пункта. Добавить слово в
запреты, поменять лимит длины или снять правило — правка canon.md.

Чего парсер НЕ умеет: правило, сформулированное принципиально по-новому
(«запрещены вопросы в заголовке»), он не подхватит — распознаются восемь
известных видов. Нераспознанные пункты возвращаются в `unparsed`, чтобы это
было видно, а не молчало.
"""

import re

QUOTED = re.compile(r"[«\"]([^»\"]+)[»\"]")

# Обрезка слова до основы ловит однокоренные формы, но «данный» и «данные»
# — разные слова с общей основой, и второе нейтрально. Такие формы исключаем
# явно, иначе линтер объявляет нарушением обычное «данные по конверсии».
AMBIGUOUS = {"данные", "данных", "данными", "данным"}
EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF⬀-⯿️]"
)
ANTITHESIS = (
    re.compile(r"\bэто\s+не\s+[^,.;!?\n]{1,60}[—–-]\s*это\b", re.I),
    re.compile(r"\bне\s+(?:просто\s+)?[^,.;!?\n]{1,60}[,—–-]\s*а\s+\S", re.I),
)


class Canon:
    def __init__(self):
        self.no_emoji = False
        self.lowercase_headings = False
        self.no_antithesis = False
        self.banned_words = []
        self.max_paragraph_lines = None
        self.max_post_chars = None
        self.numbers_need_source = False
        self.cta_required = False
        self.banned_cta = []
        self.canceleritis = []
        self.rule_no = {}       # признак -> номер пункта в каноне
        self.unparsed = []      # пункты, которых парсер не понял

    def __repr__(self):
        return (f"Canon(banned={len(self.banned_words)}, "
                f"canceleritis={len(self.canceleritis)}, "
                f"post<= {self.max_post_chars}, unparsed={len(self.unparsed)})")


def parse(text):
    canon = Canon()
    for m in re.finditer(r"^\s*(\d+)\.\s+(.+?)(?=^\s*\d+\.\s|\Z)", text, re.M | re.S):
        num, item = int(m.group(1)), " ".join(m.group(2).split())
        low = item.lower()
        known = False

        if "эмодзи" in low:
            canon.no_emoji, canon.rule_no["emoji"] = True, num
            known = True
        if "заголовк" in low and "строчн" in low:
            canon.lowercase_headings, canon.rule_no["headings"] = True, num
            known = True
        if "антитез" in low:
            canon.no_antithesis, canon.rule_no["antithesis"] = True, num
            known = True
        if "запрещённые слова" in low or "запрещенные слова" in low:
            canon.banned_words = QUOTED.findall(item)
            canon.rule_no["banned"] = num
            known = True
        if "≤" in item or "<=" in item:
            par = re.search(r"абзац\s*[≤<=]+\s*(\d+)", low)
            post = re.search(r"пост\s*[≤<=]+\s*(\d+)", low)
            if par:
                canon.max_paragraph_lines = int(par.group(1))
            if post:
                canon.max_post_chars = int(post.group(1))
            canon.rule_no["length"] = num
            known = True
        if "числ" in low and "источник" in low:
            canon.numbers_need_source, canon.rule_no["source"] = True, num
            known = True
        if "cta" in low or "действие для читателя" in low:
            canon.cta_required, canon.rule_no["cta"] = True, num
            canon.banned_cta = [q.lower() for q in QUOTED.findall(item)]
            known = True
        if "канцелярит" in low:
            tail = item[low.index("канцелярит"):]
            canon.canceleritis = QUOTED.findall(tail)
            canon.rule_no["tone"] = num
            known = True

        if not known:
            canon.unparsed.append((num, item))
    return canon


def _where(text, span, width=60):
    a = max(0, span[0] - width // 2)
    return " ".join(text[a:span[1] + width // 2].split())


def check(text, canon, skip=()):
    """Вернуть список нарушений: (номер пункта, что, дословное место)."""
    out = []

    def add(key, what, place):
        if key not in skip:
            out.append((canon.rule_no.get(key, 0), what, place))

    if canon.no_emoji:
        for m in EMOJI.finditer(text):
            add("emoji", "эмодзи", _where(text, m.span()))

    if canon.lowercase_headings:
        for m in re.finditer(r"^#{1,6}\s+(\S)", text, re.M):
            ch = m.group(1)
            if ch.isalpha() and ch.upper() == ch:
                add("headings", "заголовок с заглавной", _where(text, m.span()))

    if canon.no_antithesis:
        for rx in ANTITHESIS:
            for m in rx.finditer(text):
                add("antithesis", "антитеза", _where(text, m.span()))

    def by_stem(words, key, label):
        for word in words:
            stem = word[:-2] if len(word) > 4 else word
            for m in re.finditer(r"\b" + re.escape(stem) + r"\w*", text, re.I):
                if m.group(0).lower() in AMBIGUOUS:
                    continue
                add(key, f"{label} «{word}»", _where(text, m.span()))
                break

    by_stem(canon.banned_words, "banned", "запрещённое слово")
    by_stem(canon.canceleritis, "tone", "канцелярит")

    if canon.max_paragraph_lines:
        for para in re.split(r"\n\s*\n", text):
            lines = [l for l in para.split("\n") if l.strip()]
            if len(lines) > canon.max_paragraph_lines:
                add("length", f"абзац из {len(lines)} строк", " ".join(lines[0].split())[:60])

    if canon.max_post_chars and len(text) > canon.max_post_chars:
        add("length", f"длина {len(text)} знаков", f"лимит {canon.max_post_chars}")

    for phrase in canon.banned_cta:
        if phrase in text.lower():
            add("cta", f"запрещённый CTA «{phrase}»", phrase)

    if canon.numbers_need_source:
        for line in text.split("\n"):
            if re.search(r"\d", line) and not re.search(r"\([^)]*\)", line):
                if not line.startswith("#") and line.strip():
                    add("source", "число без источника в скобках", " ".join(line.split())[:60])

    return out
