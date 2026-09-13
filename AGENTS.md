# Repository Guidelines

## Project Structure & Module Organization

- `agtoosa/` contains the Python engine: `core/` defines domain models and lifecycle rules; `parser/` indexes source; `graph/` provides storage, queries, and visualization; `cli/` and `mcp/` expose entrypoints.
- Studio HTML, CSS, and JavaScript live in `agtoosa/graph/web/`. The VS Code/Cursor extension and its assets live in `extension/`.
- `tests/` contains automated tests. `docs/` holds the master plan, architecture, ADRs, and specifications. `scripts/` and `Formula/` support distribution.

## Build, Test, and Development Commands

Use Python 3.11+ and run commands from the repository root:

- `python3 -m venv .venv`, then `source .venv/bin/activate`: create and activate a POSIX development environment.
- `python -m pip install -e '.[dev]'`: install editable source and pytest.
- `python -m pytest`: run the complete test suite.
- `python -m pytest tests/test_parser.py -q`: run focused parser tests.
- `agtoosa graph build`: index the workspace into local SQLite storage.
- `agtoosa graph view --serve --open`: launch Studio on localhost port 8080 after indexing.
- `uv build`: build wheel and source distributions; requires uv.

## Coding Style & Naming Conventions

Use four-space Python indentation, `snake_case` modules/functions, `PascalCase` classes, and `UPPER_CASE` constants. Follow existing type hints and docstrings. JavaScript uses camelCase; match each file’s indentation. No formatter or linter command is configured; Pyrefly has project configuration. Preserve the dependency-free core and keep optional integrations optional.

## Testing Guidelines

Use pytest to run both pytest-style tests and `unittest.TestCase` suites. Name files `test_*.py` and test functions/methods `test_*`. Use temporary workspaces and databases to isolate filesystem changes. Add regression coverage for changed behavior, including relevant failure paths. No numeric coverage threshold is configured.

## Commit & Pull Request Guidelines

Use descriptive typed subjects matching history: `feat:`, `fix:`, `docs:`, `test:`, or `refactor:`; optional scopes include `feat(DEV-004): ...`. Explain the problem, behavior changes, and validation in PRs; link relevant issues/specifications and include screenshots for Studio or extension UI changes. Update architecture/specification documents when behavior changes and review the architecture CI report.

## Security & Generated Files

Keep secrets, `.env`, local `.agtoosa/` state, databases, virtual environments, and build artifacts out of commits. Preserve workspace-boundary checks and secret redaction.
