"""Красивый терминальный рендер единого отчёта. Только stdlib (ANSI).

Цвет отключается сам, если вывод не в терминал или задан NO_COLOR. Показывает:
рамку-заголовок, сводку с цветными счётчиками, находки по пунктам канона с
меткой источника (механика/судья/редакция) и строкой контекста, где нарушенный
спан подсвечен.
"""
from __future__ import annotations

import os
import sys

_USE = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str) -> str:
    return code if _USE else ""


RESET = _c("\033[0m")
BOLD = _c("\033[1m")
DIM = _c("\033[2m")
RED = _c("\033[31m")
YEL = _c("\033[33m")
GRN = _c("\033[32m")
CYA = _c("\033[36m")
MAG = _c("\033[35m")
INV = _c("\033[7m")

_SRC = {
    "mechanical": ("механика", CYA),
    "judgment-literal": ("механика", CYA),
    "judgment": ("судья", MAG),
    "redaction": ("редакция", YEL),
}


def enable_windows_ansi() -> None:
    """Включить обработку ANSI в старых консолях Windows (Win10+)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.SetConsoleMode(k.GetStdHandle(-11), 7)   # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass


def _box(title: str) -> str:
    line = "─" * (len(title) + 2)
    return f"{BOLD}╭{line}╮\n│ {title} │\n╰{line}╯{RESET}"


def _context(text: str, off: list[int]) -> str | None:
    """Строка текста вокруг спана с подсветкой нарушенного фрагмента."""
    if not text or off == [0, 0]:
        return None
    start, end = off
    ls = text.rfind("\n", 0, start) + 1
    le = text.find("\n", end)
    le = len(text) if le < 0 else le
    before, span, after = text[ls:start], text[start:end], text[end:le]
    before = ("…" + before[-40:]) if len(before) > 40 else before
    after = (after[:40] + "…") if len(after) > 40 else after
    return f"    {DIM}{before}{RESET}{INV}{RED}{span}{RESET}{DIM}{after}{RESET}"


def render(rep: dict, text: str | None = None) -> str:
    vs = rep.get("violations", [])
    s = rep.get("summary", {})
    out = [_box(f"отчёт по канону · {rep.get('file', '')}")]

    if not vs:
        out.append(f"\n{GRN}{BOLD}✓ нарушений не найдено — чисто{RESET}\n")
        return "\n".join(out)

    err, warn = s.get("errors", 0), s.get("warnings", 0)
    ec = RED if err else GRN
    parts = [f"{ec}{err} error{RESET}", f"{YEL}{warn} warning{RESET}"]
    agg: dict[str, list] = {}
    for k, n in s.get("by_kind", {}).items():
        label, col = _SRC.get(k, (k, ""))
        cur = agg.setdefault(label, [0, col])
        cur[0] += n
    bk_txt = "  ".join(f"{col}{label}:{n}{RESET}" for label, (n, col) in sorted(agg.items()))
    out.append(f"\n{BOLD}{s.get('total', 0)} нарушений{RESET}  ({', '.join(parts)})   {bk_txt}\n")

    by_pt: dict[int, list] = {}
    for v in vs:
        by_pt.setdefault(v.get("point", 0), []).append(v)
    for pt in sorted(by_pt):
        head = f"пункт {pt} канона" if pt else "редакция (безопасность публикации)"
        out.append(f"{BOLD}▸ {head}{RESET}")
        for v in by_pt[pt]:
            sev = v.get("severity")
            mark = f"{RED}✗{RESET}" if sev == "error" else f"{YEL}•{RESET}"
            label, col = _SRC.get(v.get("kind", "mechanical"), ("?", ""))
            off = v.get("offset", [0, 0])
            loc = f"{v.get('line', 1)}:{v.get('col', 1)}" if off != [0, 0] else "весь текст"
            conf = v.get("confidence")
            conf_s = f" {DIM}[{conf:.0%}]{RESET}" if isinstance(conf, (int, float)) else ""
            out.append(f"  {mark} {col}{label}{RESET} {DIM}{loc}{RESET}  "
                       f"{v.get('message', '')}{conf_s}")
            ctx = _context(text, off) if text else None
            if ctx:
                out.append(ctx)
            elif v.get("quote"):
                out.append(f"    {DIM}«{v['quote']}»{RESET}")
            if v.get("fix"):
                out.append(f"    {GRN}→ {v['fix']}{RESET}")
        out.append("")
    verdict = (f"{RED}{BOLD}✗ есть ошибки канона — публиковать нельзя{RESET}" if err
               else f"{GRN}{BOLD}✓ ошибок нет{RESET}")
    out.append(verdict)
    return "\n".join(out)


# ── HTML ──────────────────────────────────────────────────────────────

def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


_HTML_SRC = {"mechanical": "механика", "judgment-literal": "механика",
             "judgment": "судья", "redaction": "редакция"}


def render_html(rep: dict, text: str | None = None) -> str:
    vs = rep.get("violations", [])
    s = rep.get("summary", {})
    err = s.get("errors", 0)
    rows = []
    by_pt: dict[int, list] = {}
    for v in vs:
        by_pt.setdefault(v.get("point", 0), []).append(v)
    for pt in sorted(by_pt):
        head = f"пункт {pt} канона" if pt else "редакция (безопасность публикации)"
        rows.append(f'<h2>{_esc(head)}</h2>')
        for v in by_pt[pt]:
            sev = v.get("severity", "")
            src = _HTML_SRC.get(v.get("kind", "mechanical"), v.get("kind", ""))
            off = v.get("offset", [0, 0])
            loc = f'{v.get("line",1)}:{v.get("col",1)}' if off != [0, 0] else "весь текст"
            conf = v.get("confidence")
            conf_s = f' <span class="conf">{conf:.0%}</span>' if isinstance(conf, (int, float)) else ""
            fix = f'<div class="fix">→ {_esc(v.get("fix",""))}</div>' if v.get("fix") else ""
            rows.append(
                f'<div class="v {sev}">'
                f'<span class="src {v.get("kind","")}">{src}</span>'
                f'<span class="loc">{loc}</span>'
                f'<span class="msg">{_esc(v.get("message",""))}{conf_s}</span>'
                f'<div class="quote">«{_esc(v.get("quote",""))}»</div>{fix}</div>')
    verdict = ('<p class="bad">✗ есть ошибки канона — публиковать нельзя</p>' if err
               else '<p class="ok">✓ ошибок нет</p>')
    body = "\n".join(rows) if vs else '<p class="ok">✓ нарушений не найдено — чисто</p>'
    agg: dict[str, int] = {}
    for k, n in s.get("by_kind", {}).items():
        agg[_HTML_SRC.get(k, k)] = agg.get(_HTML_SRC.get(k, k), 0) + n
    bk = "  ·  ".join(f"{label}: {n}" for label, n in sorted(agg.items()))
    return f"""<!doctype html><html lang="ru"><meta charset="utf-8">
