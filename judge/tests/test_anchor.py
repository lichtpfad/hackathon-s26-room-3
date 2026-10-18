"""Якорение цитаты в offset: точное вхождение, устойчивость к пробелам, промах."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from judge.anchor import anchor, line_col   # noqa: E402

TEXT = "первая строка\nвторая строка с целью\nтретья строка тут"


def test_exact():
    s, e, ok = anchor(TEXT, "целью")
    assert ok and TEXT[s:e] == "целью"


def test_line_col():
    s, e, ok = anchor(TEXT, "целью")
    line, col = line_col(TEXT, s)
    assert line == 2 and col == 17


def test_loose_whitespace():
    # цитата с иным пробелом/переводом строки, чем в тексте
    s, e, ok = anchor(TEXT, "вторая   строка")
    assert ok and TEXT[s:e] == "вторая строка"


def test_not_found():
    s, e, ok = anchor(TEXT, "такого фрагмента нет")
    assert not ok and (s, e) == (0, 0)


def test_empty():
    s, e, ok = anchor(TEXT, "   ")
    assert not ok


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    ok = 0
    for fn in fns:
        fn(); ok += 1; print(f"  ok {fn.__name__}")
    print(f"PASS {ok}/{len(fns)} — test_anchor")
