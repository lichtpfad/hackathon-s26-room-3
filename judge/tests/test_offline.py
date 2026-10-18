"""Оффлайн-приёмка: записанный вердикт судьи → Violation той же формы, что
canon-lens, с корректным offset. LLM не вызывается."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from judge.judge import judge_text, summary   # noqa: E402

HERE = Path(__file__).resolve().parent
CANON = HERE.parents[1] / "canon-lens" / "canon.md"
FIX = HERE / "fixtures" / "antithesis-variant.md"


def _run():
    text = FIX.read_text(encoding="utf-8")
    return text, judge_text(text, CANON, offline_source=FIX)


def test_finds_antithesis_variant():
    _text, vs = _run()
    assert len(vs) == 1
    assert vs[0].rule == "no-antithesis" and vs[0].point == 3


def test_kind_is_judgment():
    _text, vs = _run()
    assert vs[0].kind == "judgment"


def test_offset_anchored_to_real_text():
    text, vs = _run()
    v = vs[0]
    assert v.offset != [0, 0]
    assert text[v.offset[0]:v.offset[1]] == v.quote     # offset реально указывает на цитату


def test_contract_fields_present():
    _text, vs = _run()
    d = vs[0].as_dict()
    for f in ("rule", "point", "category", "severity", "kind",
              "line", "col", "end_col", "offset", "quote", "message", "fix"):
        assert f in d, f"нет поля контракта: {f}"


def test_summary_shape():
    _text, vs = _run()
    s = summary(vs)
    assert s["total"] == 1 and s["errors"] == 1 and s["points"] == [3]


def test_confidence_carried():
    _text, vs = _run()
    assert abs(vs[0].confidence - 0.72) < 1e-9


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    ok = 0
    for fn in fns:
        fn(); ok += 1; print(f"  ok {fn.__name__}")
    print(f"PASS {ok}/{len(fns)} — test_offline")
