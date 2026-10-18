#!/usr/bin/env python3
"""CLI E2E конвейера комнаты 3 — через реальные CLI модулей, детерминированно.

Прогоняет полный путь на одном тексте:
  canon-lens check --json  (механика/redaction)
  judge      check --offline --json  (смысл)
  report     merge ...      (единый отчёт)
плюс digest make --offline --check (генерация → self-check).

LLM не вызывается (judge/digest в offline) — воспроизводимо на приёмке.
Запуск из корня репозитория:  python report/e2e.py

Код возврата 0 — все шаги прошли, иначе 1.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(mod_path, args, capture_out=None):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(ROOT / mod_path)
    r = subprocess.run([PY, "-m", *args], cwd=str(ROOT), env=env,
                       capture_output=True, text=True, encoding="utf-8")
    if capture_out:
        Path(capture_out).write_text(r.stdout, encoding="utf-8")
    return r


results = []
TMP = ROOT / "report" / ".e2e-tmp"
TMP.mkdir(exist_ok=True)

# один текст на весь конвейер: непрямая антитеза (regex не ловит, судья ловит)
SRC = ROOT / "judge" / "tests" / "fixtures" / "antithesis-variant.md"
CANON = ROOT / "canon-lens" / "canon.md"

# 1. canon-lens — механика
run("canon-lens", ["canon_lens.cli", "check", str(SRC), "--canon", str(CANON), "--json"],
    capture_out=TMP / "mech.json")
mech = json.loads((TMP / "mech.json").read_text(encoding="utf-8"))
results.append(("canon-lens check --json", "violations" in mech,
                f"механических: {mech.get('summary', {}).get('total', '?')}"))

# 2. judge — смысл (offline)
run("judge", ["judge.cli", "check", str(SRC), "--canon", str(CANON), "--offline", "--json"],
    capture_out=TMP / "judge.json")
jud = json.loads((TMP / "judge.json").read_text(encoding="utf-8"))
jud_ok = any(v.get("kind") == "judgment" for v in jud.get("violations", []))
results.append(("judge check --offline --json", jud_ok,
                f"судейских: {jud.get('summary', {}).get('total', '?')}"))

# 3. report — единый отчёт
rep = run("report", ["report.cli", "merge", str(TMP / "mech.json"), str(TMP / "judge.json"), "--json"],
          capture_out=TMP / "report.json")
merged = json.loads((TMP / "report.json").read_text(encoding="utf-8"))
bk = merged.get("summary", {}).get("by_kind", {})
report_ok = merged.get("summary", {}).get("total", 0) >= 1
results.append(("report merge --json", report_ok, f"by_kind: {bk}"))

# 4. digest — генерация → self-check (offline)
notes = ROOT / "digest" / "tests" / "fixtures" / "notes-week.txt"
d = run("digest", ["digest.cli", "make", str(notes), "--offline", "--check"])
digest_ok = bool(d.stdout.strip()) and "0 error" in (d.stderr or "")
results.append(("digest make --offline --check", digest_ok,
                (d.stderr.strip().splitlines() or ["нет self-check"])[-1]))

# вывод
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (ValueError, OSError, AttributeError):
    pass
print("=== CLI E2E конвейера комнаты 3 ===")
passed = sum(1 for _, ok, _ in results if ok)
for name, ok, note in results:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name:32} {note}")
print(f"\nИТОГ: {passed}/{len(results)} шагов CLI E2E прошли")
sys.exit(0 if passed == len(results) else 1)
