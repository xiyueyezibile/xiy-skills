import argparse
import dataclasses
import difflib
import re
from pathlib import Path
from typing import Optional


GLOBAL_INDEX_ROW_RE = re.compile(
    r"^\|\s*((?:P|G|C)-\d{3})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$"
)
REPO_INDEX_ROW_RE = re.compile(
    r"^\|\s*((?:P|G|C)-\d{3})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$"
)
ENTRY_HEADER_RE = re.compile(r"^###\s+((?:P|G|C)-\d{3})\s*:\s*(.+?)\s*$")


@dataclasses.dataclass(frozen=True)
class IndexRow:
    entry_id: str
    title: str
    file_name: str
    kind: Optional[str] = None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return path.name


def _unified_diff(a: str, b: str, from_name: str, to_name: str) -> str:
    return "".join(
        difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            fromfile=from_name,
            tofile=to_name,
        )
    )


def _sanitize_repo_name(repo_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", repo_name.strip())
    normalized = normalized.strip("._-")
    if normalized:
        return normalized
    raise SystemExit("repo name is empty after normalization")


def _parse_index_rows(index_text: str, repo_index: bool) -> list[IndexRow]:
    rows: list[IndexRow] = []
    row_re = REPO_INDEX_ROW_RE if repo_index else GLOBAL_INDEX_ROW_RE
    for line in index_text.splitlines():
        match = row_re.match(line)
        if not match:
            continue
        if repo_index:
            rows.append(
                IndexRow(
                    entry_id=match.group(1).strip(),
                    kind=match.group(2).strip(),
                    title=match.group(3).strip(),
                    file_name=match.group(5).strip(),
                )
            )
            continue
        rows.append(
            IndexRow(
                entry_id=match.group(1).strip(),
                title=match.group(2).strip(),
                file_name=match.group(4).strip(),
            )
        )
    return rows


def _find_by_title(index_rows: list[IndexRow], title: str) -> Optional[IndexRow]:
    expected = title.strip()
    for row in index_rows:
        if row.title == expected:
            return row
    return None


def _find_by_id(index_rows: list[IndexRow], entry_id: str) -> Optional[IndexRow]:
    expected = entry_id.strip()
    for row in index_rows:
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


def _remove_index_row(index_text: str, entry_id: str, repo_index: bool) -> str:
    row_re = REPO_INDEX_ROW_RE if repo_index else GLOBAL_INDEX_ROW_RE
    kept_lines: list[str] = []
    for line in index_text.splitlines(keepends=True):
        match = row_re.match(line.rstrip("\n"))
        if not match:
            kept_lines.append(line)
            continue
        if match.group(1).strip() != entry_id:
            kept_lines.append(line)
    return "".join(kept_lines)


def _resolve_paths(args: argparse.Namespace, references_dir: Path) -> tuple[Path, Path, bool]:
    if args.repo:
        if not args.kind:
            raise SystemExit("repo mode requires --kind")
        repo_name = _sanitize_repo_name(args.repo)
        repo_dir = references_dir / "repos" / repo_name
        index_path = repo_dir / "INDEX.md"
        return index_path, repo_dir, True
    return references_dir / "INDEX.md", references_dir, False


def main() -> int:
    parser = argparse.ArgumentParser(description="删除 team-pitfalls 条目")
    parser.add_argument("--id", help="要删除的条目 ID，例如 P-001 / G-001 / C-001")
    parser.add_argument("--title", help="要删除的条目标题")
    parser.add_argument("--repo", help="仓库名，用于删除 references/repos/<repo-name>/ 下的条目")
    parser.add_argument("--kind", choices=("glossary", "corrections"))
    parser.add_argument("--dry-run", action="store_true", help="仅预览变更，不写入文件")
    args = parser.parse_args()

    if not args.id and not args.title:
        raise SystemExit("必须提供 --id 或 --title")

    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    repo_root = skill_dir.parent.parent
    references_dir = skill_dir / "references"

    index_path, default_target_base, repo_index = _resolve_paths(args, references_dir)
    if not index_path.exists():
        raise SystemExit("INDEX.md 不存在")

    index_before = _read_text(index_path)
    index_rows = _parse_index_rows(index_before, repo_index=repo_index)

    found = _find_by_id(index_rows, args.id) if args.id else _find_by_title(index_rows, args.title or "")
    if found is None:
        query = args.id if args.id else args.title
        raise SystemExit(f"未找到条目: {query}")

    target_path = default_target_base / found.file_name
    if not target_path.exists():
        raise SystemExit(f"目标文件不存在: {found.file_name}")

    ref_before = _read_text(target_path)
    ref_after = _remove_entry_block(ref_before, found.entry_id)
    index_after = _remove_index_row(index_before, found.entry_id, repo_index=repo_index)

    if ref_before == ref_after and index_before == index_after:
        print("未找到需要删除的内容")
        return 0

    if args.dry_run:
        if ref_before != ref_after:
            print(_unified_diff(ref_before, ref_after, _rel(repo_root, target_path), _rel(repo_root, target_path)))
        if index_before != index_after:
            print(_unified_diff(index_before, index_after, _rel(repo_root, index_path), _rel(repo_root, index_path)))
        return 0

    if ref_before != ref_after:
        _write_text(target_path, ref_after)
        print(f"已从文件 {found.file_name} 中删除条目 {found.entry_id}")
    if index_before != index_after:
        _write_text(index_path, index_after)
        print(f"已从 INDEX.md 中删除条目 {found.entry_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
