"""Оффлайн-приёмка дайджеста: записанный дайджест проходит канон дайджеста
чисто и содержит ключевые факты недели. LLM не вызывается."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "digest"))
sys.path.insert(0, str(ROOT / "canon-lens"))

from digest.core import make_digest, build_prompt   # noqa: E402
from canon_lens.rules import load_canon             # noqa: E402
from canon_lens.check import check_text, summary    # noqa: E402

FIX = HERE / "fixtures" / "notes-week.txt"
DIGEST_CANON = ROOT / "digest" / "canon.digest.md"


def _digest():
    notes = FIX.read_text(encoding="utf-8")
    return make_digest(notes, offline_source=FIX)


def test_offline_returns_digest():
    d = _digest()
    assert d.strip() and d.splitlines()[0] == "итоги недели"


def test_passes_digest_canon_clean():
    d = _digest()
    canon = load_canon(DIGEST_CANON)
    s = summary(check_text(d, canon))
    assert s["errors"] == 0, f"дайджест нарушает свой канон: {s}"


def test_item_count_3_to_5():
    d = _digest()
    items = [ln for ln in d.splitlines() if ln.strip().startswith("-")]
    assert 3 <= len(items) <= 5


def test_key_facts_present():
    d = _digest().lower()
    for fact in ("тёмн", "120", "октябр", "саппорт", "6 час"):
        assert fact in d, f"пропал факт: {fact}"


def test_bad_news_not_hidden():
    # срыв интеграции — плохая новость, должна быть в дайджесте
    assert "сорвал" in _digest().lower()


def test_prompt_mentions_canon():
    p = build_prompt("пн: тест")
    assert "дайджест" in p.lower() and "заголовок" in p.lower()


if __name__ == "__main__":
    for stream in (sys.stdout,):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    ok = 0
    for fn in fns:
        fn(); ok += 1; print(f"  ok {fn.__name__}")
    print(f"PASS {ok}/{len(fns)} — test_digest")
