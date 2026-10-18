"""Оркестратор конвейера: один вход → canon-lens + judge → единый отчёт.

Импортирует соседние модули из дерева репозитория (canon-lens, judge). Если их
нет рядом — понятная ошибка. judge по умолчанию live (claude CLI); можно
отключить или взять оффлайн-вердикт.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .merge import merge_reports


class PipelineError(RuntimeError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_canon_lens(text: str, canon_path: str | Path) -> dict:
    cl = _repo_root() / "canon-lens"
    if not cl.exists():
        raise PipelineError("canon-lens не найден рядом — механический слой недоступен")
    sys.path.insert(0, str(cl))
    from canon_lens.rules import load_canon        # type: ignore
    from canon_lens.check import check_text, summary  # type: ignore
    canon = load_canon(canon_path)
    vs = [v.as_dict() for v in check_text(text, canon)]
    return {"violations": vs, "summary": summary([])}  # summary пересоберёт report


def _run_judge(text: str, canon_path: str | Path, file: str, mode: str) -> dict:
    if mode == "off":
        return {"violations": []}
    jd = _repo_root() / "judge"
    if not jd.exists():
        raise PipelineError("judge не найден рядом — смысловой слой недоступен")
    sys.path.insert(0, str(jd))
    from judge.judge import judge_text             # type: ignore
    offline = file if mode == "offline" else None
    vs = [v.as_dict() for v in judge_text(text, canon_path, offline_source=offline)]
    return {"violations": vs}


def run(file: str | Path, canon_path: str | Path, *, judge_mode: str = "live") -> tuple[dict, str]:
    """Прогнать вход через весь конвейер. judge_mode: live | offline | off.
    Возвращает (единый_отчёт, исходный_текст)."""
    text = Path(file).read_text(encoding="utf-8")
    parts = [_run_canon_lens(text, canon_path),
             _run_judge(text, canon_path, str(file), judge_mode)]
    rep = merge_reports(parts, file=str(file))
    return rep, text
