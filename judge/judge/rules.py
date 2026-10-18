"""Загрузчик канона для judge — берёт только то, что нужно судье.

Канон — тот же файл, что у canon-lens: markdown с одним ```toml``` блоком
(CONTRACTS.md §1). judge отбирает СУДЕЙСКИЕ правила:

  1. `judgment_extends = true` — буквальную форму уже поймал canon-lens,
     judge добирает смысловые вариации;
  2. `kind = "judgment"` — чисто смысловое правило, буквального аналога нет
     (canon-lens такой kind не знает и молча пропускает).

Правило несёт человекочитаемое описание для промпта судьи. Механические поля
(patterns/stems/phrases) переносятся как «уже покрыто буквально» — подсказка
модели не дублировать буквальные попадания.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_TOML_FENCE = re.compile(r"```toml\s*\n(.*?)\n```", re.DOTALL)


@dataclass
class JudgeRule:
    id: str
    point: int
    kind: str
    severity: str = "error"
    category: str = "canon"
    message: str = ""
    fix: str = ""
    judgment_extends: bool = False
    note: str = ""
    # буквальные маркеры — чтобы судья не повторял то, что уже поймано механически
    literal_markers: list[str] = field(default_factory=list)


def _literal_markers(d: dict) -> list[str]:
    out: list[str] = []
    for key in ("patterns", "stems", "phrases", "forms"):
        out.extend(str(x) for x in d.get(key, []))
    return out


def load_judge_rules(path: str | Path) -> tuple[dict, list[JudgeRule]]:
    """Вернуть (meta, судейские правила). Пусто — судить нечего."""
    text = Path(path).read_text(encoding="utf-8")
    m = _TOML_FENCE.search(text)
    if not m:
        # прозаический канон (examples/canon.md) — судейских флагов там нет,
        # judge на нём осознанно ничего не делает: буквальное покрывает canon-lens.
        return {"source": "prose", "note": "нет toml-блока — судейских правил нет"}, []
    data = tomllib.loads(m.group(1))
    rules: list[JudgeRule] = []
    for d in data.get("rule", []):
        is_judge = bool(d.get("judgment_extends")) or d.get("kind") == "judgment"
        if not is_judge:
            continue
        rules.append(JudgeRule(
            id=d["id"], point=int(d.get("point", 0)), kind=d["kind"],
            severity=d.get("severity", "error"), category=d.get("category", "canon"),
            message=d.get("message", ""), fix=d.get("fix", ""),
            judgment_extends=bool(d.get("judgment_extends", False)),
            note=d.get("note", ""),
            literal_markers=_literal_markers(d),
        ))
    return data.get("meta", {}), rules
