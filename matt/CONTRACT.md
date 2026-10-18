# Matt content pipeline contract

## Contract purpose

This contract refines the requirements in `PRD.md`.
Executable specifications provide evidence for these clauses.

## Input contract

### T-001: example directory

An example directory MUST contain `input/` and one or more UTF-8 text files.
The directory name MUST start with `01`, `02`, or `03`.

### T-002: canon file

The canon file MUST be UTF-8 Markdown.
The pipeline MUST read this file for each command.

### T-003: accepted commands

The CLI MUST accept these command forms:

```text
python3 matt/run.py run <example-directory> --canon <canon-file>
python3 matt/run.py accept <examples-directory> --canon <canon-file>
```

## Output contract

### T-004: result object

Each pipeline result has these fields:

- `example`: The example identifier.
- `kind`: One of `proofread`, `reel`, or `digest`.
- `content`: The generated Markdown.
- `evidence`: Structured facts about the result.

### T-005: CLI output

The `run` command MUST write the generated Markdown to standard output.
The command MUST return exit code `0` for a complete result.

### T-006: acceptance output

The `accept` command MUST show one `PASS` or `FAIL` line for each example.
The final line MUST use the form `passed N of M`.

### T-007: invalid input

The CLI MUST return exit code `2` for an invalid path or an invalid command input.
It MUST write a concise error message to standard error.

## Acceptance criteria

### AC-001: canon-driven proofread report

For example 01, the report MUST identify canon clauses 1, 2, 3, 4, 6, 7, and 8.

The report MUST identify all three forbidden words.
It MUST identify both forms of clerical language.
Each report item MUST contain an exact source location.

Coverage: `R-002`, `R-003`, `T-001`, `T-002`, `T-004`.

### AC-002: clean rewritten draft

For example 01, the output MUST contain a rewritten draft.
The rewritten draft MUST have no violation that the pipeline reports.

Coverage: `R-003`, `T-004`, `T-005`.

### AC-003: reel structure and facts

For example 02, the output MUST contain these timed sections:

- Hook from 0 to 3 seconds.
- Main section from 3 to 22 seconds.
- Call to action from 22 to 30 seconds.

The script MUST include three forgotten subscriptions, two minutes of setup, and support for any email service.
It MUST contain no invented product number.

Coverage: `R-004`, `T-001`, `T-004`, `T-005`.

### AC-004: digest selection

For example 03, the output MUST contain three to five digest items.
It MUST include the dark theme, 120 registrations, the landing-page qualification, and the response-time change from six hours to two.

The output MUST state that the bank integration moved to October.
It MUST exclude the unresolved internal price discussion.

Coverage: `R-005`, `T-001`, `T-004`, `T-005`.

### AC-005: canon compliance of generated content

Generated content MUST have a lowercase heading.
It MUST have no emoji, forbidden word, or prohibited antithesis.
If the content type needs a call to action, the content MUST end with one concrete action.

Coverage: `R-002`, `R-003`, `R-004`, `R-005`.

### AC-006: truthful aggregate result

If all criteria pass, the acceptance command MUST report `passed 3 of 3`.
If a required example is absent or incomplete, the command MUST return a nonzero exit code.

Coverage: `R-001`, `R-006`, `T-003`, `T-006`.

### AC-007: direct specification coverage

Each `AC-*` clause MUST have direct coverage from an `ES-*` scenario.
The specification matrix MUST not use an indirect requirement as evidence.

Coverage: `R-007`.

### AC-008: canon change without a code change

If a user adds a forbidden word to clause 4, the proofreader MUST report that word.
The user MUST NOT change Python source for this behavior.

Coverage: `R-002`, `T-002`.

### AC-009: invalid path result

If the user selects an absent example path, the CLI MUST return exit code `2`.
The error text MUST identify the absent path.

Coverage: `R-001`, `T-003`, `T-007`.

## Error contract

The `PipelineError` type represents an input-contract error inside the Python API.
The CLI maps this error to `T-007`.

## Change contract

A canon change can change validation and rewriting behavior.
A contract change MUST update its mapped executable specifications in the same commit.
