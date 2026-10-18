"""Мёрж находок canon-lens + judge: объединение, дедуп по (rule,offset),
сортировка по месту, разбивка by_kind."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from report.merge import merge_reports, summary   # noqa: E402

MECH = {
    "file": "post.md",
    "violations": [
        {"rule": "forbidden-words", "point": 4, "category": "canon", "severity": "error",
         "kind": "mechanical", "line": 5, "col": 1, "offset": [120, 129], "quote": "прорывной",
         "message": "запрещённое слово (п.4)", "fix": "заменить"},
        {"rule": "no-antithesis", "point": 3, "category": "canon", "severity": "error",
         "kind": "judgment-literal", "line": 2, "col": 1, "offset": [20, 40],
         "quote": "не X, а Y", "message": "антитеза (п.3)", "fix": ""},
    ],
}
JUDGE = {
    "file": "post.md",
    "violations": [
        {"rule": "no-antithesis", "point": 3, "category": "canon", "severity": "error",
         "kind": "judgment", "line": 8, "col": 1, "offset": [200, 230],
         "quote": "скрытое противопоставление", "message": "антитеза-вариация (п.3)", "fix": "переписать"},
    ],
}


def test_merges_all():
    r = merge_reports([MECH, JUDGE])
    assert r["summary"]["total"] == 3


def test_sorted_by_offset():
    r = merge_reports([MECH, JUDGE])
    offs = [v["offset"][0] for v in r["violations"]]
    assert offs == sorted(offs) == [20, 120, 200]


def test_dedup_same_rule_offset():
    r = merge_reports([MECH, JUDGE, JUDGE])   # judge дважды
    assert r["summary"]["total"] == 3          # дубль схлопнут


def test_by_kind_breakdown():
    r = merge_reports([MECH, JUDGE])
    bk = r["summary"]["by_kind"]
    assert bk["mechanical"] == 1 and bk["judgment"] == 1 and bk["judgment-literal"] == 1


def test_points_union():
    r = merge_reports([MECH, JUDGE])
    assert r["summary"]["points"] == [3, 4]


def test_file_inherited():
    r = merge_reports([MECH, JUDGE])
    assert r["file"] == "post.md"


def test_empty():
    r = merge_reports([{"violations": []}])
    assert r["summary"]["clean"] and r["summary"]["total"] == 0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    ok = 0
    for fn in fns:
        fn(); ok += 1; print(f"  ok {fn.__name__}")
    print(f"PASS {ok}/{len(fns)} — test_merge")
