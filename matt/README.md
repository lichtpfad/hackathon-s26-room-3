# Matt content pipeline

Matt is an offline CLI for the three Room 3 acceptance examples.
It returns a complete content result instead of only a canon report.

## Runtime

Python 3.11 is the only runtime requirement.
The pipeline uses the Python standard library.

## Run one example

Run this command from the repository root:

```bash
python3 matt/run.py run examples/01-вычитка --canon examples/canon.md
```

Replace the example path with `examples/02-рилз` or `examples/03-дайджест`.

## Run acceptance

```bash
python3 matt/run.py accept examples --canon examples/canon.md
```

If all three examples pass, the command returns exit code `0`.

## Run executable specifications

Install the development dependency:

```bash
python3 -m pip install -r matt/requirements-dev.txt
```

Run the specifications:

```bash
python3 -m pytest matt/specs -q
```

## Contract chain

- `PRD.md` defines the product requirements.
- `CONTRACT.md` refines the requirements into acceptance clauses.
- `EXECUTABLE_SPECS.md` maps each acceptance clause to a scenario.
- `specs/test_examples.py` executes the scenarios.

## Limits

The pipeline supports the three Room 3 content types.
It does not provide general language generation for unrelated inputs.
