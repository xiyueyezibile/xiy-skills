import argparse
import dataclasses
import datetime as _dt
import difflib
import json
import re
from pathlib import Path
from typing import Iterable, Optional, Tuple


@dataclasses.dataclass(frozen=True)
class Pitfall:
    title: str
    tags: str
    conclusion: str
    reasons: list[str]
    wrong: list[str]
    right: list[str]
    min_examples: list[str]
    scope_ok: str
    scope_no: str


TYPE_TO_FILE = {
    "mcp": "mcp-and-internal-content.md",
    "git": "git-and-commit.md",
    "docs": "docs-and-portability.md",
}

_PITFALL_ID_RE = re.compile(r"^P-\d{3}$")

def _today() -> str:
    return _dt.date.today().isoformat()


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


_INDEX_ROW_RE = re.compile(r"^\|\s*(P-\d{3})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")
_PITFALL_HEADER_RE = re.compile(r"^###\s+(P-\d{3})\s*:\s*(.+?)\s*$")


def _parse_index_rows(index_text: str) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for line in index_text.splitlines():
        m = _INDEX_ROW_RE.match(line)
        if not m:
            continue
        rows.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return rows


def _next_id(existing_ids: Iterable[str]) -> str:
    max_n = 0
    for pid in existing_ids:
        m = re.match(r"^P-(\d{3})$", pid)
        if not m:
            continue
        max_n = max(max_n, int(m.group(1)))
    return f"P-{max_n + 1:03d}"


def _insert_after_first_h2(doc_text: str, block: str) -> str:
    lines = doc_text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("## "):
            insert_at = i + 1
            while insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            before = "".join(lines[:insert_at])
            after = "".join(lines[insert_at:])
            sep = "" if before.endswith("\n") else "\n"
            payload = f"{sep}\n{block}\n\n"
            return before + payload + after.lstrip("\n")
    sep = "" if doc_text.endswith("\n") else "\n"
    return doc_text + f"{sep}\n{block}\n"


def _format_pitfall(pid: str, pitfall: Pitfall) -> str:
    today = _today()
    reasons = pitfall.reasons or ["TODO"]
    wrong = pitfall.wrong or ["TODO"]
    right = pitfall.right or ["TODO"]
    min_examples = pitfall.min_examples or ["TODO"]
    scope_ok = pitfall.scope_ok or "TODO"
    scope_no = pitfall.scope_no or "TODO"
    return "\n".join(
        [
            f"### {pid}: {pitfall.title}",
            f"- **标签**: {pitfall.tags}",
            f"- **首次出现**: {today}",
            f"- **最近出现**: {today}",
            "- **出现次数**: 1",
            f"- **一句话结论**: {pitfall.conclusion}",
            "- **容易写错的原因**:",
            *[f"  - {x}" for x in reasons],
            "- **错误做法（反例）**:",
            *[f"  - {x}" for x in wrong],
            "- **正确做法（正例）**:",
            *[f"  - {x}" for x in right],
            "- **最小示例**:",
            *[f"  - {x}" for x in min_examples],
            "- **适用范围/不适用范围**:",
            f"  - 适用: {scope_ok}",
            f"  - 不适用: {scope_no}",
        ]
    )


def _update_existing_pitfall_block(doc_text: str, pid: str) -> str:
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
    block_lines = [l.rstrip("\n") for l in lines[start:end]]
    today = _today()
    out: list[str] = []
    for bl in block_lines:
        if bl.startswith("- **最近出现**:"):
            out.append(f"- **最近出现**: {today}")
            continue
        if bl.startswith("- **出现次数**:"):
            m = re.search(r"(\d+)", bl)
            if m:
                out.append(f"- **出现次数**: {int(m.group(1)) + 1}")
            else:
                out.append("- **出现次数**: 1")
            continue
        out.append(bl)
    new_block = "\n".join(out) + "\n"
    return "".join(lines[:start]) + new_block + "".join(lines[end:])


def _ensure_index_header(index_text: str) -> str:
    if "| ID | 标题 | 标签 | 文件 |" in index_text:
        return index_text
    header = "\n".join(
        [
            "## Team Pitfalls Index",
            "",
            "| ID | 标题 | 标签 | 文件 |",
            "|---|---|---|---|",
            "",
        ]
    )
    if index_text.strip():
        return header + index_text.lstrip("\n")
    return header


