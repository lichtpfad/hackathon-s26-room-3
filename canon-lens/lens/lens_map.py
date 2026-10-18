#!/usr/bin/env python3
"""lens/lens_map — визуальная карта нарушений канона (одна линза из fan-out).

Вход:  текстовый файл + нарушения — JSON от `canon-lens check --json` (--violations)
       ИЛИ канон-файл, тогда проверку запускаем сами (--canon).
Выход: один самодостаточный HTML: текст с подсвеченными спанами + панель правил
       по пунктам канона, клик по пункту подсвечивает место. Без внешних зависимостей.

    python canon-lens/lens/lens_map.py draft.md --canon canon-lens/canon.sostav.md -o map.html
    canon-lens check draft.md --json > v.json && python canon-lens/lens/lens_map.py draft.md --violations v.json
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))   # canon-lens/ → import canon_lens при --canon


def _collect(text_path: Path, args) -> dict:
    if args.violations:
        d = json.loads(Path(args.violations).read_text(encoding="utf-8"))
        d.setdefault("canon_points", sorted({v["point"] for v in d["violations"] if v["point"]}))
        d.setdefault("canon_name", "")
        return d
    from canon_lens.rules import load_canon
    from canon_lens.check import check_text, summary
    canon = load_canon(args.canon)
    vs = check_text(text_path.read_text(encoding="utf-8"), canon)
    return {"file": str(text_path), "summary": summary(vs),
            "violations": [v.as_dict() for v in vs],
            "canon_points": sorted({r.point for r in canon.rules if r.point}),
            "canon_name": canon.meta.get("name", Path(args.canon).name)}


def _vid(v: dict) -> str:
    return f'{v["rule"]}@{v["offset"][0]}-{v["offset"][1]}'


def _render_text(text: str, violations: list[dict]) -> str:
    inline = [v for v in violations if v["offset"][1] > v["offset"][0]]
    cuts = sorted({0, len(text)}
                  | {v["offset"][0] for v in inline}
                  | {v["offset"][1] for v in inline})
    out = []
    for a, b in zip(cuts, cuts[1:]):
        seg = html.escape(text[a:b])
        cover = [v for v in inline if v["offset"][0] <= a and v["offset"][1] >= b]
        if not cover:
            out.append(seg)
            continue
        if any(v["category"] == "redaction" for v in cover):
            cls = "cat-redaction"
        elif any(v["severity"] == "error" for v in cover):
            cls = "sev-error"
        else:
            cls = "sev-warning"
        vids = " ".join(_vid(v) for v in cover)
        tip = " · ".join(v["message"] for v in cover)
        out.append(f'<span class="v {cls}" data-vids="{html.escape(vids)}" '
                   f'title="{html.escape(tip)}">{seg}</span>')
    return "".join(out)


def _by_point(violations: list[dict]) -> dict[int, list]:
    d: dict[int, list] = {}
    for v in violations:
        d.setdefault(v["point"], []).append(v)
    return d


def _stat_tiles(s: dict, violated: int, total_pts: int) -> str:
    total_pts = total_pts or (violated or 1)
    rows = [
        ("error", s["errors"], "нельзя публиковать" if s["errors"] else "чисто"),
        ("warning", s["warnings"], "на проверку" if s["warnings"] else "чисто"),
        ("pts", f'{violated}<span class="of"> / {total_pts}</span>', "пунктов канона задето"),
    ]
    return "".join(
        f'<div class="tile t-{k}"><div class="n">{n}</div>'
        f'<div class="c">{html.escape(c)}</div></div>' for k, n, c in rows)


def _coverage(canon_pts: list, by_pt: dict) -> str:
    if not canon_pts:
        return ""
    cells = []
    for p in canon_pts:
        vs = by_pt.get(p, [])
        st = "ok" if not vs else ("err" if any(v["severity"] == "error" for v in vs) else "warn")
        lbl = "редакция" if p == 0 else f"п.{p}"
        note = "чисто" if st == "ok" else f"{len(vs)} наруш."
        cells.append(f'<span class="cell c-{st}" title="{html.escape(lbl + ": " + note)}">'
                     f'{"R" if p == 0 else p}</span>')
    return f'<div class="cov"><span class="cov-l">канон</span>{"".join(cells)}</div>'


def _render_panel(violations: list[dict]) -> str:
    if not violations:
        return '<p class="clean">черновик проходит канон — нарушений нет</p>'
    by_pt = _by_point(violations)
    blocks = []
    for pt in sorted(by_pt):
        head = "редакция · безопасность публикации" if pt == 0 else f"п.{pt} канона"
        vs = by_pt[pt]
        errs = sum(1 for v in vs if v["severity"] == "error")
        badge = (f'<span class="badge b-err">{errs}</span>' if errs else "") + \
                (f'<span class="badge b-warn">{len(vs) - errs}</span>' if len(vs) - errs else "")
        items = []
        for v in vs:
            inline = v["offset"][1] > v["offset"][0]
            loc = f'{v["line"]}:{v["col"]}' if inline else "—"
            sev = "cat-redaction" if v["category"] == "redaction" else f'sev-{v["severity"]}'
            fix = (f'<div class="fix">→ {html.escape(v["fix"])}</div>' if v.get("fix") else "")
            items.append(
                f'<li class="{sev}" tabindex="0" data-vid="{html.escape(_vid(v))}">'
                f'<span class="loc">{loc}</span> '
                f'<b>«{html.escape(v["quote"])}»</b> {html.escape(v["message"])}{fix}</li>')
        blocks.append(f'<section><h3>{html.escape(head)}{badge}</h3>'
                      f'<ul>{"".join(items)}</ul></section>')
    return "".join(blocks)


_TPL = """<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>canon-lens · карта нарушений · __NAME__</title>
<style>
 /* нейтраль с лёгким тёплым уклоном к акценту (охра) — не чистый серый */
 :root{
   --bg:#f7f6f3; --surface:#ffffff; --line:#e4e1da; --ink:#1c1a17; --muted:#6b6660;
   --err:#c0392b; --errbg:#fbeae7; --errline:#e6b8b0;
   --warn:#9a6b12; --warnbg:#faf1dd; --warnline:#e6cea0;
   --red:#6d28d9; --redbg:#f0eafb; --redline:#cdbbf0;
   --ok:#3f7d3f;
 }
 :root:not([data-theme="light"]){}
 @media (prefers-color-scheme:dark){
   :root:not([data-theme="light"]){
     --bg:#17161a; --surface:#1f1e23; --line:#33313a; --ink:#eceae6; --muted:#9a948c;
     --err:#f0857a; --errbg:#331e1c; --errline:#5e2f2a;
     --warn:#e0b25e; --warnbg:#2f2515; --warnline:#5b4620;
     --red:#b794f6; --redbg:#241a38; --redline:#42306b;
     --ok:#8fca8f;
   }
 }
 :root[data-theme="dark"]{
   --bg:#17161a; --surface:#1f1e23; --line:#33313a; --ink:#eceae6; --muted:#9a948c;
   --err:#f0857a; --errbg:#331e1c; --errline:#5e2f2a;
   --warn:#e0b25e; --warnbg:#2f2515; --warnline:#5b4620;
   --red:#b794f6; --redbg:#241a38; --redline:#42306b;
   --ok:#8fca8f;
 }
 *{box-sizing:border-box}
 body{margin:0;font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
 header{padding:12px 20px;border-bottom:1px solid var(--line);background:var(--surface)}
 header h1{margin:0;font-size:13px;font-weight:600;letter-spacing:.01em}
 header code{background:var(--bg);padding:1px 5px;border-radius:4px;border:1px solid var(--line)}
 .canon{margin-left:6px;color:var(--muted);font-weight:400}
 .tiles{display:flex;gap:10px;margin-top:10px;flex-wrap:wrap}
 .tile{background:var(--bg);border:1px solid var(--line);border-radius:9px;padding:7px 12px;min-width:96px}
 .tile .n{font-size:20px;font-weight:650;font-variant-numeric:tabular-nums;line-height:1.15}
 .tile .n .of{font-size:13px;font-weight:400;color:var(--muted)}
 .tile .c{font-size:11px;color:var(--muted);margin-top:1px}
 .tile.t-error .n{color:var(--err)} .tile.t-warning .n{color:var(--warn)}
 .cov{display:flex;align-items:center;gap:3px;margin-top:10px;flex-wrap:wrap}
 .cov-l{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-right:5px}
 .cell{width:20px;height:20px;display:grid;place-items:center;border-radius:4px;font-size:11px;font-weight:600;font-variant-numeric:tabular-nums;color:#fff}
 .c-ok{background:var(--ok)} .c-warn{background:var(--warn)} .c-err{background:var(--err)}
 .legend{display:flex;gap:14px;margin-top:9px;font-size:11px;color:var(--muted)}
 .legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:4px;vertical-align:middle}
 .wrap{display:grid;grid-template-columns:1fr 400px;height:calc(100vh - 172px)}
 @media (max-width:820px){.wrap{grid-template-columns:1fr;height:auto}}
 .doc{padding:24px 28px;overflow:auto;white-space:pre-wrap;word-wrap:break-word;background:var(--surface);border-right:1px solid var(--line);font:13px/1.8 ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}
 .panel{overflow:auto;padding:14px 16px;background:var(--bg)}
 .panel section{margin-bottom:16px}
 .panel h3{margin:0 0 7px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);display:flex;align-items:center;gap:5px}
 .badge{font-size:10px;font-weight:700;color:#fff;border-radius:8px;padding:1px 6px;letter-spacing:0}
 .badge.b-err{background:var(--err)} .badge.b-warn{background:var(--warn)}
 .clean{margin:8px 2px;padding:12px 14px;border-radius:8px;background:var(--bg);border:1px solid var(--ok);color:var(--ok);font-weight:600}
 .panel ul{list-style:none;margin:0;padding:0}
 .panel li{padding:7px 10px;border-radius:7px;margin-bottom:5px;cursor:pointer;border-left:3px solid var(--line);background:var(--surface)}
 .panel li:hover{filter:brightness(1.04)}
 .panel li:focus-visible{outline:2px solid var(--ink);outline-offset:1px}
 .panel li .loc{color:var(--muted);font-variant-numeric:tabular-nums;margin-right:6px;font-family:ui-monospace,monospace;font-size:12px}
 .panel li .fix{color:var(--muted);font-size:12px;margin-top:3px}
 .v{border-radius:3px;padding:0 1px;box-decoration-break:clone;-webkit-box-decoration-break:clone}
 .sev-error,li.sev-error{background:var(--errbg);border-color:var(--err)}
 .sev-warning,li.sev-warning{background:var(--warnbg);border-color:var(--warn)}
 .cat-redaction,li.cat-redaction{background:var(--redbg);border-color:var(--red)}
 .v.sev-error{box-shadow:inset 0 -2px 0 var(--errline)} .v.sev-warning{box-shadow:inset 0 -2px 0 var(--warnline)} .v.cat-redaction{box-shadow:inset 0 -2px 0 var(--redline)}
 .v.flash{outline:2px solid var(--ink);outline-offset:2px}
 @media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
</style>
<header>
 <h1>карта нарушений канона · <code>__NAME__</code><span class="canon">__CANON__</span></h1>
 <div class="tiles">__TILES__</div>
 __COV__
 <div class="legend">
  <span><i style="background:var(--err)"></i>error — публиковать нельзя</span>
  <span><i style="background:var(--warn)"></i>warning — на проверку</span>
  <span><i style="background:var(--red)"></i>redaction — безопасность</span>
 </div>
</header>
<div class="wrap">
 <div class="doc" id="doc">__BODY__</div>
 <div class="panel">__PANEL__</div>
</div>
<script>
 var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
 function activate(li){
   var id = li.dataset.vid;
   document.querySelectorAll('.v.flash').forEach(function(e){ e.classList.remove('flash'); });
   var t = [].slice.call(document.querySelectorAll('.v')).filter(function(e){
     return e.dataset.vids.split(' ').indexOf(id) !== -1;
   });
   if (t.length){
     t.forEach(function(e){ e.classList.add('flash'); });
     t[0].scrollIntoView({block:'center', behavior: reduce ? 'auto' : 'smooth'});
   }
 }
 document.querySelectorAll('.panel li').forEach(function(li){
   li.addEventListener('click', function(){ activate(li); });
   li.addEventListener('keydown', function(e){
     if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); activate(li); }
   });
 });
