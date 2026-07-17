import argparse
import dataclasses
import json
import os
import re
from pathlib import Path
from typing import Optional

from upsert_pitfall import (
    CONFIG_ENV,
    DEFAULT_CONFIG_PATH,
    WIKI_ROOT_ENV,
    IndexRow,
    _ensure_wiki_scaffold,
    _next_id,
    _parse_index_rows,
    _read_index,
    _read_text,
    _sanitize_slug,
    _write_index,
    _write_llms_txt,
    _write_text,
)


GLOBAL_INDEX_ROW_RE = re.compile(
    r"^\|\s*((?:P|G|C)-\d{3})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$"
)
REPO_INDEX_ROW_RE = re.compile(
    r"^\|\s*((?:P|G|C)-\d{3})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$"
)
ENTRY_HEADER_RE = re.compile(r"^###\s+((?:P|G|C)-\d{3})\s*:\s*(.+?)\s*$")

COMMON_FILE_MAP: dict[str, str] = {
    "mcp-and-internal-content.md": "pitfalls/tools-and-internal-platforms.md",
    "git-and-commit.md": "pitfalls/git-and-commit.md",
    "docs-and-portability.md": "pitfalls/docs-and-portability.md",
}


@dataclasses.dataclass(frozen=True)
class LegacyCommonRow:
    entry_id: str
    title: str
    tags: str
    file_name: str


@dataclasses.dataclass(frozen=True)
class LegacyRepoRow:
    entry_id: str
    kind: str
    title: str
    tags: str
    file_name: str


@dataclasses.dataclass(frozen=True)
class MigrationItem:
    row: IndexRow
    source_path: Path
    target_path: Path
    block: str


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
            "Team Pitfalls LLM Wiki root 未配置，不能迁移旧版 references。",
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


def _parse_legacy_common_rows(index_text: str) -> list[LegacyCommonRow]:
    rows: list[LegacyCommonRow] = []
    for line in index_text.splitlines():
        match = GLOBAL_INDEX_ROW_RE.match(line)
        if not match:
            continue
        rows.append(
            LegacyCommonRow(
                entry_id=match.group(1).strip(),
                title=match.group(2).strip(),
                tags=match.group(3).strip(),
                file_name=match.group(4).strip(),
            )
        )
    return rows


def _parse_legacy_repo_rows(index_text: str) -> list[LegacyRepoRow]:
    rows: list[LegacyRepoRow] = []
    for line in index_text.splitlines():
        match = REPO_INDEX_ROW_RE.match(line)
        if not match:
            continue
        rows.append(
            LegacyRepoRow(
                entry_id=match.group(1).strip(),
                kind=match.group(2).strip(),
                title=match.group(3).strip(),
                tags=match.group(4).strip(),
                file_name=match.group(5).strip(),
            )
        )
    return rows


def _extract_entry_block(doc_text: str, entry_id: str) -> str:
    lines = doc_text.splitlines(keepends=True)
    start: Optional[int] = None
    for index, line in enumerate(lines):
        if line.startswith(f"### {entry_id}:"):
            start = index
            break
    if start is None:
        raise SystemExit(f"entry block not found: {entry_id}")

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if ENTRY_HEADER_RE.match(lines[index].strip()):
            end = index
            break

    return "".join(lines[start:end]).strip() + "\n"


def _rewrite_entry_header(block: str, entry_id: str, title: str) -> str:
    lines = block.splitlines()
    if not lines:
        return f"### {entry_id}: {title}\n"
    lines[0] = f"### {entry_id}: {title}"
    return "\n".join(lines).strip() + "\n"


def _append_block(doc_text: str, block: str) -> str:
    sep = "" if doc_text.endswith("\n") else "\n"
    return f"{doc_text}{sep}\n{block}"


def _page_title(file_path: str) -> str:
    return Path(file_path).stem.replace("-", " ").title()


def _ensure_page(path: Path, title: str) -> None:
    if path.exists():
        return
    _write_text(path, f"# {title}\n\n")


def _common_target_file(file_name: str) -> str:
    mapped = COMMON_FILE_MAP.get(file_name)
    if mapped:
        return mapped
    return f"pitfalls/{Path(file_name).name}"


def _repo_kind(row: LegacyRepoRow) -> str:
    if row.kind == "glossary" or row.file_name == "glossary.md" or row.entry_id.startswith("G-"):
        return "glossary"
    if row.kind in {"correction", "corrections"} or row.file_name == "corrections.md" or row.entry_id.startswith("C-"):
        return "correction"
    raise SystemExit(f"unsupported repo row kind: {row.kind}")


def _has_existing_row(rows: list[IndexRow], kind: str, title: str, file_path: Optional[str] = None) -> bool:
    normalized_title = title.strip()
    for row in rows:
        if row.kind != kind or row.title != normalized_title:
            continue
        if file_path is not None and row.file_path != file_path:
            continue
        if row.kind == kind and row.title == normalized_title:
            return True
    return False


def _allocate_entry_id(rows: list[IndexRow], prefix: str) -> str:
    entry_id = _next_id(rows, prefix)
    rows.append(IndexRow(entry_id=entry_id, kind="_reserved", title="", tags="", file_path=""))
    return entry_id


