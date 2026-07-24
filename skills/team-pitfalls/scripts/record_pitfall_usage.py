import argparse
import datetime as dt
import re
from pathlib import Path

from upsert_pitfall import (
    ENTRY_HEADER_RE,
    _parse_index_rows,
    _read_index,
    _read_text,
    _resolve_wiki_root,
    _unified_diff,
    _write_text,
)


COUNT_RE = re.compile(r"(\d+)")


def _entry_range(lines: list[str], entry_id: str) -> tuple[int, int]:
    start = -1
    for index, line in enumerate(lines):
        if line.startswith(f"### {entry_id}:"):
            start = index
            break
    if start < 0:
        raise SystemExit(f"正文中未找到条目: {entry_id}")

    end = len(lines)
    for index in range(start + 1, len(lines)):
        if ENTRY_HEADER_RE.match(lines[index].strip()):
            end = index
            break
    return start, end


def _increment_usage(doc_text: str, entry_id: str, today: str) -> str:
    lines = doc_text.splitlines()
    start, end = _entry_range(lines, entry_id)
    count_index = -1
    stale_indexes: list[int] = []

    for index in range(start + 1, end):
        line = lines[index]
        if line.startswith("- **使用次数**:"):
            count_index = index
        elif (
            line.startswith("- **出现次数**:")
            or line.startswith("- **最近使用**:")
            or line.startswith("- **首次出现**:")
            or line.startswith("- **最近出现**:")
        ):
            stale_indexes.append(index)

    if count_index >= 0:
        match = COUNT_RE.search(lines[count_index])
        current_count = int(match.group(1)) if match else 0
        lines[count_index] = f"- **使用次数**: {current_count + 1}"
    else:
        lines[start + 1:start + 1] = ["- **使用次数**: 1"]

    for index in reversed(stale_indexes):
        del lines[index]

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="维护/批处理用途：记录 team-pitfalls 条目在前置检查中的实际使用；累计使用次数并清理旧统计字段")
    parser.add_argument("--id", action="append", required=True, dest="entry_ids", help="命中的条目 ID，可重复传入")
    parser.add_argument("--dry-run", action="store_true", help="仅预览变更，不写入文件")
    args = parser.parse_args()

    wiki_root = _resolve_wiki_root()
    rows = _parse_index_rows(_read_index(wiki_root))
    rows_by_id = {row.entry_id: row for row in rows}
    entry_ids = list(dict.fromkeys(args.entry_ids))
    missing_ids = [entry_id for entry_id in entry_ids if entry_id not in rows_by_id]
    if missing_ids:
        raise SystemExit(f"index.md 中未找到条目: {', '.join(missing_ids)}")

    today = dt.date.today().isoformat()
    changes: dict[Path, tuple[str, str]] = {}
    for entry_id in entry_ids:
        target_path = wiki_root / rows_by_id[entry_id].file_path
        before, current = changes.get(target_path, (_read_text(target_path), _read_text(target_path)))
        changes[target_path] = (before, _increment_usage(current, entry_id, today))

    for target_path, (before, after) in changes.items():
        if args.dry_run:
            print(_unified_diff(before, after, str(target_path.relative_to(wiki_root)), str(target_path.relative_to(wiki_root))))
        else:
            _write_text(target_path, after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
