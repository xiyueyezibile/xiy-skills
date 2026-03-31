import argparse
import difflib
import re
from pathlib import Path
from typing import Iterable, Optional, Tuple


_INDEX_ROW_RE = re.compile(r"^\|\s*(P-\d{3})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")
_PITFALL_HEADER_RE = re.compile(r"^###\s+(P-\d{3})\s*:\s*(.+?)\s*$")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except Exception:
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


def _parse_index_rows(index_text: str) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for line in index_text.splitlines():
        m = _INDEX_ROW_RE.match(line)
        if not m:
            continue
        rows.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return rows


def _find_by_title(index_rows: list[tuple[str, str, str, str]], title: str) -> Optional[Tuple[str, str]]:
    t = title.strip()
    for pid, row_title, _tags, file_name in index_rows:
        if row_title.strip() == t:
            return pid, file_name.strip()
    return None


def _find_by_id(index_rows: list[tuple[str, str, str, str]], pid: str) -> Optional[Tuple[str, str, str]]:
    p = pid.strip()
    for row_pid, row_title, row_tags, file_name in index_rows:
        if row_pid.strip() == p:
            return row_title.strip(), row_tags.strip(), file_name.strip()
    return None


def _remove_pitfall_block(doc_text: str, pid: str) -> str:
    lines = doc_text.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if line.startswith(f"### {pid}:"):
            start = i
            break
    if start is None:
        return doc_text

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("### P-") and _PITFALL_HEADER_RE.match(lines[j].strip()):
            end = j
            break

    while start > 0 and lines[start - 1].strip() == "":
        start -= 1

    return "".join(lines[:start]) + "".join(lines[end:])


def _remove_index_row(index_text: str, pid: str) -> str:
    lines = index_text.splitlines(keepends=True)
    out: list[str] = []
    for line in lines:
        m = _INDEX_ROW_RE.match(line.rstrip("\n"))
        if not m:
            out.append(line)
            continue
        row_pid = m.group(1).strip()
        if row_pid != pid:
            out.append(line)
            continue
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="删除 team-pitfalls 条目")
    parser.add_argument("--id", help="要删除的条目 ID，例如 P-001")
    parser.add_argument("--title", help="要删除的条目标题，用于模糊匹配")
    parser.add_argument("--index", default="references/INDEX.md")
    parser.add_argument("--dry-run", action="store_true", help="仅预览变更，不写入文件")
    args = parser.parse_args()

    if not args.id and not args.title:
        raise SystemExit("必须提供 --id 或 --title")

    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    repo_root = skill_dir.parent.parent
    references_dir = script_dir.parent / "references"

    index_path = references_dir / "INDEX.md"
    if not index_path.exists():
        raise SystemExit("INDEX.md 不存在")

    index_text = _read_text(index_path)
    index_rows = _parse_index_rows(index_text)

    pid_to_delete: Optional[str] = None
    file_name_to_delete: Optional[str] = None

    if args.id:
        result = _find_by_id(index_rows, args.id)
        if not result:
            raise SystemExit(f"未找到 ID 为 {args.id} 的条目")
        _title, _tags, file_name_to_delete = result
        pid_to_delete = args.id.strip()
        print(f"找到条目: {pid_to_delete} - {_title}")
    else:
        result = _find_by_title(index_rows, args.title)
        if not result:
            raise SystemExit(f"未找到标题包含 '{args.title}' 的条目")
        pid_to_delete, file_name_to_delete = result
        print(f"找到条目: {pid_to_delete} - {args.title}")

    if not pid_to_delete or not file_name_to_delete:
        raise SystemExit("无法确定要删除的条目")

    target_file = references_dir / file_name_to_delete
    if not target_file.exists():
        raise SystemExit(f"目标文件不存在: {file_name_to_delete}")

    ref_before = _read_text(target_file)
    ref_after = _remove_pitfall_block(ref_before, pid_to_delete)

    idx_before = index_text
    idx_after = _remove_index_row(idx_before, pid_to_delete)

    if ref_before == ref_after and idx_before == idx_after:
        print("未找到需要删除的内容")
        return 0

    if args.dry_run:
        print("=== 预览变更 ===")
        if ref_before != ref_after:
            print(_unified_diff(ref_before, ref_after, _rel(repo_root, target_file), _rel(repo_root, target_file)))
        if idx_before != idx_after:
            print(_unified_diff(idx_before, idx_after, _rel(repo_root, index_path), _rel(repo_root, index_path)))
        return 0

    if ref_before != ref_after:
        _write_text(target_file, ref_after)
        print(f"已从文件 {file_name_to_delete} 中删除条目 {pid_to_delete}")

    if idx_before != idx_after:
        _write_text(index_path, idx_after)
        print(f"已从 INDEX.md 中删除条目 {pid_to_delete}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
