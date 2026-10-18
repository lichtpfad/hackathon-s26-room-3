"""Executable specifications for the Matt content pipeline."""

from __future__ import annotations

from pathlib import Path
import re

from matt.pipeline import accept_all, evaluate, find_violations, generate, load_canon
from matt.run import main


REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "examples"
CANON_PATH = EXAMPLES / "canon.md"


def test_es_001_proofread_report_has_direct_locations() -> None:
    """ES-001 covers AC-001 in pure mode."""
    # Given
    canon = load_canon(CANON_PATH)
    # When
    result = generate(EXAMPLES / "01-вычитка", CANON_PATH)
    # Then
    points = [item.point for item in result.violations]
    assert {1, 2, 3, 4, 6, 7, 8} <= set(points)
    assert points.count(4) >= 3
    assert points.count(8) >= 2
    assert all(item.quote and item.line > 0 and item.column > 0 for item in result.violations)
    assert evaluate(result, canon).passed


def test_es_002_rewritten_draft_is_clean() -> None:
    """ES-002 covers AC-002 and AC-005 in pure mode."""
    # Given
    canon = load_canon(CANON_PATH)
    # When
    result = generate(EXAMPLES / "01-вычитка", CANON_PATH)
    rewritten = result.content.split("## переписанный черновик", 1)[1].strip()
    # Then
    assert rewritten
    assert find_violations(rewritten, canon) == ()


def test_es_003_reel_uses_source_facts() -> None:
    """ES-003 covers AC-003 and AC-005 in pure mode."""
    # Given
    canon = load_canon(CANON_PATH)
    # When
    result = generate(EXAMPLES / "02-рилз", CANON_PATH)
    acceptance = evaluate(result, canon)
    # Then
    assert acceptance.passed, acceptance.failures
    assert result.evidence["fact_count"] == 3


def test_es_004_digest_selects_reader_events() -> None:
    """ES-004 covers AC-004 and AC-005 in pure mode."""
    # Given
    canon = load_canon(CANON_PATH)
    # When
    result = generate(EXAMPLES / "03-дайджест", CANON_PATH)
    acceptance = evaluate(result, canon)
    # Then
    assert acceptance.passed, acceptance.failures
    assert "спор про цену" not in result.content.lower()


def test_es_005_complete_set_passes_three_examples(capsys) -> None:
    """ES-005 covers AC-006 in pure mode."""
    # Given / When
    results = accept_all(EXAMPLES, CANON_PATH)
    exit_code = main(["accept", str(EXAMPLES), "--canon", str(CANON_PATH)])
    # Then
    assert len(results) == 3
    assert all(result.passed for result in results)
    assert exit_code == 0
    assert "passed 3 of 3" in capsys.readouterr().out


def test_es_006_incomplete_set_fails(tmp_path: Path, capsys) -> None:
    """ES-006 covers AC-006 in pure mode."""
    # Given
    incomplete_examples = tmp_path / "examples"
    incomplete_examples.mkdir()
    # When
    results = accept_all(incomplete_examples, CANON_PATH)
    exit_code = main(["accept", str(incomplete_examples), "--canon", str(CANON_PATH)])
    # Then
    assert len(results) == 3
    assert not any(result.passed for result in results)
    assert exit_code != 0
    assert "passed 0 of 3" in capsys.readouterr().out


def test_es_007_all_contract_clauses_have_direct_coverage() -> None:
    """ES-007 covers AC-007 in pure mode."""
    # Given
    contract = (REPO / "matt" / "CONTRACT.md").read_text(encoding="utf-8")
    specifications = (REPO / "matt" / "EXECUTABLE_SPECS.md").read_text(encoding="utf-8")
    clauses = set(re.findall(r"^### (AC-\d+):", contract, re.MULTILINE))
    # When
    matrix = specifications.split("## Direct coverage matrix", 1)[1]
    # Then
    assert clauses == {f"AC-{number:03d}" for number in range(1, 10)}
    assert all(f"`{clause}`" in matrix for clause in clauses)


def test_es_008_external_canon_adds_a_rule_without_code_change(tmp_path: Path) -> None:
    """ES-008 covers AC-008 in pure mode."""
    # Given
    changed_canon = tmp_path / "canon.md"
    canon_text = CANON_PATH.read_text(encoding="utf-8")
    changed_canon.write_text(
        canon_text.replace("«синергия»", "«синергия», «инструмент»"),
        encoding="utf-8",
    )
    # When
    result = generate(EXAMPLES / "01-вычитка", changed_canon)
    # Then
    added = [item for item in result.violations if item.point == 4 and item.quote.lower() == "инструмент"]
    assert added


def test_es_009_invalid_path_returns_input_error(tmp_path: Path, capsys) -> None:
    """ES-009 covers AC-009 in pure mode."""
    # Given
    absent = tmp_path / "absent-example"
    # When
    exit_code = main(["run", str(absent), "--canon", str(CANON_PATH)])
    captured = capsys.readouterr()
    # Then
    assert exit_code == 2
    assert str(absent) in captured.err