def _append_index_row(index_text: str, pid: str, title: str, tags: str, file_name: str) -> str:
    index_text = _ensure_index_header(index_text)
    row = f"| {pid} | {title} | {tags} | {file_name} |"
    lines = index_text.splitlines(keepends=True)
    out: list[str] = []
    inserted = False
    for line in lines:
        out.append(line)
    if out and not out[-1].endswith("\n"):
        out[-1] = out[-1] + "\n"
    if len(out) >= 1 and out[-1].strip() != "":
        out.append("\n")
    out.append(row + "\n")
    inserted = True
    if not inserted:
        out.append(row + "\n")
    return "".join(out)


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


def _coerce_str_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []
    return [str(v).strip()] if str(v).strip() else []


def _coerce_tags(v) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        items = [str(x).strip() for x in v if str(x).strip()]
        return ", ".join(items)
    return str(v).strip()


def _pitfall_from_json_obj(obj: dict) -> Pitfall:
    title = str(obj.get("title", "")).strip()
    tags = _coerce_tags(obj.get("tags"))

    conclusion = str(obj.get("conclusion", "")).strip()
    if not conclusion:
        conclusion = str(obj.get("one_liner", "")).strip()
    if not conclusion:
        conclusion = str(obj.get("one_liner_cn", "")).strip()

    reasons = _coerce_str_list(obj.get("reasons"))
    if not reasons:
        reasons = _coerce_str_list(obj.get("why_wrong"))

    wrong = _coerce_str_list(obj.get("wrong"))
    if not wrong:
        wrong = _coerce_str_list(obj.get("anti_patterns"))

    right = _coerce_str_list(obj.get("right"))
    if not right:
        right = _coerce_str_list(obj.get("best_practices"))

    min_examples = _coerce_str_list(obj.get("min_examples"))
    if not min_examples:
        min_examples = _coerce_str_list(obj.get("minimal_example"))
    if not min_examples:
        min_examples = _coerce_str_list(obj.get("minimal_examples"))

    scope_ok = str(obj.get("scope_ok", "")).strip()
    scope_no = str(obj.get("scope_no", "")).strip()
    scope = obj.get("scope")
    if isinstance(scope, dict):
        if not scope_ok:
            scope_ok = str(scope.get("apply", "")).strip()
        if not scope_no:
            scope_no = str(scope.get("not_apply", "")).strip()

    return Pitfall(
        title=title,
        tags=tags,
        conclusion=conclusion,
        reasons=reasons,
        wrong=wrong,
        right=right,
        min_examples=min_examples,
        scope_ok=scope_ok,
        scope_no=scope_no,
    )


def _load_payload(args: argparse.Namespace) -> Pitfall:
    if args.json:
        obj = json.loads(args.json)
        if not isinstance(obj, dict):
            raise SystemExit("--json must be a JSON object")
        return _pitfall_from_json_obj(obj)
    return Pitfall(
        title=(args.title or "").strip(),
        tags=(args.tags or "").strip(),
        conclusion=(args.conclusion or "").strip(),
        reasons=[x.strip() for x in (args.reason or []) if x.strip()],
        wrong=[x.strip() for x in (args.wrong or []) if x.strip()],
        right=[x.strip() for x in (args.right or []) if x.strip()],
        min_examples=[x.strip() for x in (args.min_example or []) if x.strip()],
        scope_ok=(args.scope_ok or "").strip(),
        scope_no=(args.scope_no or "").strip(),
    )


def _desired_id_from_args(args: argparse.Namespace) -> Optional[str]:
    if not args.json:
        return None
    obj = json.loads(args.json)
    if not isinstance(obj, dict):
        return None
    pid = str(obj.get("id", "")).strip()
    if not pid:
        return None
    if not _PITFALL_ID_RE.match(pid):
        return None
    return pid


