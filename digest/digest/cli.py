"""CLI: digest make <файл-заметок> [--offline] [--llm-cmd claude] [--check]

Печатает дайджест в stdout. `--offline` берёт <файл>.digest.md (детерминированно).
`--check` дополнительно прогоняет результат через canon-lens (если модуль рядом)
и печатает число нарушений в stderr — self-check порождённого контента.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import make_digest


def _self_check(text: str) -> str | None:
    """Прогнать дайджест через canon-lens по канону дайджеста. None — недоступен."""
    root = Path(__file__).resolve().parents[2]
    cl = root / "canon-lens"
    digest_canon = Path(__file__).resolve().parents[1] / "canon.digest.md"
    if not cl.exists() or not digest_canon.exists():
        return None
    sys.path.insert(0, str(cl))
    try:
        from canon_lens.rules import load_canon      # type: ignore
        from canon_lens.check import check_text, summary   # type: ignore
    except Exception:
        return None
    canon = load_canon(digest_canon)
    vs = check_text(text, canon)
    s = summary(vs)
    return f"self-check ({digest_canon.name}): {s['total']} нарушений ({s['errors']} error)"


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
    p = argparse.ArgumentParser(prog="digest", description="дайджест недели из заметок по канону")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make", help="сделать дайджест из файла заметок")
    m.add_argument("file", help="файл сырых заметок")
    m.add_argument("--offline", action="store_true", help="взять <файл>.digest.md, не звать LLM")
    m.add_argument("--llm-cmd", default="claude", help="команда LLM-CLI (деф. claude)")
    m.add_argument("--timeout", type=int, default=180, help="таймаут LLM, сек")
    m.add_argument("--check", action="store_true", help="self-check результата через canon-lens")
    a = p.parse_args(argv)

    if a.cmd != "make":
        return 2

    notes = Path(a.file).read_text(encoding="utf-8")
    out = make_digest(notes, offline_source=a.file if a.offline else None,
                      llm_cmd=a.llm_cmd, timeout=a.timeout)
    print(out)
    if a.check:
        res = _self_check(out)
        print(res or "self-check: canon-lens недоступен", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
