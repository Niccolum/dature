# dature — type-safe config loader for Python dataclasses

## Commands

- `prek run --all-files` (alias: `prek run -a`) — lint + type check (ruff + mypy)
- `uv run pytest -q` — run tests
- `uv run pytest tests/path/to/test.py::TestClass::test_func -xvs` — single test
- `uv build` — build package

## Slash commands

- `/done` — pre-finish checklist: run prek + tests + verify changelog fragment
- `/arch` — architecture reference (module map, Source hierarchy, test conventions)
- `/new-source` — step-by-step guide for adding a new Source type

## Rules

- Zero required deps. Optional via extras, imported inside the function that needs them
- Type hints everywhere. `py.typed` is required
- Public API is minimal — don't break it without discussion (`__init__.py` is the contract)
- Errors must be human-readable with field path to the problem
- Google-style docstrings, English
- **IMPORTANT:** never finish without running `/done` (prek + tests + changelog check)
- **IMPORTANT:** every bugfix needs a regression test
- **IMPORTANT:** every change to `src/` needs a `changes/` fragment for towncrier