</script>
"""


def build_html(text: str, data: dict) -> str:
    s = data["summary"]
    vs = data["violations"]
    by_pt = _by_point(vs)
    canon_pts = data.get("canon_points") or sorted(by_pt)
    canon_name = data.get("canon_name") or ""
    return (_TPL
            .replace("__NAME__", html.escape(Path(data["file"]).name))
            .replace("__CANON__", html.escape(canon_name))
            .replace("__TILES__", _stat_tiles(s, len(by_pt), len(canon_pts)))
            .replace("__COV__", _coverage(canon_pts, by_pt))
            .replace("__BODY__", _render_text(text, vs))
            .replace("__PANEL__", _render_panel(vs)))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="lens_map", description="визуальная карта нарушений канона")
    p.add_argument("file")
    p.add_argument("--canon", help="канон-файл (запустить проверку самому)")
    p.add_argument("--violations", help="JSON от `canon-lens check --json`")
    p.add_argument("-o", "--out", default="canon-map.html")
    a = p.parse_args(argv)
    if not a.canon and not a.violations:
        p.error("нужен --canon или --violations")

    tp = Path(a.file)
    data = _collect(tp, a)
    out = build_html(tp.read_text(encoding="utf-8"), data)
    Path(a.out).write_text(out, encoding="utf-8")
    print(f"{a.out}  ({len(out)} b, {data['summary']['total']} нарушений)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
