"""Smoke-тесты рендера: терминальный и HTML не падают и содержат суть."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from report import render as R   # noqa: E402

REP = {
    "file": "post.md",
    "summary": {"total": 2, "errors": 1, "warnings": 1, "points": [3, 4],
                "by_kind": {"mechanical": 1, "judgment": 1}, "clean": False},
    "violations": [
        {"rule": "forbidden-words", "point": 4, "severity": "error", "kind": "mechanical",
         "line": 1, "col": 1, "offset": [0, 9], "quote": "прорывной",
         "message": "запрещённое слово (п.4)", "fix": "заменить"},
        {"rule": "no-antithesis", "point": 3, "severity": "warning", "kind": "judgment",
         "line": 1, "col": 20, "offset": [20, 40], "quote": "скрытая антитеза",
         "message": "антитеза (п.3)", "confidence": 0.8, "fix": "переписать"},
    ],
}
TEXT = "прорывной подход, тут скрытая антитеза и дальше текст продолжается ещё"


def test_terminal_render_runs():
    out = R.render(REP, TEXT)
    assert "post.md" in out and "2 нарушени" in out


def test_terminal_no_color_when_piped():
    # в тестовом окружении stdout не tty → без ANSI-кодов
    out = R.render(REP, TEXT)
    assert "\033[" not in out


def test_html_valid_shell():
    html = R.render_html(REP, TEXT)
    assert html.startswith("<!doctype html>") and "</html>" in html
    assert "запрещённое слово" in html and "антитеза" in html


def test_html_escapes():
    rep = {"file": "x", "summary": {"total": 1, "errors": 1, "warnings": 0, "by_kind": {}},
           "violations": [{"rule": "r", "point": 1, "severity": "error", "kind": "mechanical",
                           "offset": [0, 3], "quote": "<b>&", "message": "m", "line": 1, "col": 1}]}
    assert "&lt;b&gt;&amp;" in R.render_html(rep)


def test_clean_report():
    clean = {"file": "ok.md", "summary": {"total": 0, "errors": 0, "warnings": 0,
             "by_kind": {}, "clean": True}, "violations": []}
    assert "чисто" in R.render(clean)
    assert "чисто" in R.render_html(clean)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    ok = 0
    for fn in fns:
        fn(); ok += 1; print(f"  ok {fn.__name__}")
    print(f"PASS {ok}/{len(fns)} — test_render")
