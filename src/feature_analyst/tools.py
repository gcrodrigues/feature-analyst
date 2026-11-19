"""Read-only tools the agent can call. All of them are confined to a root folder."""
from dataclasses import dataclass
from pathlib import Path

IGNORED_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "build"}


class ToolError(Exception):
    """Base error for tool failures."""


class PathOutsideRootError(ToolError):
    """Raised when a path resolves outside the allowed root."""


@dataclass(frozen=True)
class SearchMatch:
    path: str
    line: int
    text: str


def resolve_in_root(root: Path, path: str) -> Path:
    """Return the absolute path of `path` inside `root`, or raise PathOutsideRootError."""
    resolved_root = root.resolve()
    resolved_path = (resolved_root / path).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise PathOutsideRootError(f"{path} is outside the target folder")
    return resolved_path


def _collect_files(root: Path, path: str) -> list[str]:
    """All files under `path`, sorted, as POSIX paths relative to `root`."""
    start = resolve_in_root(root, path)
    if not start.exists():
        raise ToolError(f"Path does not exist: {path}")
    if not start.is_dir():
        raise ToolError(f"Path is not a directory: {path}")
    resolved_root = root.resolve()
    files: list[str] = []
    for item in start.rglob("*"):
        relative = item.relative_to(resolved_root)                                
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        if not item.resolve().is_relative_to(resolved_root):
            continue
        if item.is_file():
            files.append(relative.as_posix())
    return sorted(files)


def list_files(root: Path, path: str = ".", max_entries: int = 500) -> list[str]:
    """List files under `path`, recursively, as sorted POSIX paths relative to `root`."""
    return _collect_files(root, path)[:max_entries]   


def read_file(root: Path, path: str, max_chars: int = 20_000) -> str:
    """Return the text of a file, cut at `max_chars` with a 'truncated' notice."""
    file = resolve_in_root(root, path)
    if not file.exists():
        raise ToolError(f"File does not exist: {path}")
    if not file.is_file():
        raise ToolError(f"Path is not a file: {path}")
    try:
        text = file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ToolError(f"File is not text (binary?): {path}")
    if len(text) > max_chars:
        return text[:max_chars] + f"\n\n[truncated: showing {max_chars} of {len(text)} characters]"
    return text


def search_code(
    root: Path, query: str, path: str = ".", max_results: int = 50
) -> list[SearchMatch]:
    """Find lines containing `query` (literal, case-insensitive) under `path`."""
    if not query.strip():
        raise ToolError("Search query is empty")
    resolved_root = root.resolve()
    needle = query.lower()
    matches: list[SearchMatch] = []
    for relative in _collect_files(root, path):
        file = resolved_root / relative
        try:
            lines = file.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, start=1):
            if needle in line.lower():
                matches.append(SearchMatch(path=relative, line=number, text=line.strip()))
                if len(matches) >= max_results:
                    return matches
    return matches