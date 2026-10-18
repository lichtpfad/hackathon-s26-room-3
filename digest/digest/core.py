"""Ядро digest: заметки → дайджест через LLM (claude CLI headless).

LLM-runtime по умолчанию — локальный `claude` CLI (ключ API не нужен), провайдер
сменяем (`llm_cmd`). Оффлайн-режим (детерминированная приёмка/CI): берётся
записанный дайджест из `<файл>.digest.md` рядом со входом.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

SYSTEM = (
    "Ты — редактор еженедельного дайджеста для команды. Из сырых заметок делаешь "
    "короткий дайджест. Пишешь только по фактам из заметок, ничего не выдумываешь. "
    "Отвечаешь ТОЛЬКО текстом дайджеста, без пояснений и без markdown-обёрток."
)

# Канон дайджеста — тезисно, из examples/03-дайджест/expected.md.
CANON_BRIEF = """Канон дайджеста:
- заголовок — со строчной буквы, одна строка;
- 3–5 пунктов списком, каждый ≤ 2 строк;
- включай только события, значимые для читателя (результат, изменение, факт);
  внутренние споры без решения — можно опустить или дать как «решение ожидается»;
- плохие новости (срывы, переносы) не прячь — упоминай честно;
- без эмодзи; без антитез «не X, а Y»; числа приводи как есть (источник — сами заметки)."""


class DigestError(RuntimeError):
    pass


def build_prompt(notes: str, canon_brief: str = CANON_BRIEF) -> str:
    return f"""{canon_brief}

СЫРЬЁ — заметки недели:
<<<
{notes}
>>>

Сделай дайджест недели строго по канону выше. Только текст дайджеста."""


def _call_claude(prompt: str, system: str, cmd: str, timeout: int) -> str:
    exe = shutil.which(cmd) or cmd
    argv = [exe, "-p", "--output-format", "json"]
    if system:
        argv += ["--append-system-prompt", system]
    try:
        proc = subprocess.run(argv, input=prompt, capture_output=True, text=True,
                              encoding="utf-8", timeout=timeout)
    except FileNotFoundError as e:
        raise DigestError(f"CLI {cmd!r} не найден — укажи llm_cmd или используй offline") from e
    except subprocess.TimeoutExpired as e:
        raise DigestError(f"таймаут LLM ({timeout}s)") from e
    if proc.returncode != 0:
        raise DigestError(f"LLM вернул код {proc.returncode}: {proc.stderr[:300]}")
    out = proc.stdout.strip()
    try:
        env = json.loads(out)
        if isinstance(env, dict) and "result" in env:
            return env["result"].strip()
    except json.JSONDecodeError:
        pass
    return out


def make_digest(notes: str, *, offline_source: str | Path | None = None,
                llm_cmd: str = "claude", timeout: int = 180,
                canon_brief: str = CANON_BRIEF) -> str:
    """Породить дайджест. offline_source задан → взять <источник>.digest.md."""
    if offline_source is not None:
        p = Path(str(offline_source) + ".digest.md")
        if not p.exists():
            raise DigestError(f"нет оффлайн-дайджеста: {p.name}")
        return p.read_text(encoding="utf-8").strip()
    return _call_claude(build_prompt(notes, canon_brief), SYSTEM, llm_cmd, timeout)
