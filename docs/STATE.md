# Project state

## Current phase
Phase 0 · Single agent in Python, no framework. Not started.

## Done
- Project created with uv (Python 3.12, src layout)
- Dependencies: pydantic, python-dotenv; dev: pytest, ruff
- .env with OPENROUTER_API_KEY (not committed), .env.example committed
- CLAUDE.md with rules for Claude Code
- Public repository on GitHub

## Structure
- src/feature_analyst/: system code (empty)
- tests/: pytest tests (empty)
- docs/: state and per-phase notes

## Decisions
- Python 3.12, managed with uv
- Models via OpenRouter, API key in .env
- Code, README and commits in English
- HTTP client for OpenRouter: to be decided in phase 0

## Open problems
None.