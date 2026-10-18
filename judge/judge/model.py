"""Форма записи нарушения — идентична canon-lens (CONTRACTS.md §2).

judge выдаёт объекты этой же формы с `kind = "judgment"`. Контракт стабилен:
`rule`, `point`, `offset`, `quote`, `severity` не меняются; новые поля — только
опциональные. Дублируется здесь намеренно: папка модуля изолирована, без
зависимости от canon-lens.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field


@dataclass
class Violation:
    rule: str             # id правила канона
    point: int            # пункт канона (0 = вне нумерации)
    category: str         # canon | redaction
    severity: str         # error | warning
    kind: str             # judgment | judgment-literal | mechanical | redaction
    line: int             # 1-based
    col: int              # 1-based
    end_col: int
    offset: list[int]     # [start, end) абсолютный сдвиг в тексте
    quote: str
    message: str
    fix: str = ""
    confidence: float | None = None   # опц.: уверенность судьи 0..1 (новое поле, доп. к контракту)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Finding:
    """Сырьё от LLM до якорения в offset — не часть контракта наружу."""
    rule_id: str
    quote: str
    reason: str = ""
    fix: str = ""
    confidence: float | None = None
