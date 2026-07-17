import argparse
import dataclasses
import difflib
import json
import os
import re
from pathlib import Path
from typing import Optional


WIKI_ROOT_ENV = "TEAM_PITFALLS_LLM_WIKI_ROOT"
CONFIG_ENV = "TEAM_PITFALLS_CONFIG"
DEFAULT_CONFIG_PATH = Path("~/.config/team-pitfalls/config.json")

INDEX_ROW_RE = re.compile(
    r"^\|\s*((?:P|G|C)-\d{3})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$"
)
ENTRY_HEADER_RE = re.compile(r"^###\s+((?:P|G|C)-\d{3})\s*:\s*(.+?)\s*$")


@dataclasses.dataclass(frozen=True)
class IndexRow:
    entry_id: str
    kind: str
    title: str
    tags: str
    file_path: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def _unified_diff(before: str, after: str, from_name: str, to_name: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=from_name,
            tofile=to_name,
        )
    )


def _wiki_root_from_config() -> str:
    raw_config_path = os.environ.get(CONFIG_ENV, "").strip()
    config_path = Path(raw_config_path).expanduser() if raw_config_path else DEFAULT_CONFIG_PATH.expanduser()
    if not config_path.exists():
        return ""
    parsed = json.loads(_read_text(config_path))
    if not isinstance(parsed, dict):
        raise SystemExit(f"config must be a JSON object: {config_path}")
    return str(parsed.get("wiki_root", "")).strip()


def _missing_wiki_root_message() -> str:
    return "\n".join(
        [
            "Team Pitfalls LLM Wiki root 未配置，不能删除沉淀条目。",
            "",
            "请先主动配置外部 Wiki 目录，然后重新运行本命令。可任选一种方式：",
            "1. 单次执行：传入 --wiki-root <path>",
            f"2. 当前 shell：export {WIKI_ROOT_ENV}=<path>",
            f"3. 持久配置：写入 {DEFAULT_CONFIG_PATH.expanduser()}",
            "",
            "配置文件示例：",
            '{',
            '  "wiki_root": "/path/to/team-pitfalls-wiki"',
            '}',
        ]
    )


def _resolve_wiki_root(raw_path: Optional[str]) -> Path:
    configured_path = (raw_path or os.environ.get(WIKI_ROOT_ENV, "") or _wiki_root_from_config()).strip()
    if not configured_path:
        raise SystemExit(_missing_wiki_root_message())
    return Path(configured_path).expanduser().resolve()


def _parse_index_rows(index_text: str) -> list[IndexRow]:
    rows: list[IndexRow] = []
    for line in index_text.splitlines():
        match = INDEX_ROW_RE.match(line)
        if not match:
            continue
        rows.append(
            IndexRow(
                entry_id=match.group(1).strip(),
                kind=match.group(2).strip(),
                title=match.group(3).strip(),
                tags=match.group(4).strip(),
                file_path=match.group(5).strip(),
            )
        )
    return rows


def _index_header() -> str:
    return "\n".join(
        [
            "# Team Pitfalls Index",
            "",
            "LLM Wiki root for reusable pitfalls, repo glossary, and AI correction records.",
            "",
            "## Entries",
            "",
            "| ID | Kind | Title | Tags | File |",
            "|---|---|---|---|---|",
            "",
        ]
    )


def _write_index(wiki_root: Path, rows: list[IndexRow]) -> None:
    lines = [_index_header().rstrip(), ""]
    for row in sorted(rows, key=lambda item: item.entry_id):
        lines.append(f"| {row.entry_id} | {row.kind} | {row.title} | {row.tags or 'TODO'} | {row.file_path} |")
    lines.append("")
    _write_text(wiki_root / "index.md", "\n".join(lines))


def _write_llms_txt(wiki_root: Path, rows: list[IndexRow]) -> None:
    repo_names = sorted(
        {
            row.file_path.split("/")[1]
            for row in rows
            if row.file_path.startswith("repos/") and len(row.file_path.split("/")) >= 3
        }
    )
    lines = [
        "# Team Pitfalls",
        "",
        "> Reusable pitfalls and repo-specific knowledge for coding agents.",
        "",
        "## Entry Points",
        "",
        "- [Index](index.md): canonical list of all records",
        "- [Common Pitfalls](pitfalls/): cross-project reusable pitfalls",
        "- [Repositories](repos/): repo-specific glossary and corrections",
        "",
        "## Reading Order",
        "",
        "1. Read `index.md` first.",
        "2. Open only the matched page under `pitfalls/` or `repos/`.",
        "3. Prefer repo-specific records over common records when both apply.",
        "",
    ]
    if repo_names:
        lines.extend(["## Known Repositories", ""])
        lines.extend(f"- [{repo}](repos/{repo}/index.md)" for repo in repo_names)
        lines.append("")
    _write_text(wiki_root / "llms.txt", "\n".join(lines))


