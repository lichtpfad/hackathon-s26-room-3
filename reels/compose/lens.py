"""Адаптер к движку канона.

Комната сделала `canon-lens/` (HA59) — правила в TOML, богаче нашего парсера,
и это правильный общий движок. Но он импортирует `tomllib`, который появился
только в Python 3.11, а на машине сборщика 3.10 — модуль не поднимается вовсе.

Поэтому здесь развилка: если `canon_lens` импортируется, работаем через него;
если нет — падаем на собственный парсер прозаического canon.md, чтобы
конвейер рилзов не вставал. Какой движок сработал, видно в отчёте.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LENS_DIR = os.path.join(_ROOT, "canon-lens")

ENGINE = "fallback"
try:
    if _LENS_DIR not in sys.path:
        sys.path.insert(0, _LENS_DIR)
    from canon_lens import load_canon as _load_canon, check_text as _check_text
    ENGINE = "canon-lens"
except Exception:  # нет tomllib на 3.10, нет папки, сломанный канон
    from . import canon as _own

# виды правил, которые нельзя предъявлять исходнику: они про форму документа,
# а исходник мы видим только обрывками цитат
_DOC_LEVEL = {
    "headline_case", "paragraph_max_lines", "doc_max_chars", "number_without_source",
    "require_present", "require_in_lead", "keyword_min_count", "count_range",
}
_OWN_DOC_LEVEL = ("headings", "length", "cta", "source")


class Finding:
    """Общая форма находки для отчёта, независимая от движка."""

    __slots__ = ("point", "message", "quote")

    def __init__(self, point, message, quote):
        self.point, self.message, self.quote = point, message, quote


class CanonUnreadable(RuntimeError):
    """Канон есть, но этим движком его прочитать нельзя."""


def load(path):
    if ENGINE == "canon-lens":
        return _load_canon(path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    # TOML-канон запасной парсер не понимает и молча вернул бы ноль правил —
    # то есть «канон пройден» на любом тексте. Лучше остановиться громко.
    if "```toml" in text:
        raise CanonUnreadable(
            f"{path} — канон в TOML, для него нужен canon-lens и Python 3.11+ "
            f"(здесь {sys.version_info.major}.{sys.version_info.minor}, нет tomllib)")
    canon = _own.parse(text)
    if not (canon.banned_words or canon.rule_no):
        raise CanonUnreadable(f"{path} — не распознано ни одного правила")
    return canon


def needs_number_source(canon):
    if ENGINE == "canon-lens":
        return any(r.kind == "number_without_source" for r in canon.rules)
    return canon.numbers_need_source


def unparsed(canon):
    return [] if ENGINE == "canon-lens" else canon.unparsed


def check(text, canon, document_level=True):
    """Нарушения канона в тексте. document_level=False — только правила,
    применимые к обрывку (запрещённые слова, эмодзи, антитезы, канцелярит)."""
    if ENGINE == "canon-lens":
        out = []
        by_id = {r.id: r for r in canon.rules}
        for v in _check_text(text, canon):
            rule = by_id.get(v.rule)
            if not document_level and rule is not None and rule.kind in _DOC_LEVEL:
                continue
            out.append(Finding(v.point, v.message, v.quote))
        return out
    skip = () if document_level else _OWN_DOC_LEVEL
    return [Finding(num, what, place) for num, what, place in _own.check(text, canon, skip=skip)]
