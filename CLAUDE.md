# feature-analyst

Multi-agent system in Python with LangGraph. This is a learning project:
the owner writes the core code himself.

## Rules
- Do not write or rewrite agent state, graph nodes, edges or agent prompts.
  If asked, explain the approach and point to what to change instead.
- You may write: project setup, tests, fixtures, Docker, CI and mechanical refactors.
- Read docs/STATE.md before starting any task.

## Commands
- Run: uv run python -m feature_analyst
- Test: uv run pytest
- Lint: uv run ruff check .