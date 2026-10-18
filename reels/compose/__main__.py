"""python -m reels.compose facts.json examples/canon.md -o reels/out/<id>/

Код возврата 0 и при отказе: отказ — штатный результат, а не ошибка.
Ненулевой код только на сломанном входе.
"""

import argparse
import io
import os
import sys

from . import build
from . import lens


def main(argv=None):
    ap = argparse.ArgumentParser(description="сценарий рилза из facts.json по канону")
    ap.add_argument("facts", help="путь к facts.json")
    ap.add_argument("canon", nargs="?", default="examples/canon.md", help="путь к canon.md")
    ap.add_argument("-o", "--out", default=".", help="куда класть script.md и report.md")
    args = ap.parse_args(argv)

    try:
        data = build.load(args.facts)
        canon = lens.load(args.canon)
    except (OSError, ValueError, lens.CanonUnreadable) as exc:
        print(f"вход сломан: {exc}", file=sys.stderr)
        return 2

    os.makedirs(args.out, exist_ok=True)
    script_path = os.path.join(args.out, "script.md")

    try:
        script, used, template_cta = build.render(data, canon)
    except build.Refusal as refusal:
        text = build.report(data, canon, refusal=str(refusal))
        io.open(os.path.join(args.out, "report.md"), "w", encoding="utf-8",
                newline="\n").write(text)
        if os.path.exists(script_path):
            os.remove(script_path)
        print(f"контента нет — {refusal}")
        return 0

    io.open(script_path, "w", encoding="utf-8", newline="\n").write(script)
    text = build.report(data, canon, script=script, used=used, template_cta=template_cta)
    io.open(os.path.join(args.out, "report.md"), "w", encoding="utf-8",
            newline="\n").write(text)
    print(f"ok {script_path} · фактов {len(used)} · канон: {canon}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
