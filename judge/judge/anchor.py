"""Якорение цитаты судьи в offset — детерминированно, как у canon-lens.

LLM возвращает дословную цитату, но не смещение. Здесь цитата ищется в тексте
и превращается в [start, end) + line/col. Устойчивость к мелкому дрейфу:
1) точное вхождение; 2) вхождение при схлопнутых пробелах. Не найдено —
запись уровня документа (offset=[0,0]), находка не теряется.
"""
from __future__ import annotations

import re


def line_col(text: str, pos: int) -> tuple[int, int]:
    head = text[:pos]
    return head.count("\n") + 1, pos - (head.rfind("\n") + 1) + 1


def _find_exact(text: str, quote: str, start_at: int) -> tuple[int, int] | None:
    i = text.find(quote, start_at)
    if i < 0 and start_at:                      # не нашли после курсора — с начала
        i = text.find(quote)
    return (i, i + len(quote)) if i >= 0 else None


def _find_loose(text: str, quote: str) -> tuple[int, int] | None:
    """Схлопываем любые пробелы/переводы строк в цитате в \\s+ и ищем регэкспом."""
    q = quote.strip()
    if not q:
        return None
    parts = [re.escape(p) for p in q.split()]
    if not parts:
        return None
    rx = re.compile(r"\s+".join(parts))
    m = rx.search(text)
    return (m.start(), m.end()) if m else None


def anchor(text: str, quote: str, cursor: int = 0) -> tuple[int, int, bool]:
    """Вернуть (start, end, anchored). anchored=False → место не найдено."""
    q = (quote or "").strip()
    if not q:
        return 0, 0, False
    span = _find_exact(text, q, cursor) or _find_loose(text, q)
    if span:
        return span[0], span[1], True
    return 0, 0, False