def _update_index_row(index_text: str, pid: str, title: Optional[str], tags: Optional[str]) -> str:
    if not title and not tags:
        return index_text
    lines = index_text.splitlines(keepends=True)
    out: list[str] = []
    replaced = False
    for line in lines:
        m = _INDEX_ROW_RE.match(line.rstrip("\n"))
        if not m:
            out.append(line)
            continue
        row_pid, row_title, row_tags, row_file = m.group(1), m.group(2), m.group(3), m.group(4)
        if row_pid.strip() != pid:
            out.append(line)
            continue
        new_title = title.strip() if title else row_title.strip()
        new_tags = tags.strip() if tags else row_tags.strip()
        out.append(f"| {pid} | {new_title} | {new_tags} | {row_file.strip()} |\n")
        replaced = True
    if not replaced:
        return index_text
    return "".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=sorted(TYPE_TO_FILE.keys()))
    parser.add_argument("--file", help="references 下的文件名（例如 git-and-commit.md）")
    parser.add_argument("--index", default="references/INDEX.md")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", help="JSON 字符串，包含 title/tags/conclusion/reasons/... 字段")
    parser.add_argument("--title")
    parser.add_argument("--tags", default="")
    parser.add_argument("--conclusion", default="")
    parser.add_argument("--reason", action="append")
    parser.add_argument("--wrong", action="append")
    parser.add_argument("--right", action="append")
    parser.add_argument("--min-example", action="append")
    parser.add_argument("--scope-ok", default="")
    parser.add_argument("--scope-no", default="")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    repo_root = skill_dir.parent.parent
    references_dir = script_dir.parent / "references"

    index_path = references_dir / "INDEX.md"
    if not index_path.exists():
        index_text = _ensure_index_header("")
    else:
        index_text = _read_text(index_path)
    index_rows = _parse_index_rows(index_text)

    desired_id = _desired_id_from_args(args)
    pitfall = _load_payload(args)
    if not pitfall.title:
        raise SystemExit("missing title")
    if not pitfall.conclusion:
        pitfall = dataclasses.replace(pitfall, conclusion="TODO")

    existing = _find_by_title(index_rows, pitfall.title)
    if not existing and desired_id:
        by_id = _find_by_id(index_rows, desired_id)
        if by_id:
            _title, _tags, file_name = by_id
            existing = (desired_id, file_name)
    if existing:
        pid, file_name = existing
        target_file = references_dir / file_name
        if not target_file.exists():
            raise SystemExit("target file not found")
        before = _read_text(target_file)
        after = _update_existing_pitfall_block(before, pid)
        if before == after:
            raise SystemExit("existing pitfall found but block not updated")
        idx_after = _update_index_row(index_text, pid, pitfall.title if pitfall.title else None, pitfall.tags if pitfall.tags else None)
        if args.dry_run:
            print(_unified_diff(before, after, _rel(repo_root, target_file), _rel(repo_root, target_file)))
            if idx_after != index_text:
                print(_unified_diff(index_text, idx_after, _rel(repo_root, index_path), _rel(repo_root, index_path)))
        else:
            _write_text(target_file, after)
            if idx_after != index_text:
                _write_text(index_path, idx_after)
        return 0

    pid = desired_id or _next_id([r[0] for r in index_rows])
    file_name = (args.file or "").strip()
    if not file_name:
        if not args.type:
            raise SystemExit("missing --type or --file")
        file_name = TYPE_TO_FILE[args.type]
    if "/" in file_name or "\\" in file_name:
        raise SystemExit("file must be a filename under references/")
    target_file = references_dir / file_name
    if not target_file.exists():
        raise SystemExit("target file not found")

    block = _format_pitfall(pid, pitfall)
    ref_before = _read_text(target_file)
    ref_after = _insert_after_first_h2(ref_before, block)

    idx_before = index_text
    idx_after = _append_index_row(idx_before, pid, pitfall.title, pitfall.tags or "TODO", file_name)

    if args.dry_run:
        print(_unified_diff(ref_before, ref_after, _rel(repo_root, target_file), _rel(repo_root, target_file)))
        print(_unified_diff(idx_before, idx_after, _rel(repo_root, index_path), _rel(repo_root, index_path)))
        return 0

    _write_text(target_file, ref_after)
    _write_text(index_path, idx_after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
