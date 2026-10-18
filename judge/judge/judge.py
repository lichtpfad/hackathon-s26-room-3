"""Ядро judge: канон → судейские правила → LLM/оффлайн находки → Violation.

Порядок:
1. отобрать судейские правила из канона (rules.load_judge_rules);
2. получить находки — LLM (`claude` CLI) или оффлайн-вердикт из фикстуры;
3. каждую находку привязать к offset (anchor) и собрать в Violation(kind=judgment);
4. отсортировать и дедуплицировать по (rule, offset) — как canon-lens.

Находка на несуществующее rule_id отбрасывается (модель не должна выдумывать
правила). Находка, чью цитату не удалось привязать, сохраняется записью уровня
документа (offset=[0,0]) — теряться не должна.
"""
from __future__ import annotations

from pathlib import Path

from .model import Violation, Finding
from .rules import JudgeRule, load_judge_rules
from .anchor import anchor, line_col
from .prompts import SYSTEM, build_prompt
from . import llm


def _to_findings(raw: list[dict]) -> list[Finding]:
    out: list[Finding] = []
    for d in raw:
        if not isinstance(d, dict) or not d.get("quote") or not d.get("rule_id"):
            continue
        conf = d.get("confidence")
        try:
            conf = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf = None
        out.append(Finding(
            rule_id=str(d["rule_id"]), quote=str(d["quote"]),
            reason=str(d.get("reason", "")), fix=str(d.get("fix", "")),
            confidence=conf,
        ))
    return out


def _violation(text: str, rule: JudgeRule, f: Finding) -> Violation:
    start, end, ok = anchor(text, f.quote)
    if ok:
        line, col = line_col(text, start)
        end_col = col + (end - start)
        quote = f.quote.strip() or f.quote
    else:                                   # не привязалось — запись уровня документа
        line, col, end_col = 1, 1, 1
        start, end = 0, 0
        quote = f.quote.strip() or f.quote
    msg = rule.message or rule.id
    if f.reason:
        msg = f"{msg}: {f.reason}"
    return Violation(
        rule=rule.id, point=rule.point, category=rule.category, severity=rule.severity,
        kind="judgment", line=line, col=col, end_col=end_col,
        offset=[start, end], quote=quote, message=msg,
        fix=f.fix or rule.fix, confidence=f.confidence,
    )


def judge_text(text: str, canon_path: str | Path, *,
               offline_source: str | Path | None = None,
               llm_cmd: str = "claude", timeout: int = 120) -> list[Violation]:
    """Судить текст. offline_source задан → берём вердикт из фикстуры, LLM не зовём."""
    _meta, rules = load_judge_rules(canon_path)
    if not rules:
        return []
    by_id = {r.id: r for r in rules}

    if offline_source is not None:
        raw = llm.findings_offline(offline_source)
    else:
        raw = llm.findings_via_llm(build_prompt(text, rules), SYSTEM, llm_cmd, timeout)

    violations: list[Violation] = []
    for f in _to_findings(raw):
        rule = by_id.get(f.rule_id)
        if rule is None:                    # модель выдумала правило — игнор
            continue
        violations.append(_violation(text, rule, f))

    violations.sort(key=lambda v: (v.offset[0], v.offset[1], v.point, v.rule))
    seen: set[tuple] = set()
    uniq: list[Violation] = []
    for v in violations:
        key = (v.rule, v.offset[0], v.offset[1])
        if key not in seen:
            seen.add(key)
            uniq.append(v)
    return uniq


def summary(violations: list[Violation]) -> dict:
    errs = sum(1 for v in violations if v.severity == "error")
    return {
        "total": len(violations),
        "errors": errs,
        "warnings": len(violations) - errs,
        "points": sorted({v.point for v in violations}),
        "clean": errs == 0,
    }
