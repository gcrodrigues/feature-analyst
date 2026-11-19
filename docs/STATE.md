# Project state

## Current phase
Phase 0 · Single agent in Python, no framework. In progress.

Step plan for this phase:
1. Read-only tools confined to the target root (`list_files`, `read_file`, `search_code`) + tests — **done** (35 tests passing, pyright 0 errors, ruff clean)
2. OpenRouter client (httpx, sync) — **next**
3. Tool schemas + dispatcher (tool errors go back to the model as tool results)
4. Agent loop with iteration limit
5. Final answer validated with Pydantic (answer text + cited files that exist)
6. CLI command

## Done
- Project created with uv (Python 3.12, src layout)
- Dependencies: pydantic, python-dotenv; dev: pytest, ruff, pyright
- .env with OPENROUTER_API_KEY (not committed), .env.example committed
- CLAUDE.md with rules for Claude Code
- Public repository on GitHub
- `src/feature_analyst/tools.py`: `resolve_in_root`, `_collect_files` (shared walker), `list_files`, `read_file`, `search_code`, `ToolError`, `PathOutsideRootError`, `SearchMatch`
- `tests/test_tools.py`: 35 contract tests, including paths outside the root (`..`, absolute, sibling prefix, symlinks)

## Structure
- src/feature_analyst/tools.py: read-only tools
- tests/test_tools.py: tool tests
- docs/: state and per-phase notes

## Decisions
- Python 3.12, managed with uv
- Models via OpenRouter, API key in .env
- Code, README and commits in English
- Type checker: pyright in its default ("standard") mode, run as `uv run pyright`. Same engine as Pylance in VS Code. Unlike mypy's default, it checks the body of functions without annotations. Strict mode can be turned on later with `[tool.pyright] typeCheckingMode = "strict"`
- Typing rule: Pydantic for data coming from outside (model responses, tool arguments); dataclasses for data our own code creates (e.g. `SearchMatch`)
- HTTP client: httpx, synchronous, no OpenRouter SDK (the point of phase 0 is to see the raw request/response). Default httpx timeout is 5s, so LLM calls need an explicit longer timeout
- Sync over async in phase 0: the loop is sequential and tools are local file I/O, so async adds nothing yet
- Tool contract: tools take `root: Path` as first argument and return relative POSIX paths; every expected failure raises `ToolError`; escaping the root raises `PathOutsideRootError(ToolError)`
- Path confinement: `(root.resolve() / path).resolve()` then `is_relative_to(root)`; covers `..`, absolute paths, sibling-prefix folders and symlinks
- Raise vs skip: a bad request (missing folder, path outside root, empty query) raises `ToolError`; a single bad item inside a result (symlink leaving the root, binary file during search) is skipped
- `list_files` and `search_code` share `_collect_files`, so the walk and its protections exist once
- `search_code`: literal, case-insensitive substring search; `text` is the line stripped of surrounding whitespace; stops at `max_results`

## Open problems
- `read_text` can raise errors that are not `ToolError` (e.g. `PermissionError`, or a file deleted between listing and reading). Decide in step 3 whether the dispatcher catches `OSError` too or the tools convert it