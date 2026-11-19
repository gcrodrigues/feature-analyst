"""Contract tests for the read-only tools in feature_analyst.tools.

Every tool is confined to a target root folder. A path that resolves outside
the root must raise PathOutsideRootError; every other expected failure
(missing file, binary file, empty query...) raises ToolError, so the agent
loop can catch a single exception type and report it back to the model.
"""

import sys
from pathlib import Path

import pytest

from feature_analyst.tools import (
    PathOutsideRootError,
    ToolError,
    list_files,
    read_file,
    resolve_in_root,
    search_code,
)

needs_symlinks = pytest.mark.skipif(
    sys.platform == "win32", reason="symlinks need extra privileges on Windows"
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A small fake repository, plus a sibling folder that must stay unreachable."""
    root = tmp_path / "repo"
    (root / "src" / "api").mkdir(parents=True)
    (root / "src" / "api" / "routes.py").write_text(
        "from fastapi import APIRouter\n\nrouter = APIRouter()\n\n# TODO: add auth\n",
        encoding="utf-8",
    )
    (root / "src" / "main.py").write_text(
        "def main():\n    print('hello')\n", encoding="utf-8"
    )
    (root / "README.md").write_text("# Demo repo\n", encoding="utf-8")
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\xff\xfe")

    # Noise the tools must skip.
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core] TODO\n", encoding="utf-8")
    (root / "node_modules" / "lib").mkdir(parents=True)
    (root / "node_modules" / "lib" / "index.js").write_text(
        "// TODO\n", encoding="utf-8"
    )

    # Outside the root. Its name shares the root's prefix on purpose.
    evil = tmp_path / "repo-evil"
    evil.mkdir()
    (evil / "secret.txt").write_text("TODO: leaked secret\n", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("outside\n", encoding="utf-8")

    return root


# --- resolve_in_root -------------------------------------------------------


def test_resolve_relative_path_inside_root(repo: Path) -> None:
    resolved = resolve_in_root(repo, "src/main.py")
    assert resolved == (repo / "src" / "main.py").resolve()


def test_resolve_dot_is_the_root(repo: Path) -> None:
    assert resolve_in_root(repo, ".") == repo.resolve()


def test_resolve_dotdot_inside_root_is_allowed(repo: Path) -> None:
    resolved = resolve_in_root(repo, "src/api/../main.py")
    assert resolved == (repo / "src" / "main.py").resolve()


@pytest.mark.parametrize(
    "bad_path",
    [
        "../outside.txt",
        "src/../../outside.txt",
        "../repo-evil/secret.txt",  # defeats a naive str.startswith check
    ],
)
def test_resolve_rejects_dotdot_escape(repo: Path, bad_path: str) -> None:
    with pytest.raises(PathOutsideRootError):
        resolve_in_root(repo, bad_path)


def test_resolve_rejects_absolute_path_outside_root(repo: Path) -> None:
    outside = str(repo.parent / "outside.txt")
    with pytest.raises(PathOutsideRootError):
        resolve_in_root(repo, outside)


def test_resolve_accepts_absolute_path_inside_root(repo: Path) -> None:
    inside = str(repo / "README.md")
    assert resolve_in_root(repo, inside) == (repo / "README.md").resolve()


@needs_symlinks
def test_resolve_rejects_symlink_pointing_outside(repo: Path) -> None:
    (repo / "sneaky.txt").symlink_to(repo.parent / "outside.txt")
    with pytest.raises(PathOutsideRootError):
        resolve_in_root(repo, "sneaky.txt")


def test_path_outside_root_error_is_a_tool_error() -> None:
    assert issubclass(PathOutsideRootError, ToolError)


# --- list_files ------------------------------------------------------------


def test_list_files_returns_sorted_relative_posix_paths(repo: Path) -> None:
    assert list_files(repo) == [
        "README.md",
        "logo.png",
        "src/api/routes.py",
        "src/main.py",
    ]


def test_list_files_in_subfolder_keeps_paths_relative_to_root(repo: Path) -> None:
    assert list_files(repo, "src/api") == ["src/api/routes.py"]


def test_list_files_respects_max_entries(repo: Path) -> None:
    assert len(list_files(repo, max_entries=2)) == 2


def test_list_files_rejects_path_outside_root(repo: Path) -> None:
    with pytest.raises(PathOutsideRootError):
        list_files(repo, "../repo-evil")


def test_list_files_missing_folder_raises_tool_error(repo: Path) -> None:
    with pytest.raises(ToolError):
        list_files(repo, "does/not/exist")


def test_list_files_on_a_file_raises_tool_error(repo: Path) -> None:
    with pytest.raises(ToolError):
        list_files(repo, "README.md")


@needs_symlinks
def test_list_files_skips_symlinks_pointing_outside(repo: Path) -> None:
    (repo / "sneaky.txt").symlink_to(repo.parent / "outside.txt")
    (repo / "sneaky_dir").symlink_to(repo.parent / "repo-evil", target_is_directory=True)
    result = list_files(repo)
    assert "sneaky.txt" not in result
    assert not any(p.startswith("sneaky_dir") for p in result)


# --- read_file -------------------------------------------------------------


def test_read_file_returns_content(repo: Path) -> None:
    assert read_file(repo, "src/main.py") == "def main():\n    print('hello')\n"


def test_read_file_truncates_long_files(repo: Path) -> None:
    (repo / "big.txt").write_text("a" * 1000, encoding="utf-8")
    result = read_file(repo, "big.txt", max_chars=100)
    assert result.startswith("a" * 100)
    assert "a" * 101 not in result
    assert "truncated" in result.lower()


def test_read_file_rejects_path_outside_root(repo: Path) -> None:
    with pytest.raises(PathOutsideRootError):
        read_file(repo, "../repo-evil/secret.txt")


def test_read_file_missing_file_raises_tool_error(repo: Path) -> None:
    with pytest.raises(ToolError):
        read_file(repo, "nope.py")


def test_read_file_on_a_folder_raises_tool_error(repo: Path) -> None:
    with pytest.raises(ToolError):
        read_file(repo, "src")


def test_read_file_binary_raises_tool_error(repo: Path) -> None:
    with pytest.raises(ToolError):
        read_file(repo, "logo.png")


# --- search_code -----------------------------------------------------------


def test_search_code_finds_matches_with_one_based_line_numbers(repo: Path) -> None:
    matches = search_code(repo, "TODO")
    assert len(matches) == 1
    assert matches[0].path == "src/api/routes.py"
    assert matches[0].line == 5
    assert matches[0].text == "# TODO: add auth"


def test_search_code_is_case_insensitive(repo: Path) -> None:
    matches = search_code(repo, "apirouter")
    assert [(m.path, m.line) for m in matches] == [
        ("src/api/routes.py", 1),
        ("src/api/routes.py", 3),
    ]


def test_search_code_treats_query_as_literal_text(repo: Path) -> None:
    # "print(" is an invalid regex; a literal search must still work.
    matches = search_code(repo, "print(")
    assert [(m.path, m.line) for m in matches] == [("src/main.py", 2)]


def test_search_code_skips_ignored_folders_and_binaries(repo: Path) -> None:
    paths = {m.path for m in search_code(repo, "TODO")}
    assert not any(p.startswith((".git/", "node_modules/")) for p in paths)
    assert "logo.png" not in paths


def test_search_code_respects_max_results(repo: Path) -> None:
    (repo / "many.txt").write_text("hit\n" * 20, encoding="utf-8")
    assert len(search_code(repo, "hit", max_results=5)) == 5


def test_search_code_limited_to_subfolder(repo: Path) -> None:
    matches = search_code(repo, "def", path="src/api")
    assert matches == []


def test_search_code_rejects_path_outside_root(repo: Path) -> None:
    with pytest.raises(PathOutsideRootError):
        search_code(repo, "TODO", path="../repo-evil")


@pytest.mark.parametrize("query", ["", "   "])
def test_search_code_empty_query_raises_tool_error(repo: Path, query: str) -> None:
    with pytest.raises(ToolError):
        search_code(repo, query)


@needs_symlinks
def test_search_code_does_not_follow_symlinks_outside(repo: Path) -> None:
    (repo / "sneaky_dir").symlink_to(repo.parent / "repo-evil", target_is_directory=True)
    matches = search_code(repo, "leaked")
    assert matches == []


def test_tools_accept_root_as_relative_path(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The CLI will pass whatever the user typed, e.g. "../mx-clinics-api".
    monkeypatch.chdir(repo.parent)
    assert "src/main.py" in list_files(Path("repo"))
    assert read_file(Path("repo"), "README.md") == "# Demo repo\n"


def test_search_code_strips_indentation_from_text(repo: Path) -> None:
    (repo / "indented.py").write_text("def f():\n    return 'needle'\n", encoding="utf-8")
    matches = search_code(repo, "needle")
    assert [m.text for m in matches] == ["return 'needle'"]