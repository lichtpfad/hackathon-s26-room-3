# Matt executable specifications

## Runner

The specifications use pytest and pure run mode.
Pure mode reads local fixtures and does not use a network service.

Run the specifications from the repository root:

```bash
python3 -m pytest matt/specs -q
```

## Scenario structure

Each scenario uses three ordered phases: `Given`, `When`, and `Then`.
The Python test name contains the stable `ES-*` identifier.

## Scenarios

### ES-001: proofread report

Coverage: `AC-001`.

- Given: Example 01 and the shared canon.
- When: The pipeline processes the draft.
- Then: The report contains all required violations and exact locations.

### ES-002: rewritten draft

Coverage: `AC-002`, `AC-005`.

- Given: Example 01 and the shared canon.
- When: The pipeline rewrites the draft.
- Then: The result contains no violation from the active mechanical rules.

### ES-003: reel script

Coverage: `AC-003`, `AC-005`.

- Given: Example 02 and the shared canon.
- When: The pipeline creates the reel script.
- Then: The script has the required sections, source facts, and one action.

### ES-004: weekly digest

Coverage: `AC-004`, `AC-005`.

- Given: Example 03 and the shared canon.
- When: The pipeline creates the digest.
- Then: The digest includes required events and excludes the internal discussion.

### ES-005: aggregate acceptance

Coverage: `AC-006`.

- Given: The three canonical examples.
- When: The acceptance evaluator processes the set.
- Then: It reports three completed examples and no failed example.

### ES-006: incomplete set

Coverage: `AC-006`.

- Given: An examples directory without a required example.
- When: The acceptance evaluator processes the set.
- Then: It reports failure and the CLI returns a nonzero exit code.

### ES-007: contract coverage

Coverage: `AC-007`.

- Given: The executable specification matrix.
- When: The coverage test reads the matrix.
- Then: Every acceptance criterion has direct scenario coverage.

### ES-008: external canon change

Coverage: `AC-008`.

- Given: A copy of the canon with one additional forbidden word.
- When: The proofreader reads this canon and processes the original draft.
- Then: The report contains the additional forbidden word without a Python source change.

### ES-009: invalid example path

Coverage: `AC-009`.

- Given: An example path that does not exist.
- When: The user runs the CLI for this path.
- Then: The CLI returns exit code 2 and identifies the path.

## Direct coverage matrix

| Contract clause | Executable specification |
|---|---|
| `AC-001` | `ES-001` |
| `AC-002` | `ES-002` |
| `AC-003` | `ES-003` |
| `AC-004` | `ES-004` |
| `AC-005` | `ES-002`, `ES-003`, `ES-004` |
| `AC-006` | `ES-005`, `ES-006` |
| `AC-007` | `ES-007` |
| `AC-008` | `ES-008` |
| `AC-009` | `ES-009` |

## Evidence limits

These scenarios prove behavior for the three repository examples.
They do not prove general language understanding for unrelated source material.
