# Интеграция canon-lens в инструмент комнаты

Для оркестратора / acceptance-runner (issue #2). Зависимостей нет — stdlib, Python ≥ 3.11.
Точка запуска: из папки `canon-lens/`, либо добавить её в `sys.path` / `PYTHONPATH`.

## 1. Приёмка примера — `accept.run()`

```python
import sys; sys.path.insert(0, "canon-lens")
from accept import run

r = run("examples/01-вычитка", "canon-lens/canon.md")
# r = {"passed": 7, "of": 7, "missed": [], "ok": True,
#      "expected_points": [...], "caught_points": [...], "per_file": [...]}
```

CLI: `python canon-lens/accept.py examples/01-вычитка [--canon ...]` → печатает
«прошло N из M», код возврата 0 (ok) / 1 (промах) / 2 (нет `expected.md`/`input/`).

`accept` сверяет пункты канона, упомянутые в `expected.md` как `(п.N)`, с тем, что
поймал линтер. Для рилз/дайджеста таких пунктов нет — там приёмка не через canon-lens.

## 2. Проверка произвольного текста — `check_text()`

```python
from canon_lens import load_canon, check_text

canon = load_canon("canon-lens/canon.sostav.md")
violations = check_text(text, canon)          # list[Violation]
data = [v.as_dict() for v in violations]      # форма — canon-lens/CONTRACTS.md
```

CLI: `python -m canon_lens.cli check <файл> --canon <канон> [--json]`
`--json` → `{file, summary, violations[]}`. Код возврата 1 при наличии `error`.

## 3. Визуальная карта — `lens/lens_map.py`

```
python canon-lens/lens/lens_map.py <файл> --canon <канон> -o map.html
# или из готового JSON:
python canon-lens/lens/lens_map.py <файл> --violations v.json -o map.html
```
Самодостаточный HTML, без внешних зависимостей.

## Каноны в репо

| Файл | Для чего |
|---|---|
| `canon.md` | synthetic, под приёмку `examples/` |
| `canon.sostav.md` | клубный блог AI Practiq (лид, кейс, FAQ, SEO-ключ, 1–2 CTA на клуб) |

Смена канона = аргумент `--canon`, код не меняется. Новый вид правила = функция
в `canon_lens/check.py` (`_DISPATCH`); всё прочее — данными в `.md`.

## Контракт формы нарушения

`canon-lens/CONTRACTS.md`. Стабильны: `rule, point, offset, quote, severity`.
Модуль `judge/` (смысловые правила) выдаёт объекты той же формы — `report/`
объединяет по `offset`.
