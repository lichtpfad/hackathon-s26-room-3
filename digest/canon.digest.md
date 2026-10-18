# Канон дайджеста недели

Отдельный канон под формат «дайджест». Тот же движок `canon-lens`, другой файл —
поведение меняется без правки кода. Отличие от synthetic-канона поста: в дайджесте
**числа не требуют источника в скобках** (источник — сами заметки недели), нет
запрета на CTA и нет лимита 1200 знаков; добавлен контроль числа пунктов (3–5).

```toml
[meta]
name = "Канон дайджеста недели (room-3)"
source = "examples/03-дайджест/expected.md"

[[rule]]
id = "no-emoji"
point = 1
kind = "emoji"
severity = "error"
message = "эмодзи запрещены (п.1)"
fix = "убрать эмодзи"

[[rule]]
id = "headline-lowercase"
point = 2
kind = "headline_case"
severity = "error"
message = "заголовок должен начинаться со строчной буквы (п.2)"
fix = "начать заголовок со строчной буквы"

[[rule]]
id = "no-antithesis"
point = 3
kind = "regex_forbidden"
severity = "error"
judgment_extends = true
patterns = [
  '(?i)\bне\s+(?:просто\s+|только\s+)?[^,.\n]{1,40},\s+а\s+\S',
  '(?i)\bэто\s+не\s+[^—\n]{1,50}\s*—\s*это\b',
]
message = "антитеза «не X, а Y» (п.3)"
fix = "переформулировать без противопоставления"

[[rule]]
id = "forbidden-words"
point = 4
kind = "stem_forbidden"
severity = "error"
stems = ["уникальн", "инновацион", "прорывн", "синерги"]
message = "запрещённое слово (п.4)"
fix = "убрать или заменить нейтральным словом"

[[rule]]
id = "digest-item-count"
point = 5
kind = "count_range"
severity = "warning"
patterns = ['(?m)^\s*[-*]\s+\S']
min = 3
max = 5
message = "в дайджесте должно быть 3–5 пунктов (п.5)"
fix = "оставить 3–5 самых значимых событий"

[[rule]]
id = "clericalese-phrases"
point = 6
kind = "phrase_forbidden"
severity = "error"
phrases = ["в рамках", "на сегодняшний день", "в связи с этим"]
message = "канцелярит (п.6)"
fix = "сказать проще"

[[rule]]
id = "clericalese-stems"
point = 6
kind = "stem_forbidden"
severity = "error"
stems = ["осуществл"]
message = "канцелярит (п.6)"
fix = "сказать проще: «делать», «идёт»"

# redaction — безопасность публикации (сырьё может быть внутренним)
[[rule]]
id = "redact-abs-path"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "error"
patterns = ['(?:/home/|/Users/|/root/|/opt/)[\w./-]{2,}', '[A-Za-z]:\\[\w.\\-]{2,}']
message = "абсолютный путь машины — вычистить перед публикацией"
fix = "убрать путь"

[[rule]]
id = "redact-secret"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "error"
patterns = ['\b(?:ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b']
message = "секрет или токен — вычистить"
fix = "убрать секрет"
```
