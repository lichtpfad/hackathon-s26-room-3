# report

Модуль участника **MG7S**. Единый отчёт из находок разных модулей по общему
контракту `Violation` (`canon-lens/CONTRACTS.md §2`).

## Что делает

`canon-lens` даёт механические/redaction-нарушения, `judge` — смысловые, оба в
форме `{file, summary, violations[]}`. `report` их **мёржит по `offset`**,
дедуплицирует по `(rule, offset)`, сортирует по месту в тексте и печатает один
отчёт — по пунктам канона, с пометкой источника (механика / судья / редакция).
Детерминированно, без LLM.

## Пайплайн одной командой — `report run`

Единая точка входа: принимает **вход** (черновик), сам прогоняет весь конвейер
(`canon-lens` → `judge`), собирает единый отчёт и печатает его **красиво в
терминал**, либо отдаёт JSON, либо верстает **HTML**.

```bash
# из корня репозитория:
PYTHONPATH=report python -m report.cli run post.md                 # цветной отчёт в терминал
PYTHONPATH=report python -m report.cli run post.md --judge offline # без LLM (детерминированно)
PYTHONPATH=report python -m report.cli run post.md --judge off     # только механика (canon-lens)
PYTHONPATH=report python -m report.cli run post.md --html out.html # + HTML-файл
PYTHONPATH=report python -m report.cli run post.md --json          # единый JSON-контракт
PYTHONPATH=report python -m report.cli run post.md --canon canon-lens/canon.digest.md  # другой канон
```

- вход — путь к текстовому черновику;
- `--judge live` (по умолчанию) — смысловой слой через `claude` CLI;
  `offline` — из `<файл>.judge.json`; `off` — только механика;
- выход — терминал (цвет, метка источника механика/судья/редакция, строка
  контекста с подсветкой нарушенного спана, `→ fix`, вердикт), либо `--html`,
  либо `--json`.

Терминальный вывод: рамка-заголовок, сводка со счётчиками и разбивкой по слоям,
находки по пунктам канона. Цвет отключается сам вне терминала или при `NO_COLOR`.
HTML — самодостаточный файл (тёмная тема, инлайн-CSS, без зависимостей).

## Ручной режим — `report merge`

Если выходы модулей уже получены отдельно, их можно слить напрямую:

```bash
PYTHONPATH=canon-lens python -m canon_lens.cli check post.md --json > mech.json
PYTHONPATH=judge      python -m judge.cli      check post.md --offline --json > judge.json
PYTHONPATH=report     python -m report.cli     merge mech.json judge.json          # терминал
PYTHONPATH=report     python -m report.cli     merge mech.json judge.json --json   # контракт
```

## Проверка

```bash
python report/tests/test_merge.py     # PASS 7/7  — мёрж, дедуп, by_kind
python report/tests/test_render.py    # PASS 5/5  — терминальный и HTML рендер
python report/e2e.py                  # 4/4       — сквозной CLI-прогон конвейера
```

Код возврата `run`/`merge`: `1` если есть `severity=error`, иначе `0`.

## Итоговый summary

К полям контракта добавлена разбивка `by_kind` (сколько находок механических,
судейских, redaction) — видно, какой слой что поймал:

```json
{"total": 3, "errors": 3, "warnings": 0, "points": [3, 4],
 "by_kind": {"mechanical": 1, "judgment-literal": 1, "judgment": 1}, "clean": false}
```

Только stdlib (Python ≥ 3.11). Папка изолирована. Секретов нет.

## Отношение к другим модулям

- вход — выходы `canon-lens` (HA59) и `judge` (MG7S);
- `report` — то, что делает из набора линтеров один продукт: одна картина
  нарушений по всему тексту, независимо от того, каким слоем найдено.
