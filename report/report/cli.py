"""CLI: report merge <out1.json> <out2.json> ... [--json]

Читает JSON-выходы модулей (`canon-lens check --json`, `judge check --json`),
мёржит в один отчёт. Человекочитаемо — по пунктам канона с пометкой источника;
`--json` — единый контракт {file, summary, violations[]}.
Код возврата: 1 если есть severity=error, иначе 0.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pathlib import Path

from .merge import merge_reports
from . import render as R

_KIND_MARK = {
    "mechanical": "механика",
    "judgment": "судья",
    "judgment-literal": "механика",
    "redaction": "редакция",
}


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
    p = argparse.ArgumentParser(prog="report", description="единый отчёт из находок модулей")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge", help="слить JSON-выходы модулей в один отчёт")
    m.add_argument("inputs", nargs="+", help="файлы JSON-выходов (canon-lens/judge)")
    m.add_argument("--json", action="store_true", help="выдать единый JSON-контракт")

    r = sub.add_parser("run", help="прогнать файл через весь конвейер и показать отчёт")
    r.add_argument("file", help="входной текст (черновик)")
    r.add_argument("--canon", default=None, help="канон (деф. canon-lens/canon.md)")
    r.add_argument("--judge", choices=["live", "offline", "off"], default="live",
                   help="смысловой слой: live (claude) | offline (фикстура) | off")
    r.add_argument("--json", action="store_true", help="единый JSON-контракт")
    r.add_argument("--html", metavar="FILE", help="сохранить HTML-отчёт в файл")
    a = p.parse_args(argv)

    if a.cmd == "merge":
        reports = [json.loads(Path(f).read_text(encoding="utf-8")) for f in a.inputs]
        rep = merge_reports(reports)
        if a.json:
            print(json.dumps(rep, ensure_ascii=False, indent=2))
        else:
            print(R.render(rep))
        return 1 if any(v.get("severity") == "error" for v in rep["violations"]) else 0

    if a.cmd == "run":
        from .pipeline import run as pipe_run, PipelineError
        canon = a.canon or str(Path(__file__).resolve().parents[2] / "canon-lens" / "canon.md")
        try:
            rep, text = pipe_run(a.file, canon, judge_mode=a.judge)
        except PipelineError as e:
            print(f"ошибка конвейера: {e}", file=sys.stderr)
            return 2
        if a.html:
            Path(a.html).write_text(R.render_html(rep, text), encoding="utf-8")
            print(f"HTML-отчёт: {a.html}", file=sys.stderr)
        if a.json:
            print(json.dumps(rep, ensure_ascii=False, indent=2))
        else:
            R.enable_windows_ansi()
            print(R.render(rep, text))
        return 1 if any(v.get("severity") == "error" for v in rep["violations"]) else 0

    return 2


def _pretty(rep: dict) -> None:
    vs = rep["violations"]
    s = rep["summary"]
    if not vs:
        print(f"{rep['file']}: нарушений не найдено")
        return
    kinds = ", ".join(f"{k}: {n}" for k, n in sorted(s["by_kind"].items()))
    print(f"{rep['file']}: {s['total']} нарушений "
          f"({s['errors']} error, {s['warnings']} warning)  [{kinds}]\n")
    by_pt: dict[int, list] = {}
    for v in vs:
        by_pt.setdefault(v.get("point", 0), []).append(v)
    for pt in sorted(by_pt):
        head = f"п.{pt} канона" if pt else "редакция (безопасность публикации)"
        print(f"── {head} ──")
        for v in by_pt[pt]:
            mark = "✗" if v.get("severity") == "error" else "•"
            src = _KIND_MARK.get(v.get("kind", "mechanical"), v.get("kind", ""))
            off = v.get("offset", [0, 0])
            loc = f"{v.get('line', 1)}:{v.get('col', 1)}" if off != [0, 0] else "весь текст"
            print(f"  {mark} [{src}] {loc}\t«{v.get('quote', '')}»\t{v.get('message', '')}")
            if v.get("fix"):
                print(f"       → {v['fix']}")
        print()


if __name__ == "__main__":
    sys.exit(main())