def _find_by_title(rows: list[IndexRow], title: str) -> Optional[IndexRow]:
    expected = title.strip()
    for row in rows:
        if row.title == expected:
            return row
    return None


def _find_by_id(rows: list[IndexRow], entry_id: str) -> Optional[IndexRow]:
    expected = entry_id.strip()
    for row in rows:
        if row.entry_id == expected:
            return row
    return None


def _remove_entry_block(doc_text: str, entry_id: str) -> str:
    lines = doc_text.splitlines(keepends=True)
    start: Optional[int] = None
    for index, line in enumerate(lines):
        if line.startswith(f"### {entry_id}:"):
            start = index
            break
    if start is None:
        return doc_text

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if ENTRY_HEADER_RE.match(lines[index].strip()):
            end = index
            break

    while start > 0 and lines[start - 1].strip() == "":
        start -= 1
    return "".join(lines[:start]) + "".join(lines[end:])


def _repo_from_file_path(file_path: str) -> Optional[str]:
    parts = file_path.split("/")
    if len(parts) >= 3 and parts[0] == "repos":
        return parts[1]
    return None


def _refresh_repo_index(wiki_root: Path, repo: str, rows: list[IndexRow]) -> None:
    repo_rows = [row for row in rows if row.file_path.startswith(f"repos/{repo}/")]
    repo_index_path = wiki_root / "repos" / repo / "index.md"
    if not repo_rows:
        if repo_index_path.exists():
            _write_text(repo_index_path, f"# {repo} Index\n\n暂无条目。\n")
        return
    lines = [f"# {repo} Index", "", f"{repo} 的仓库级踩坑、术语和纠错记录。", ""]
    for row in sorted(repo_rows, key=lambda item: item.entry_id):
        lines.append(f"- `{row.entry_id}` `{row.kind}` [{row.title}](../../{row.file_path})")
    lines.append("")
    _write_text(repo_index_path, "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="删除 team-pitfalls LLM Wiki 条目")
    parser.add_argument("--wiki-root", help=f"LLM Wiki 根目录，也可用环境变量 {WIKI_ROOT_ENV}")
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--id", help="要删除的条目 ID，例如 P-001 / G-001 / C-001")
    target_group.add_argument("--title", help="要删除的条目标题")
    parser.add_argument("--dry-run", action="store_true", help="仅预览变更，不写入文件")
    args = parser.parse_args()

    wiki_root = _resolve_wiki_root(args.wiki_root)
    index_path = wiki_root / "index.md"
    if not index_path.exists():
        raise SystemExit("index.md does not exist in wiki root")

    index_before = _read_text(index_path)
    rows = _parse_index_rows(index_before)
    found = _find_by_id(rows, args.id) if args.id else _find_by_title(rows, args.title or "")
    if found is None:
        query = args.id if args.id else args.title
        raise SystemExit(f"未找到条目: {query}")

    target_path = wiki_root / found.file_path
    if not target_path.exists():
        raise SystemExit(f"目标文件不存在: {found.file_path}")

    doc_before = _read_text(target_path)
    doc_after = _remove_entry_block(doc_before, found.entry_id)
    rows_after = [row for row in rows if row.entry_id != found.entry_id]
    repo = _repo_from_file_path(found.file_path)

    if args.dry_run:
        if doc_before != doc_after:
            print(_unified_diff(doc_before, doc_after, _rel(wiki_root, target_path), _rel(wiki_root, target_path)))
        print("index.md / llms.txt would be refreshed")
        if repo:
            print(f"repos/{repo}/index.md would be refreshed")
        return 0

    _write_text(target_path, doc_after)
    _write_index(wiki_root, rows_after)
    _write_llms_txt(wiki_root, rows_after)
    if repo:
        _refresh_repo_index(wiki_root, repo, rows_after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
