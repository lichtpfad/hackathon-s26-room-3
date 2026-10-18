"""LLM-адаптер. По умолчанию — локальный `claude` CLI (Claude Code) в headless
режиме, ключ API не нужен. Провайдер сменяем: любая команда, читающая промпт со
stdin и печатающая текст ответа в stdout, подходит (`--llm-cmd`).

Оффлайн-режим (для детерминированной приёмки и тестов): вместо вызова модели
берём заранее записанный вердикт из `<файл>.judge.json` рядом с входом.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class LLMError(RuntimeError):
    pass


def _extract_json_array(raw: str) -> list[dict]:
    """Выдрать первый JSON-массив из ответа модели (терпимо к обёрткам)."""
    s = raw.strip()
    if s.startswith("```"):                              # ```json ... ```
        s = s.strip("`")
        s = s[s.find("\n") + 1:] if "\n" in s else s
    a, b = s.find("["), s.rfind("]")
    if a < 0 or b < 0 or b < a:
        raise LLMError(f"в ответе нет JSON-массива: {raw[:200]!r}")
    try:
        data = json.loads(s[a:b + 1])
    except json.JSONDecodeError as e:
        raise LLMError(f"невалидный JSON в ответе: {e}: {s[a:b+1][:200]!r}") from e
    if not isinstance(data, list):
        raise LLMError("ожидался JSON-массив находок")
    return data


def call_claude(prompt: str, system: str, cmd: str = "claude", timeout: int = 120) -> str:
    """Вызвать claude CLI headless. Возвращает сырой текст ответа модели."""
    exe = shutil.which(cmd) or cmd
    argv = [exe, "-p", "--output-format", "json"]
    if system:
        argv += ["--append-system-prompt", system]
    try:
        proc = subprocess.run(
            argv, input=prompt, capture_output=True, text=True,
            encoding="utf-8", timeout=timeout,
        )
    except FileNotFoundError as e:
        raise LLMError(f"CLI {cmd!r} не найден — укажи --llm-cmd или --offline") from e
    except subprocess.TimeoutExpired as e:
        raise LLMError(f"таймаут LLM ({timeout}s)") from e
    if proc.returncode != 0:
        raise LLMError(f"LLM вернул код {proc.returncode}: {proc.stderr[:300]}")
    # claude --output-format json оборачивает ответ в {"result": "...", ...}
    out = proc.stdout.strip()
    try:
        env = json.loads(out)
        if isinstance(env, dict) and "result" in env:
            return env["result"]
    except json.JSONDecodeError:
        pass
    return out


def findings_via_llm(prompt: str, system: str, cmd: str = "claude",
                     timeout: int = 120) -> list[dict]:
    return _extract_json_array(call_claude(prompt, system, cmd, timeout))


def findings_offline(input_path: str | Path) -> list[dict]:
    """Прочитать записанный вердикт `<input>.judge.json`. Нет файла → []."""
    p = Path(str(input_path) + ".judge.json")
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "findings" in data:
        return data["findings"]
    if isinstance(data, list):
        return data
    raise LLMError(f"{p.name}: ожидался список находок или {{'findings': [...]}}")
