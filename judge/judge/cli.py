"""CLI: judge check <файл> [--canon canon.md] [--json] [--offline] [--llm-cmd claude]

Выход:
  человекочитаемо — смысловые нарушения, сгруппированные по пунктам канона;
  --json          — {file, summary, violations[]} — тот же контракт, что у
                    canon-lens, чтобы report/ смёржил механику и суждения.
Код возврата: 1 если есть нарушения severity=error, иначе 0.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .judge import judge_text, summary

DEFAULT_CANON = Path(__file__).resolve().parent.parent.parent / "canon-lens" / "canon.md"


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):             # Windows: не падать на кириллице
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
    p = argparse.ArgumentParser(prog="judge", description="смысловая проверка текста против канона (LLM)")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="судить файл против канона")
    c.add_argument("file", help="текстовый файл для проверки")
    c.add_argument("--canon", default=str(DEFAULT_CANON),
                   help=f"канон (по умолчанию {DEFAULT_CANON})")
    c.add_argument("--json", action="store_true", help="выдать JSON-контракт")
    c.add_argument("--offline", action="store_true",
                   help="не звать LLM: взять вердикт из <файл>.judge.json")
    c.add_argument("--llm-cmd", default="claude", help="команда LLM-CLI (деф. claude)")
    c.add_argument("--timeout", type=int, default=120, help="таймаут LLM, сек")
    a = p.parse_args(argv)

    if a.cmd != "check":
        return 2

    text = Path(a.file).read_text(encoding="utf-8")
    vs = judge_text(
        text, a.canon,
        offline_source=a.file if a.offline else None,
        llm_cmd=a.llm_cmd, timeout=a.timeout,
    )
    if a.json:
        print(json.dumps(
            {"file": a.file, "summary": summary(vs), "violations": [v.as_dict() for v in vs]},
            ensure_ascii=False, indent=2))
    else:
        _pretty(a.file, vs)
    return 1 if any(v.severity == "error" for v in vs) else 0


def _pretty(fname: str, vs) -> None:
    if not vs:
        print(f"{fname}: смысловых нарушений канона не найдено")
        return
    s = summary(vs)
    print(f"{fname}: {s['total']} смысловых нарушений "
          f"({s['errors']} error, {s['warnings']} warning)\n")
    by_pt: dict[int, list] = {}
    for v in vs:
        by_pt.setdefault(v.point, []).append(v)
    for pt in sorted(by_pt):
        head = f"п.{pt} канона" if pt else "вне нумерации"
        print(f"── {head} (судья) ──")
        for v in by_pt[pt]:
            mark = "✗" if v.severity == "error" else "•"
            conf = f" [{v.confidence:.2f}]" if v.confidence is not None else ""
            loc = f"{v.line}:{v.col}" if v.offset != [0, 0] else "весь текст"
            print(f"  {mark} {loc}\t«{v.quote}»{conf}\t{v.message}")
            if v.fix:
                print(f"       → {v.fix}")
        print()


if __name__ == "__main__":
    sys.exit(main())
