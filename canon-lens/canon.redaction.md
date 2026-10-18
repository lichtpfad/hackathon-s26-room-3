# Канон: безопасность публикации (redaction)

Отдельный проход перед выпуском наружу. Кейс заказчика: «публиковать лог сессии
небезопасно» — это его причина №2, почему находки не выходят. Запускать как
самостоятельную проверку поверх любого черновика, собранного из логов сессий,
git-истории, переписок.

```
python -m canon_lens.cli check <черновик> --canon canon-lens/canon.redaction.md --json
```

Всё — `category = redaction`, `point = 0`. `error` — публиковать нельзя пока не
вычищено; `warning` — проверить глазами.

```toml
[meta]
name = "Redaction — безопасность публикации"
source = "интервью HA59: заказчик A, причина №2"

[[rule]]
id = "abs-path-unix"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "error"
patterns = ['(?:/home/|/Users/|/root/|/opt/|/srv/|/var/(?!$))[\w./-]{2,}']
message = "абсолютный путь машины"
fix = "заменить условным путём (~/, <repo>/) или убрать"

[[rule]]
id = "abs-path-win"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "error"
patterns = ['[A-Za-z]:\\(?:Users|home)\\[\w.\\-]{2,}', '[A-Za-z]:\\[\w]+\\[\w.\\-]{2,}']
message = "абсолютный путь Windows (возможно с именем пользователя)"
fix = "убрать или заменить на <path>"

[[rule]]
id = "secret-token"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "error"
patterns = ['\b(?:ghp_|gho_|ghs_|github_pat_)[A-Za-z0-9_]{20,}', '\bsk-[A-Za-z0-9]{20,}', '\bAKIA[0-9A-Z]{16}\b', '\bxox[baprs]-[A-Za-z0-9-]{10,}', '\bAIza[0-9A-Za-z_-]{30,}']
message = "секрет / токен доступа"
fix = "убрать из текста; при реальной утечке — ротировать"

[[rule]]
id = "private-key-block"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "error"
patterns = ['-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----']
message = "блок приватного ключа"
fix = "удалить полностью"

[[rule]]
id = "env-assignment"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "error"
patterns = ['(?im)^[A-Z][A-Z0-9_]{2,}_(?:KEY|TOKEN|SECRET|PASSWORD|PWD|DSN|URL)\s*=\s*\S+', '(?i)(?:password|passwd|api[_-]?key|secret)\s*[:=]\s*["\x27]?\S{6,}']
message = "присваивание секрета в стиле .env"
fix = "заменить значение на <redacted>"

[[rule]]
id = "auth-header"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "error"
patterns = ['(?i)authorization:\s*(?:bearer|basic|token)\s+\S+', '(?i)\bbearer\s+[A-Za-z0-9._-]{16,}']
message = "заголовок авторизации с токеном"
fix = "убрать значение токена"

[[rule]]
id = "url-with-key"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "error"
patterns = ['[?&](?:api_?key|access_?token|token|key|secret)=[\w.-]{8,}']
message = "ключ в query-параметре URL"
fix = "вырезать параметр"

[[rule]]
id = "private-host"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "warning"
patterns = ['\b127\.0\.0\.1\b', '\blocalhost:\d+', '\b192\.168\.\d{1,3}\.\d{1,3}\b', '\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '\b[\w-]+\.local\b']
message = "внутренний адрес / хост"
fix = "проверить: не раскрывает ли внутреннюю сеть"

[[rule]]
id = "public-ip"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "warning"
patterns = ['(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\w.])']
message = "IP-адрес — проверить, не адрес ли это твоей машины"
fix = "заменить на <ip> если это не публичный пример"

[[rule]]
id = "repo-ref"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "warning"
patterns = ['github\.com[:/][\w.-]+/[\w.-]+', '(?i)\bgit@github\.com:[\w.-]+/[\w.-]+']
message = "ссылка на конкретный репозиторий — раскрывает название проекта"
fix = "обезличить, если репозиторий приватный"

[[rule]]
id = "email"
point = 0
kind = "regex_forbidden"
category = "redaction"
severity = "warning"
patterns = ['\b[\w.+-]+@[\w-]+\.[A-Za-z]{2,}\b']
message = "e-mail"
fix = "обезличить, если адрес не публичный"
```
