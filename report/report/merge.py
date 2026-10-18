"""Мёрж находок из нескольких выходов `--json` (canon-lens, judge) в один отчёт.

Каждый вход — dict `{file, summary?, violations[]}` (контракт CONTRACTS.md §2).
Находки объединяются, дедуплицируются по (rule, offset[start], offset[end]),
сортируются по месту в тексте. Итоговый summary добавляет разбивку по `kind`.
"""
from __future__ import annotations


def _viol_key(v: dict) -> tuple:
    off = v.get("offset", [0, 0])
    return (v.get("rule", ""), off[0], off[1])


def _sort_key(v: dict) -> tuple:
    off = v.get("offset", [0, 0])
    return (off[0], off[1], v.get("point", 0), v.get("rule", ""))


def merge_reports(reports: list[dict], file: str | None = None) -> dict:
    """Слить несколько `{violations[]}` в один отчёт `{file, summary, violations[]}`."""
    all_v: list[dict] = []
    for r in reports:
        all_v.extend(r.get("violations", []))
    all_v.sort(key=_sort_key)

    seen: set[tuple] = set()
    uniq: list[dict] = []
    for v in all_v:
        k = _viol_key(v)
        if k not in seen:
            seen.add(k)
            uniq.append(v)

    if file is None:
        for r in reports:                       # первый непустой file из входов
            if r.get("file"):
                file = r["file"]
                break
    return {"file": file or "", "summary": summary(uniq), "violations": uniq}


def summary(violations: list[dict]) -> dict:
    errs = sum(1 for v in violations if v.get("severity") == "error")
    by_kind: dict[str, int] = {}
    for v in violations:
        k = v.get("kind", "mechanical")
        by_kind[k] = by_kind.get(k, 0) + 1
    return {
        "total": len(violations),
        "errors": errs,
        "warnings": len(violations) - errs,
        "points": sorted({v.get("point", 0) for v in violations}),
        "by_kind": by_kind,
        "clean": errs == 0,
    }
