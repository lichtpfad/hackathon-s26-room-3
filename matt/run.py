#!/usr/bin/env python3
"""CLI for the Matt content pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

try:
    from .pipeline import PipelineError, accept_all, evaluate, generate, load_canon
except ImportError:  # Direct script execution from matt/run.py.
    from pipeline import PipelineError, accept_all, evaluate, generate, load_canon


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="matt", description="Room 3 offline content pipeline")
    commands = parser.add_subparsers(dest="command", required=True)

    run_parser = commands.add_parser("run", help="process one example")
    run_parser.add_argument("example_dir")
    run_parser.add_argument("--canon", required=True)

    accept_parser = commands.add_parser("accept", help="process all acceptance examples")
    accept_parser.add_argument("examples_dir")
    accept_parser.add_argument("--canon", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "run":
            result = generate(args.example_dir, args.canon)
            acceptance = evaluate(result, load_canon(args.canon))
            print(result.content, end="")
            if not acceptance.passed:
                for failure in acceptance.failures:
                    print(f"FAIL: {failure}", file=sys.stderr)
                return 1
            return 0

        results = accept_all(args.examples_dir, args.canon)
        for result in results:
            state = "PASS" if result.passed else "FAIL"
            print(f"{state} {result.example}")
            for failure in result.failures:
                print(f"  - {failure}")
        passed = sum(result.passed for result in results)
        print(f"passed {passed} of {len(results)}")
        return 0 if passed == len(results) == 3 else 1
    except (OSError, UnicodeError, PipelineError) as error:
        print(f"matt: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
