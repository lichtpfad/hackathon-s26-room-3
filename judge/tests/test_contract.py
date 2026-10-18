"""Устойчивость ядра: выдуманное правило отбрасывается, непривязанная цитата
не теряется, дедуп по (rule, offset), пустой канон → пусто."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from judge import judge   # noqa: E402
from judge.judge import judge_text   # noqa: E402

HERE = Path(__file__).resolve().parent
CANON = HERE.parents[1] / "canon-lens" / "canon.md"
PROSE_CANON = HERE.parents[1] / "examples" / "canon.md"

TEXT = "Многие думают, что агент — это про скорость. Но дело совсем не в скорости."


def _judge_with(raw, text=TEXT):
    """Прогнать ядро на подсунутых «находках» (минуя LLM), monkeypatch offline."""
    import judge.llm as llm
    orig = llm.findings_offline
    llm.findings_offline = lambda _p: raw
    try:
        return judge_text(text, CANON, offline_source="dummy")
    finally:
        llm.findings_offline = orig


def test_invented_rule_dropped():
    vs = _judge_with([{"rule_id": "no-such-rule", "quote": "агент"}])
    assert vs == []


def test_unanchored_kept_as_doc_level():
    vs = _judge_with([{"rule_id": "no-antithesis", "quote": "фразы которой нет в тексте"}])
    assert len(vs) == 1 and vs[0].offset == [0, 0] and vs[0].line == 1


def test_dedup_same_rule_same_span():
    dup = {"rule_id": "no-antithesis", "quote": "дело совсем не в скорости"}
    vs = _judge_with([dup, dict(dup)])
    assert len(vs) == 1


def test_missing_quote_ignored():
    vs = _judge_with([{"rule_id": "no-antithesis"}, {"quote": "дело совсем не в скорости"}])
    assert vs == []


def test_prose_canon_has_no_judge_rules():
    # прозаический канон без toml-блока → судить нечего
    vs = judge_text(TEXT, PROSE_CANON, offline_source="dummy")
    assert vs == []


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    ok = 0
    for fn in fns:
        fn(); ok += 1; print(f"  ok {fn.__name__}")
    print(f"PASS {ok}/{len(fns)} — test_contract")