<title>отчёт по канону · {_esc(rep.get('file',''))}</title>
<style>
:root{{color-scheme:dark}}
body{{background:#0d1117;color:#c9d1d9;font:15px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;max-width:820px;margin:2rem auto;padding:0 1rem}}
h1{{font-size:1.1rem;border-bottom:1px solid #30363d;padding-bottom:.5rem}}
h2{{font-size:.95rem;color:#8b949e;margin:1.4rem 0 .5rem}}
.sum{{color:#8b949e;margin:.5rem 0 1rem}}
.sum b{{color:#c9d1d9}}
.v{{border-left:3px solid #30363d;padding:.5rem .8rem;margin:.4rem 0;background:#161b22;border-radius:0 6px 6px 0}}
.v.error{{border-color:#f85149}} .v.warning{{border-color:#d29922}}
.src{{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;padding:.1rem .4rem;border-radius:4px;background:#21262d;margin-right:.5rem}}
.src.judgment{{color:#d2a8ff}} .src.mechanical,.src.judgment-literal{{color:#79c0ff}} .src.redaction{{color:#e3b341}}
.loc{{color:#6e7681;font-size:.8rem;margin-right:.5rem}}
.quote{{color:#8b949e;font-style:italic;margin-top:.3rem}}
.fix{{color:#3fb950;margin-top:.2rem}}
.conf{{color:#6e7681;font-size:.8rem}}
.ok{{color:#3fb950;font-weight:600}} .bad{{color:#f85149;font-weight:600}}
</style>
<h1>отчёт по канону · {_esc(rep.get('file',''))}</h1>
<p class="sum"><b>{s.get('total',0)} нарушений</b> · {err} error · {s.get('warnings',0)} warning · {_esc(bk)}</p>
{body}
{verdict}
</html>"""
