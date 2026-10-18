# Matt content pipeline PRD

## Product goal

The Matt content pipeline converts source notes into a useful content draft.
It also applies the repository content canon.

The pipeline operates without a network connection or an external AI service.
This mode makes the demonstration repeatable.

## Source authority

The product uses these sources in this order:

1. The files in `examples/` and their `expected.md` files.
2. The rules in `examples/canon.md`.
3. The Room 3 repository README.
4. Customer interview notes.

## Users and problems

Content authors spend time on three repeated tasks:

- They find canon violations and rewrite a draft.
- They convert meeting notes into a short reel script.
- They convert weekly notes into a concise digest.

## Requirements

### R-001: common CLI

The product MUST provide one CLI for each example and for the complete acceptance set.

### R-002: external canon

The CLI MUST read the canon from a file that the user selects.
The core canon rules MUST stay outside the Python source.

### R-003: proofreading result

For a proofreading input, the product MUST return a violation report and a rewritten draft.

Each violation MUST contain the clause number, exact quote, line, and column.
The rewritten draft MUST remove every reported violation.

### R-004: reel result

For reel notes, the product MUST return a 30-second script.

The script MUST contain a hook, a main section, and one concrete call to action.
The main section MUST use two or three facts from the source notes.

### R-005: digest result

For weekly notes, the product MUST return a digest with three to five items.

The digest MUST include material product events and adverse events.
It MUST exclude an unresolved internal price discussion.

### R-006: truthful acceptance

The acceptance command MUST count complete examples, not individual rule checks.
If an example is incomplete, the command MUST return a nonzero exit code.

### R-007: traceability

Each acceptance criterion MUST map to one or more executable specifications.
An executable specification MUST name the clauses that it covers.

## Constraints

- Runtime code MUST use Python 3.11 and the standard library.
- Runtime code MUST NOT call a network service.
- The implementation MUST stay in `matt/`.
- The implementation MUST NOT change `examples/` or `examples/canon.md`.
- Output facts MUST come from the selected input.

## Success measure

The command `python3 matt/run.py accept examples --canon examples/canon.md` reports `passed 3 of 3`.
The command returns exit code `0` only for this complete result.

## Out of scope

- Video processing.
- Audio transcription.
- General natural-language generation for unknown content types.
- A web interface.
- Publication to a social platform.