def _collect_common_items(source_references: Path, wiki_root: Path, rows: list[IndexRow]) -> list[MigrationItem]:
    index_path = source_references / "INDEX.md"
    if not index_path.exists():
        return []

    items: list[MigrationItem] = []
    working_rows = rows[:]
    for legacy_row in _parse_legacy_common_rows(_read_text(index_path)):
        if _has_existing_row(working_rows, "pitfall", legacy_row.title):
            continue
        source_path = source_references / legacy_row.file_name
        if not source_path.exists():
            raise SystemExit(f"legacy source file not found: {source_path}")
        target_file = _common_target_file(legacy_row.file_name)
        entry_id = _allocate_entry_id(working_rows, "P")
        items.append(
            MigrationItem(
                row=IndexRow(
                    entry_id=entry_id,
                    kind="pitfall",
                    title=legacy_row.title,
                    tags=legacy_row.tags,
                    file_path=target_file,
                ),
                source_path=source_path,
                target_path=wiki_root / target_file,
                block=_rewrite_entry_header(
                    _extract_entry_block(_read_text(source_path), legacy_row.entry_id),
                    entry_id,
                    legacy_row.title,
                ),
            )
        )
        working_rows.append(items[-1].row)
    return items


def _collect_repo_items(source_references: Path, wiki_root: Path, rows: list[IndexRow]) -> list[MigrationItem]:
    repos_dir = source_references / "repos"
    if not repos_dir.exists():
        return []

    items: list[MigrationItem] = []
    working_rows = rows[:]
    for repo_dir in sorted(path for path in repos_dir.iterdir() if path.is_dir()):
        index_path = repo_dir / "INDEX.md"
        if not index_path.exists():
            continue
        repo_name = _sanitize_slug(repo_dir.name)
        for legacy_row in _parse_legacy_repo_rows(_read_text(index_path)):
            kind = _repo_kind(legacy_row)
            target_file = "glossary.md" if kind == "glossary" else "corrections.md"
            source_path = repo_dir / legacy_row.file_name
            if not source_path.exists():
                raise SystemExit(f"legacy source file not found: {source_path}")
            file_path = f"repos/{repo_name}/{target_file}"
            if _has_existing_row(working_rows, kind, legacy_row.title, file_path):
                continue
            entry_id = _allocate_entry_id(working_rows, "G" if kind == "glossary" else "C")
            items.append(
                MigrationItem(
                    row=IndexRow(
                        entry_id=entry_id,
                        kind=kind,
                        title=legacy_row.title,
                        tags=legacy_row.tags,
                        file_path=file_path,
                    ),
                    source_path=source_path,
                    target_path=wiki_root / file_path,
                    block=_rewrite_entry_header(
                        _extract_entry_block(_read_text(source_path), legacy_row.entry_id),
                        entry_id,
                        legacy_row.title,
                    ),
                )
            )
            working_rows.append(items[-1].row)
    return items


def _refresh_repo_indexes(wiki_root: Path, rows: list[IndexRow]) -> None:
    repo_names = sorted(
        {
            row.file_path.split("/")[1]
            for row in rows
            if row.file_path.startswith("repos/") and len(row.file_path.split("/")) >= 3
        }
    )
    for repo_name in repo_names:
        repo_rows = [row for row in rows if row.file_path.startswith(f"repos/{repo_name}/")]
        lines = [f"# {repo_name} Index", "", f"{repo_name} 的仓库级踩坑、术语和纠错记录。", ""]
        for row in sorted(repo_rows, key=lambda item: item.entry_id):
            lines.append(f"- `{row.entry_id}` `{row.kind}` [{row.title}](../../{row.file_path})")
        lines.append("")
        _write_text(wiki_root / "repos" / repo_name / "index.md", "\n".join(lines))


def _migrate_items(wiki_root: Path, rows: list[IndexRow], items: list[MigrationItem]) -> list[IndexRow]:
    current_rows = rows[:]
    for item in items:
        _ensure_page(item.target_path, _page_title(item.row.file_path))
        doc_text = _read_text(item.target_path)
        if f"### {item.row.entry_id}:" not in doc_text:
            _write_text(item.target_path, _append_block(doc_text, item.block))
        current_rows.append(item.row)
    return [row for row in current_rows if row.kind != "_reserved"]


def main() -> int:
    parser = argparse.ArgumentParser(description="把旧版 team-pitfalls references 目录迁移到标准 LLM Wiki root")
    parser.add_argument("--source-references", required=True, help="旧版 references 目录路径")
    parser.add_argument("--wiki-root", help=f"LLM Wiki 根目录，也可用环境变量 {WIKI_ROOT_ENV}")
    parser.add_argument("--dry-run", action="store_true", help="只展示迁移计划，不写入文件")
    args = parser.parse_args()

    source_references = Path(args.source_references).expanduser().resolve()
    if not source_references.exists():
        raise SystemExit(f"source references does not exist: {source_references}")

    wiki_root = _resolve_wiki_root(args.wiki_root)
    _ensure_wiki_scaffold(wiki_root)
    rows = _parse_index_rows(_read_index(wiki_root))

    common_items = _collect_common_items(source_references, wiki_root, rows)
    rows_with_common = [*rows, *(item.row for item in common_items)]
    repo_items = _collect_repo_items(source_references, wiki_root, rows_with_common)
    items = [*common_items, *repo_items]

    if args.dry_run:
        print(f"source: {source_references}")
        print(f"wiki_root: {wiki_root}")
        print(f"to_migrate: {len(items)}")
        for item in items:
            print(f"- {item.row.entry_id} {item.row.kind} {item.row.title} -> {item.row.file_path}")
        return 0

    rows_after = _migrate_items(wiki_root, rows, items)
    _write_index(wiki_root, rows_after)
    _write_llms_txt(wiki_root, rows_after)
    _refresh_repo_indexes(wiki_root, rows_after)
    print(f"migrated: {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
