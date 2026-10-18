"""judge — смысловая проверка текста против канона через LLM.

Добирает то, что детерминированный canon-lens ловит только буквально:
правила с `judgment_extends = true` (вариации) и чисто смысловые правила
(`kind = "judgment"`). Выход — объекты той же формы `Violation`, что и у
canon-lens (`kind = "judgment"`), чтобы `report/` мог смёржить находки по
`offset`, а `lens/` — подсветить спаны.
"""
from .model import Violation
from .judge import judge_text, summary

__all__ = ["Violation", "judge_text", "summary"]
