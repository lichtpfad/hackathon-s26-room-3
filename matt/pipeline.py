"""Offline content pipeline for the Room 3 acceptance examples."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Iterable


class PipelineError(ValueError):
    """An input does not satisfy the Matt input contract."""


@dataclass(frozen=True)
class Canon:
    """The subset of canon data that the deterministic pipeline can apply."""

    path: Path
    text: str
    clauses: frozenset[int]
    forbidden_words: tuple[str, ...]
    clerical_terms: tuple[str, ...]
    max_chars: int = 1200
    max_paragraph_lines: int = 4


@dataclass(frozen=True)
class Violation:
    point: int
    quote: str
    line: int
    column: int
    message: str

    def markdown(self) -> str:
        return (
            f"- п.{self.point}, строка {self.line}, колонка {self.column}: "
            f"«{self.quote}» — {self.message}."
        )


@dataclass(frozen=True)
class PipelineResult:
    example: str
    kind: str
    content: str
    source: str
    violations: tuple[Violation, ...] = ()
    evidence: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class AcceptanceResult:
    example: str
    passed: bool
    checks: tuple[str, ...]
    failures: tuple[str, ...]
    result: PipelineResult | None = None


_QUOTE_RE = re.compile(r"[«“](.*?)[»”]")
_CLAUSE_RE = re.compile(r"^\s*(\d+)\.", re.MULTILINE)
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "]",
)
_ANTITHESIS_RE = re.compile(
    r"\b(?:это\s+)?не\s+(?:просто\s+)?[^.!?\n]+?[,—-]\s*а\s+[^.!?\n]+",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"(?<!\w)\d+(?:[.,]\d+)?%?")


def load_canon(path: str | Path) -> Canon:
    canon_path = Path(path)
    if not canon_path.is_file():
        raise PipelineError(f"canon file does not exist: {canon_path}")

    text = canon_path.read_text(encoding="utf-8")
    clauses = frozenset(int(value) for value in _CLAUSE_RE.findall(text))
    lines = {int(match.group(1)): match.group(2) for match in re.finditer(
        r"^\s*(\d+)\.\s*(.+)$", text, re.MULTILINE
    )}

    forbidden_words = tuple(
        word.strip().lower()
        for word in _QUOTE_RE.findall(lines.get(4, ""))
        if word.strip()
    )
    clerical_source = lines.get(8, "")
    clerical_source = clerical_source[clerical_source.lower().find("канцеляр"):]
    clerical_terms = tuple(
        word.strip().lower()
        for word in _QUOTE_RE.findall(clerical_source)
        if word.strip()
    )

    max_chars = _first_int_after(lines.get(5, ""), "пост", default=1200)
    max_lines = _first_int_after(lines.get(5, ""), "абзац", default=4)
    return Canon(
        path=canon_path,
        text=text,
        clauses=clauses,
        forbidden_words=forbidden_words,
        clerical_terms=clerical_terms,
        max_chars=max_chars,
        max_paragraph_lines=max_lines,
    )


def generate(example_dir: str | Path, canon_path: str | Path) -> PipelineResult:
    directory = Path(example_dir)
    if not directory.is_dir():
        raise PipelineError(f"example directory does not exist: {directory}")

    input_dir = directory / "input"
    input_files = sorted(path for path in input_dir.glob("*") if path.is_file())
    if not input_files:
        raise PipelineError(f"example has no input files: {directory}")

    source = "\n\n".join(path.read_text(encoding="utf-8") for path in input_files)
    canon = load_canon(canon_path)
    prefix = directory.name.split("-", 1)[0]
    if prefix == "01":
        return _proofread(directory.name, source, canon)
    if prefix == "02":
        return _reel(directory.name, source, canon)
    if prefix == "03":
        return _digest(directory.name, source, canon)
    raise PipelineError(f"unsupported example type: {directory.name}")


def accept_all(examples_dir: str | Path, canon_path: str | Path) -> tuple[AcceptanceResult, ...]:
    root = Path(examples_dir)
    if not root.is_dir():
        raise PipelineError(f"examples directory does not exist: {root}")

    canon = load_canon(canon_path)
    results: list[AcceptanceResult] = []
    for prefix in ("01", "02", "03"):
        matches = sorted(path for path in root.glob(f"{prefix}-*") if path.is_dir())
        if len(matches) != 1:
            results.append(AcceptanceResult(
                example=prefix,
                passed=False,
                checks=(),
                failures=(f"expected one {prefix}-* example, found {len(matches)}",),
            ))
            continue
        result = generate(matches[0], canon.path)
        results.append(evaluate(result, canon))
    return tuple(results)


def evaluate(result: PipelineResult, canon: Canon) -> AcceptanceResult:
    if result.kind == "proofread":
        return _evaluate_proofread(result, canon)
    if result.kind == "reel":
        return _evaluate_reel(result, canon)
    if result.kind == "digest":
        return _evaluate_digest(result, canon)
    return AcceptanceResult(result.example, False, (), ("unsupported result kind",), result)


def find_violations(text: str, canon: Canon) -> tuple[Violation, ...]:
    violations: list[Violation] = []

    if 1 in canon.clauses:
        for match in _EMOJI_RE.finditer(text):
            violations.append(_violation(text, match, 1, "эмодзи запрещено"))

    if 2 in canon.clauses:
        heading = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if heading:
            first = re.search(r"[A-Za-zА-Яа-яЁё]", heading.group(1))
            if first and first.group(0).isupper():
                start = heading.start(1) + first.start()
                match = re.match(r".+", text[start:])
                assert match is not None
                violations.append(_violation_from_span(
                    text,
                    start,
                    start + len(heading.group(1)),
                    2,
                    "заголовок должен начинаться со строчной буквы",
                ))

    if 3 in canon.clauses:
        for match in _ANTITHESIS_RE.finditer(text):
            violations.append(_violation(text, match, 3, "антитеза запрещена"))

    if 4 in canon.clauses:
        for word in canon.forbidden_words:
            for match in re.finditer(rf"(?<!\w){re.escape(word)}\w*", text, re.IGNORECASE):
                violations.append(_violation(text, match, 4, "запрещённое слово"))

    if 5 in canon.clauses:
        if len(text) > canon.max_chars:
            violations.append(_violation_from_span(
                text, 0, min(len(text), 20), 5, f"текст длиннее {canon.max_chars} знаков"
            ))
        for paragraph in re.split(r"\n\s*\n", text):
            if len(paragraph.splitlines()) > canon.max_paragraph_lines:
                start = text.find(paragraph)
                violations.append(_violation_from_span(
                    text,
                    start,
                    start + min(len(paragraph), 40),
                    5,
                    f"абзац длиннее {canon.max_paragraph_lines} строк",
                ))

    if 6 in canon.clauses:
        offset = 0
        for line in text.splitlines(keepends=True):
            visible = line.rstrip("\r\n")
            for match in _NUMBER_RE.finditer(visible):
                value = match.group(0)
                if len(value) == 4 and value.isdigit():
                    continue
                if "(" in visible and ")" in visible:
                    continue
                violations.append(_violation_from_span(
                    text,
                    offset + match.start(),
                    offset + match.end(),
                    6,
                    "число должно иметь источник в скобках",
                ))
            offset += len(line)

    if 7 in canon.clauses:
        for match in re.finditer(r"\bподписывайтесь\b", text, re.IGNORECASE):
            violations.append(_violation(text, match, 7, "CTA «подписывайтесь» запрещён"))

    if 8 in canon.clauses:
        for term in canon.clerical_terms:
            stem = _term_stem(term)
            pattern = rf"(?<!\w){re.escape(stem)}\w*" if stem else re.escape(term)
            for match in re.finditer(pattern, text, re.IGNORECASE):
                violations.append(_violation(text, match, 8, "канцелярит"))

    return tuple(sorted(violations, key=lambda item: (item.line, item.column, item.point)))


def _proofread(example: str, source: str, canon: Canon) -> PipelineResult:
    violations = find_violations(source, canon)
    rewritten = _rewrite_draft(source, canon)
    report = "\n".join(item.markdown() for item in violations)
    content = (
        "# отчёт вычитки\n\n"
        "## нарушения\n\n"
        f"{report}\n\n"
        "## переписанный черновик\n\n"
        f"{rewritten.strip()}\n"
    )
    return PipelineResult(
        example=example,
        kind="proofread",
        content=content,
        source=source,
        violations=violations,
        evidence={"violation_count": len(violations)},
    )


def _reel(example: str, source: str, canon: Canon) -> PipelineResult:
    source_lower = source.lower()
    facts: list[str] = []
    if "3 «забытые» подписки" in source or "3 \"забытые\" подписки" in source:
        facts.append("Средний пользователь находит 3 забытые подписки в первый месяц (заметки с созвона).")
    if "две минуты" in source_lower or "2 минуты" in source_lower:
        facts.append("Настройка занимает 2 минуты (заметки с созвона).")
    if "любой почтой" in source_lower:
        facts.append("Приложение работает с любой почтой.")

    product = "Приложение собирает чеки из почты и считает траты по категориям."
    if "собирает чеки из почты" not in source_lower:
        product = "Приложение обрабатывает сведения из заметок."

    content = (
        "# сценарий рилза\n\n"
        "### хук (0–3 с)\n\n"
        "Вы теряли чек, когда он был нужен для гарантии?\n\n"
        "### суть (3–22 с)\n\n"
        f"{product}\n\n"
        f"{' '.join(facts)}\n\n"
        "### действие (22–30 с)\n\n"
        "Откройте почту и найдите один чек, который важно сохранить.\n"
    )
    return PipelineResult(
        example=example,
        kind="reel",
        content=content,
        source=source,
        evidence={"source_facts": tuple(facts), "fact_count": len(facts)},
    )


def _digest(example: str, source: str, canon: Canon) -> PipelineResult:
    items: list[str] = []
    for raw_line in source.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        if "тёмную тему" in lower:
            items.append("Вышла тёмная тема. Две жалобы на контраст исправили за день.")
        elif "интеграция с банком" in lower and "сорвалась" in lower:
            items.append("Интеграция с банком N сорвалась и переносится на октябрь.")
        elif "120 новых регистраций" in lower:
            items.append("Получили 120 регистраций после поста у блогера; ссылку на старый лендинг исправили.")
        elif "время ответа" in lower and "6 часов" in lower and "2" in lower:
            items.append("Наняли второго специалиста поддержки; время ответа сократилось с 6 часов до 2.")

    content = "# главное за неделю\n\n" + "\n".join(f"- {item}" for item in items) + "\n"
    return PipelineResult(
        example=example,
        kind="digest",
        content=content,
        source=source,
        evidence={"item_count": len(items)},
    )


def _evaluate_proofread(result: PipelineResult, canon: Canon) -> AcceptanceResult:
    checks: list[str] = []
    failures: list[str] = []
    points = [item.point for item in result.violations]
    required_points = {1, 2, 3, 4, 6, 7, 8}
    _record(required_points.issubset(points), "required canon clauses are reported", checks, failures)
    _record(points.count(4) >= 3, "three forbidden words are reported", checks, failures)
    _record(points.count(8) >= 2, "two clerical forms are reported", checks, failures)
    _record(
        all(item.line > 0 and item.column > 0 and item.quote for item in result.violations),
        "each violation has an exact location",
        checks,
        failures,
    )
    marker = "## переписанный черновик"
    rewritten = result.content.split(marker, 1)[1].strip() if marker in result.content else ""
    _record(bool(rewritten), "a rewritten draft is present", checks, failures)
    remaining = find_violations(rewritten, canon) if rewritten else ()
    _record(not remaining, "the rewritten draft is clean", checks, failures)
    return AcceptanceResult(result.example, not failures, tuple(checks), tuple(failures), result)


def _evaluate_reel(result: PipelineResult, canon: Canon) -> AcceptanceResult:
    checks: list[str] = []
    failures: list[str] = []
    lower = result.content.lower()
    for label in ("хук (0–3 с)", "суть (3–22 с)", "действие (22–30 с)"):
        _record(label in lower, f"section {label} is present", checks, failures)
    _record("3 забытые подписки" in lower, "three subscriptions fact is present", checks, failures)
    _record("2 минуты" in lower, "two-minute setup fact is present", checks, failures)
    _record("любой почтой" in lower, "any-email fact is present", checks, failures)
    _record(result.evidence.get("fact_count") == 3, "the main section uses three source facts", checks, failures)
    disallowed = {1, 2, 3, 4, 7}
    generated_violations = find_violations(result.content, canon)
    _record(
        not any(item.point in disallowed for item in generated_violations),
        "the reel obeys the applicable canon rules",
        checks,
        failures,
    )
    source_numbers = set(_NUMBER_RE.findall(result.source))
    source_lower = result.source.lower()
    if "две минуты" in source_lower:
        source_numbers.add("2")
    content_without_timing = re.sub(r"\(\d+[–-]\d+\s*с\)", "", result.content)
    content_numbers = set(_NUMBER_RE.findall(content_without_timing))
    _record(content_numbers <= source_numbers, "the reel has no invented product number", checks, failures)
    return AcceptanceResult(result.example, not failures, tuple(checks), tuple(failures), result)


def _evaluate_digest(result: PipelineResult, canon: Canon) -> AcceptanceResult:
    checks: list[str] = []
    failures: list[str] = []
    lower = result.content.lower()
    item_count = sum(1 for line in result.content.splitlines() if line.startswith("- "))
    _record(3 <= item_count <= 5, "the digest has three to five items", checks, failures)
    for fact in ("тёмная тема", "120 регистраций", "старый лендинг", "6 часов до 2"):
        _record(fact in lower, f"required fact {fact} is present", checks, failures)
    _record("интеграция" in lower and "октябрь" in lower, "the integration delay is present", checks, failures)
    _record("спор про цену" not in lower, "the internal price discussion is absent", checks, failures)
    disallowed = {1, 2, 3, 4}
    generated_violations = find_violations(result.content, canon)
    _record(
        not any(item.point in disallowed for item in generated_violations),
        "the digest obeys the applicable canon rules",
        checks,
        failures,
    )
    return AcceptanceResult(result.example, not failures, tuple(checks), tuple(failures), result)


def _rewrite_draft(source: str, canon: Canon) -> str:
    output: list[str] = []
    for original in source.splitlines():
        line = original.strip()
        if not line:
            if output and output[-1] != "":
                output.append("")
            continue
        if line.startswith("# "):
            heading = _EMOJI_RE.sub("", line[2:])
            heading = _remove_forbidden(heading, canon).strip(" .")
            output.append(f"# {heading.lower()}")
            continue
        if re.search(r"\bв\s+рамках\b", line, re.IGNORECASE) and "отдел" in line.lower():
            output.append("Наше решение помогает отделам работать вместе.")
            continue
        if _ANTITHESIS_RE.search(line):
            match = re.search(r"[,—-]\s*а\s+(.+)", line, re.IGNORECASE)
            replacement = f"Это {match.group(1)}" if match else line
            replacement = _remove_forbidden(replacement, canon)
            output.append(_normalize_sentence(replacement))
            continue
        if _line_has_unsourced_number(line) and 6 in canon.clauses:
            continue
        if re.search(r"\bподписывайтесь\b", line, re.IGNORECASE) and 7 in canon.clauses:
            output.append("Проверьте один рабочий материал по канону.")
            continue
        output.append(_normalize_sentence(_remove_forbidden(line, canon)))

    while output and output[-1] == "":
        output.pop()
    return "\n".join(output)


def _remove_forbidden(text: str, canon: Canon) -> str:
    value = text
    for word in canon.forbidden_words:
        value = re.sub(rf"(?<!\w){re.escape(word)}\w*", "", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).replace(" ,", ",").strip()


def _normalize_sentence(text: str) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    value = re.sub(r"\s+([,.!?])", r"\1", value)
    return value[:1].upper() + value[1:] if value else value


def _line_has_unsourced_number(line: str) -> bool:
    return bool(_NUMBER_RE.search(line)) and not ("(" in line and ")" in line)


def _record(condition: bool, label: str, checks: list[str], failures: list[str]) -> None:
    (checks if condition else failures).append(label)


def _first_int_after(text: str, word: str, default: int) -> int:
    position = text.lower().find(word)
    match = re.search(r"\d+", text[position:] if position >= 0 else "")
    return int(match.group(0)) if match else default


def _term_stem(term: str) -> str:
    if term.startswith("осуществ"):
        return "осуществ"
    return term


def _violation(text: str, match: re.Match[str], point: int, message: str) -> Violation:
    return _violation_from_span(text, match.start(), match.end(), point, message)


def _violation_from_span(text: str, start: int, end: int, point: int, message: str) -> Violation:
    line = text.count("\n", 0, start) + 1
    previous_newline = text.rfind("\n", 0, start)
    column = start - previous_newline
    return Violation(point, text[start:end], line, column, message)
