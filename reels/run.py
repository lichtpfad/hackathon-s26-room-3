"""Сквозная команда: статья -> факты -> сценарий рилза + отчёт.

    python reels/run.py reels/input/sostav-86369.md
    python reels/run.py 86369                      # сначала скачает статью
    python reels/run.py reels/input/               # все статьи папки

Между шагами руками не делается ничего — это и есть конвейер.

Добытчик фактов выбирается сам: есть `reels/extract` (ведёт meta1ex) — работаем
им; нет или он упал — включается запасной разбор `compose/stopgap_extract.py`.
Он беднее, зато без модели и без сети. Чем собрано, печатается в выводе и
пишется в отчёт.
"""

import argparse
import io
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reels.compose import build, lens  # noqa: E402
from reels.compose.stopgap_extract import extract as stopgap  # noqa: E402
from reels.tools import fetch_article  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HAS_EXTRACT = os.path.exists(os.path.join(HERE, "extract", "__main__.py"))


def run_extract(target, out_root, extra):
    """Прогнать экстрактор meta1ex его собственным интерфейсом."""
    cmd = [sys.executable, "-m", "reels.extract", target, "-o", out_root] + extra
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().split("\n")[-1:]
        return False, " ".join(tail)
    return True, ""


def run_stopgap(paths, out_root):
    for path in paths:
        data = stopgap(path)
        article_id = data["source"]["id"].replace("sostav-", "")
        data["source"]["id"] = article_id
        out_dir = os.path.join(out_root, article_id)
        os.makedirs(out_dir, exist_ok=True)
        io.open(os.path.join(out_dir, "facts.json"), "w", encoding="utf-8",
                newline="\n").write(json.dumps(data, ensure_ascii=False, indent=2))


def source_path(article_id, input_dir):
    for name in (f"sostav-{article_id}.md", f"{article_id}.md"):
        candidate = os.path.join(input_dir, name)
        if os.path.exists(candidate):
            return candidate
    return None


def compose_one(facts_path, canon, input_dir, extractor):
    data = build.load(facts_path)
    out_dir = os.path.dirname(facts_path)
    article_id = data["source"].get("id", os.path.basename(out_dir))
    origin = source_path(article_id, input_dir)
    source_text = io.open(origin, encoding="utf-8").read() if origin else None
    script_path = os.path.join(out_dir, "script.md")

    try:
        script, used, template_cta = build.render(data, canon)
    except build.Refusal as refusal:
        text = build.report(data, canon, refusal=str(refusal),
                            source_text=source_text, extractor=extractor)
        io.open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8",
                newline="\n").write(text)
        if os.path.exists(script_path):
            os.remove(script_path)
        return article_id, None, len(data["facts"]), None

    io.open(script_path, "w", encoding="utf-8", newline="\n").write(script)
    text = build.report(data, canon, script=script, used=used,
                        template_cta=template_cta, source_text=source_text,
                        extractor=extractor)
    io.open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8",
            newline="\n").write(text)
    total = round(sum(secs for _, secs, _ in build.timing(script)), 1)
    return article_id, used, len(data["facts"]), total


def main(argv=None):
    ap = argparse.ArgumentParser(description="статья -> сценарий рилза")
    ap.add_argument("target", help="файл статьи, папка со статьями или id статьи sostav")
    ap.add_argument("--canon", default="examples/canon.md")
    ap.add_argument("-o", "--out", default="reels/out")
    ap.add_argument("--input-dir", default="reels/input")
    ap.add_argument("--no-llm", action="store_true", help="экстрактор без модели")
    ap.add_argument("--stopgap", action="store_true", help="принудительно запасной разбор")
    args = ap.parse_args(argv)

    try:
        canon = lens.load(args.canon)
    except (OSError, ValueError, lens.CanonUnreadable) as exc:
        print(f"канон не прочитан: {exc}", file=sys.stderr)
        return 2

    target = args.target
    if not os.path.exists(target):
        print(f"качаю статью {target}")
        target, _, _ = fetch_article.fetch(target, args.input_dir)

    paths = ([os.path.join(target, n) for n in sorted(os.listdir(target)) if n.endswith(".md")]
             if os.path.isdir(target) else [target])
    if not paths:
        print("статей не найдено", file=sys.stderr)
        return 2

    extractor, why = "stopgap", ""
    if HAS_EXTRACT and not args.stopgap:
        ok, why = run_extract(target, args.out, ["--no-llm"] if args.no_llm else [])
        extractor = "reels.extract" if ok else "stopgap"
    if extractor == "stopgap":
        if why:
            print(f"экстрактор не отработал ({why}) — беру запасной разбор")
        run_stopgap(paths, args.out)

    print(f"добытчик фактов: {extractor} · движок канона: {lens.ENGINE}")
    for path in paths:
        article_id = os.path.splitext(os.path.basename(path))[0].replace("sostav-", "")
        facts_path = os.path.join(args.out, article_id, "facts.json")
        if not os.path.exists(facts_path):
            print(f"  {article_id}: фактов нет, пропускаю")
            continue
        article_id, used, total, secs = compose_one(facts_path, canon,
                                                    args.input_dir, extractor)
        where = os.path.join(args.out, article_id)
        if used is None:
            print(f"  {article_id}: контента нет · фактов {total} · {where}/report.md")
        else:
            print(f"  {article_id}: сценарий из {len(used)} фактов "
                  f"(добыто {total}) · {secs} с · {where}/script.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
