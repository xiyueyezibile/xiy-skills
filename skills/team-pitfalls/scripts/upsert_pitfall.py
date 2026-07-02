import argparse
import dataclasses
import datetime as _dt
import difflib
import json
import re
from pathlib import Path
from typing import Optional


TYPE_TO_FILE: dict[str, str] = {
    "mcp": "mcp-and-internal-content.md",
    "git": "git-and-commit.md",
    "docs": "docs-and-portability.md",
}

ENTRY_ID_RE = re.compile(r"^(P|G|C)-\d{3}$")
ENTRY_HEADER_RE = re.compile(r"^###\s+((?:P|G|C)-\d{3})\s*:\s*(.+?)\s*$")
GLOBAL_INDEX_ROW_RE = re.compile(
    r"^\|\s*((?:P|G|C)-\d{3})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$"
)
REPO_INDEX_ROW_RE = re.compile(
    r"^\|\s*((?:P|G|C)-\d{3})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$"
)


@dataclasses.dataclass(frozen=True)
class CommonPitfall:
    title: str
    tags: str
    conclusion: str
    reasons: list[str]
    wrong: list[str]
    right: list[str]
    min_examples: list[str]
    scope_ok: str
    scope_no: str


@dataclasses.dataclass(frozen=True)
class GlossaryEntry:
    title: str
    tags: str
    standard_meaning: str
    common_misunderstandings: list[str]
    correct_understanding: list[str]
    min_examples: list[str]
    scope_ok: str
    scope_no: str


@dataclasses.dataclass(frozen=True)
class CorrectionEntry:
    title: str
    tags: str
    wrong_understanding: str
    user_correction: str
    correction_conclusion: str
    trigger_clues: list[str]
    min_examples: list[str]
    scope_ok: str
    scope_no: str


@dataclasses.dataclass(frozen=True)
class IndexRow:
    entry_id: str
    title: str
    tags: str
    file_name: str
    kind: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class RepoPaths:
    repo_name: str
    repo_dir: Path
    index_path: Path
    glossary_path: Path
    corrections_path: Path


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


def _coerce_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    rendered = str(value).strip()
    return [rendered] if rendered else []


def _coerce_tags(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _scope_values(obj: dict[str, object], scope_ok_key: str = "scope_ok", scope_no_key: str = "scope_no") -> tuple[str, str]:
    scope_ok = str(obj.get(scope_ok_key, "")).strip()
    scope_no = str(obj.get(scope_no_key, "")).strip()
    raw_scope = obj.get("scope")
    if isinstance(raw_scope, dict):
        if not scope_ok:
            scope_ok = str(raw_scope.get("apply", "")).strip()
        if not scope_no:
            scope_no = str(raw_scope.get("not_apply", "")).strip()
    return scope_ok, scope_no


def _find_string(obj: dict[str, object], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = obj.get(key)
        if value is None:
            continue
        rendered = str(value).strip()
        if rendered:
            return rendered
    return ""


def _find_list(obj: dict[str, object], keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        values = _coerce_str_list(obj.get(key))
        if values:
            return values
    return []


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
                    tags=match.group(4).strip(),
                    file_name=match.group(5).strip(),
                )
            )
            continue
        rows.append(
            IndexRow(
                entry_id=match.group(1).strip(),
                title=match.group(2).strip(),
                tags=match.group(3).strip(),
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


def _next_id(existing_ids: list[str], prefix: str) -> str:
    max_n = 0
    expected_prefix = f"{prefix}-"
    for entry_id in existing_ids:
        if not entry_id.startswith(expected_prefix):
            continue
        number_part = entry_id[len(expected_prefix):]
        if not number_part.isdigit():
            continue
        max_n = max(max_n, int(number_part))
    return f"{prefix}-{max_n + 1:03d}"


def _insert_after_first_h2(doc_text: str, block: str) -> str:
    lines = doc_text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if not line.startswith("## "):
            continue
        insert_at = index + 1
        while insert_at < len(lines) and lines[insert_at].strip() == "":
            insert_at += 1
        before = "".join(lines[:insert_at])
        after = "".join(lines[insert_at:])
        sep = "" if before.endswith("\n") else "\n"
        return before + f"{sep}\n{block}\n\n" + after.lstrip("\n")
    sep = "" if doc_text.endswith("\n") else "\n"
    return doc_text + f"{sep}\n{block}\n"


def _update_existing_entry_block(doc_text: str, entry_id: str) -> str:
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

    block_lines = [line.rstrip("\n") for line in lines[start:end]]
    today = _today()
    updated: list[str] = []
    for line in block_lines:
        if line.startswith("- **最近出现**:"):
            updated.append(f"- **最近出现**: {today}")
            continue
        if line.startswith("- **出现次数**:"):
            match = re.search(r"(\d+)", line)
            count = int(match.group(1)) if match else 0
            updated.append(f"- **出现次数**: {count + 1}")
            continue
        updated.append(line)
    return "".join(lines[:start]) + "\n".join(updated) + "\n" + "".join(lines[end:])


def _ensure_global_index_header(index_text: str) -> str:
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


def _ensure_repo_index_header(index_text: str) -> str:
    if "| ID | 类型 | 标题 | 标签 | 文件 |" in index_text:
        return index_text
    header = "\n".join(
        [
            "## Repo Pitfalls Index",
            "",
            "| ID | 类型 | 标题 | 标签 | 文件 |",
            "|---|---|---|---|---|",
            "",
        ]
    )
    if index_text.strip():
        return header + index_text.lstrip("\n")
    return header


def _append_global_index_row(index_text: str, row: IndexRow) -> str:
    normalized = _ensure_global_index_header(index_text)
    suffix = "" if normalized.endswith("\n") else "\n"
    return normalized + suffix + f"| {row.entry_id} | {row.title} | {row.tags or 'TODO'} | {row.file_name} |\n"


def _append_repo_index_row(index_text: str, row: IndexRow) -> str:
    normalized = _ensure_repo_index_header(index_text)
    suffix = "" if normalized.endswith("\n") else "\n"
    kind = row.kind or ""
    return normalized + suffix + f"| {row.entry_id} | {kind} | {row.title} | {row.tags or 'TODO'} | {row.file_name} |\n"


def _update_index_row(index_text: str, row: IndexRow, repo_index: bool) -> str:
    row_re = REPO_INDEX_ROW_RE if repo_index else GLOBAL_INDEX_ROW_RE
    output: list[str] = []
    replaced = False
    for line in index_text.splitlines(keepends=True):
        match = row_re.match(line.rstrip("\n"))
        if not match:
            output.append(line)
            continue
        if match.group(1).strip() != row.entry_id:
            output.append(line)
            continue
        replaced = True
        if repo_index:
            output.append(f"| {row.entry_id} | {row.kind or ''} | {row.title} | {row.tags or 'TODO'} | {row.file_name} |\n")
        else:
            output.append(f"| {row.entry_id} | {row.title} | {row.tags or 'TODO'} | {row.file_name} |\n")
    return "".join(output) if replaced else index_text


def _sanitize_repo_name(repo_name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", repo_name.strip())
    normalized = normalized.strip("._-")
    if normalized:
        return normalized
    raise SystemExit("repo name is empty after normalization")


def _repo_paths(references_dir: Path, repo_name: str) -> RepoPaths:
    normalized_name = _sanitize_repo_name(repo_name)
    repo_dir = references_dir / "repos" / normalized_name
    return RepoPaths(
        repo_name=normalized_name,
        repo_dir=repo_dir,
        index_path=repo_dir / "INDEX.md",
        glossary_path=repo_dir / "glossary.md",
        corrections_path=repo_dir / "corrections.md",
    )


def _repo_header_for(kind: str) -> str:
    if kind == "glossary":
        return "## 业务黑话 / 术语映射\n"
    if kind == "corrections":
        return "## AI 纠错记录\n"
    raise SystemExit(f"unsupported repo kind: {kind}")


def _repo_file_name_for(kind: str) -> str:
    if kind == "glossary":
        return "glossary.md"
    if kind == "corrections":
        return "corrections.md"
    raise SystemExit(f"unsupported repo kind: {kind}")


def _repo_path_for(paths: RepoPaths, kind: str) -> Path:
    if kind == "glossary":
        return paths.glossary_path
    if kind == "corrections":
        return paths.corrections_path
    raise SystemExit(f"unsupported repo kind: {kind}")


def _ensure_repo_scaffold(paths: RepoPaths) -> None:
    if not paths.index_path.exists():
        _write_text(paths.index_path, _ensure_repo_index_header(""))
    if not paths.glossary_path.exists():
        _write_text(paths.glossary_path, _repo_header_for("glossary"))
    if not paths.corrections_path.exists():
        _write_text(paths.corrections_path, _repo_header_for("corrections"))


def _common_from_json(obj: dict[str, object]) -> CommonPitfall:
    scope_ok, scope_no = _scope_values(obj)
    return CommonPitfall(
        title=_find_string(obj, ("title",)),
        tags=_coerce_tags(obj.get("tags")),
        conclusion=_find_string(obj, ("conclusion", "one_liner", "one_liner_cn")),
        reasons=_find_list(obj, ("reasons", "why_wrong")),
        wrong=_find_list(obj, ("wrong", "anti_patterns")),
        right=_find_list(obj, ("right", "best_practices")),
        min_examples=_find_list(obj, ("min_examples", "minimal_example", "minimal_examples")),
        scope_ok=scope_ok,
        scope_no=scope_no,
    )


def _glossary_from_json(obj: dict[str, object]) -> GlossaryEntry:
    scope_ok, scope_no = _scope_values(obj)
    return GlossaryEntry(
        title=_find_string(obj, ("title",)),
        tags=_coerce_tags(obj.get("tags")),
        standard_meaning=_find_string(obj, ("standard_meaning", "conclusion")),
        common_misunderstandings=_find_list(obj, ("common_misunderstandings", "wrong", "anti_patterns")),
        correct_understanding=_find_list(obj, ("correct_understanding", "right", "best_practices")),
        min_examples=_find_list(obj, ("min_examples", "minimal_example", "minimal_examples")),
        scope_ok=scope_ok,
        scope_no=scope_no,
    )


def _correction_from_json(obj: dict[str, object]) -> CorrectionEntry:
    scope_ok, scope_no = _scope_values(obj)
    return CorrectionEntry(
        title=_find_string(obj, ("title",)),
        tags=_coerce_tags(obj.get("tags")),
        wrong_understanding=_find_string(obj, ("wrong_understanding", "error_understanding", "wrong")),
        user_correction=_find_string(obj, ("user_correction", "correct_understanding", "right")),
        correction_conclusion=_find_string(obj, ("correction_conclusion", "conclusion")),
        trigger_clues=_find_list(obj, ("trigger_clues", "reasons", "why_wrong")),
        min_examples=_find_list(obj, ("min_examples", "minimal_example", "minimal_examples")),
        scope_ok=scope_ok,
        scope_no=scope_no,
    )


def _format_common_pitfall(entry_id: str, entry: CommonPitfall) -> str:
    today = _today()
    return "\n".join(
        [
            f"### {entry_id}: {entry.title}",
            f"- **标签**: {entry.tags or 'TODO'}",
            f"- **首次出现**: {today}",
            f"- **最近出现**: {today}",
            "- **出现次数**: 1",
            f"- **一句话结论**: {entry.conclusion or 'TODO'}",
            "- **容易写错的原因**:",
            *[f"  - {item}" for item in (entry.reasons or ["TODO"])],
            "- **错误做法（反例）**:",
            *[f"  - {item}" for item in (entry.wrong or ["TODO"])],
            "- **正确做法（正例）**:",
            *[f"  - {item}" for item in (entry.right or ["TODO"])],
            "- **最小示例**:",
            *[f"  - {item}" for item in (entry.min_examples or ["TODO"])],
            "- **适用范围/不适用范围**:",
            f"  - 适用: {entry.scope_ok or 'TODO'}",
            f"  - 不适用: {entry.scope_no or 'TODO'}",
        ]
    )


def _format_glossary_entry(entry_id: str, entry: GlossaryEntry) -> str:
    today = _today()
    return "\n".join(
        [
            f"### {entry_id}: {entry.title}",
            f"- **标签**: {entry.tags or 'TODO'}",
            f"- **首次出现**: {today}",
            f"- **最近出现**: {today}",
            "- **出现次数**: 1",
            f"- **标准含义**: {entry.standard_meaning or 'TODO'}",
            "- **常见误解**:",
            *[f"  - {item}" for item in (entry.common_misunderstandings or ["TODO"])],
            "- **正确理解**:",
            *[f"  - {item}" for item in (entry.correct_understanding or ["TODO"])],
            "- **最小示例**:",
            *[f"  - {item}" for item in (entry.min_examples or ["TODO"])],
            "- **适用范围/不适用范围**:",
            f"  - 适用: {entry.scope_ok or 'TODO'}",
            f"  - 不适用: {entry.scope_no or 'TODO'}",
        ]
    )


def _format_correction_entry(entry_id: str, entry: CorrectionEntry) -> str:
    today = _today()
    return "\n".join(
        [
            f"### {entry_id}: {entry.title}",
            f"- **标签**: {entry.tags or 'TODO'}",
            f"- **首次出现**: {today}",
            f"- **最近出现**: {today}",
            "- **出现次数**: 1",
            f"- **错误理解**: {entry.wrong_understanding or 'TODO'}",
            f"- **用户修正**: {entry.user_correction or 'TODO'}",
            f"- **修正结论**: {entry.correction_conclusion or 'TODO'}",
            "- **触发线索**:",
            *[f"  - {item}" for item in (entry.trigger_clues or ["TODO"])],
            "- **最小示例**:",
            *[f"  - {item}" for item in (entry.min_examples or ["TODO"])],
            "- **适用范围/不适用范围**:",
            f"  - 适用: {entry.scope_ok or 'TODO'}",
            f"  - 不适用: {entry.scope_no or 'TODO'}",
        ]
    )


def _desired_id(payload_obj: Optional[dict[str, object]], expected_prefix: str) -> Optional[str]:
    if payload_obj is None:
        return None
    raw_entry_id = str(payload_obj.get("id", "")).strip()
    if not ENTRY_ID_RE.match(raw_entry_id):
        return None
    if not raw_entry_id.startswith(f"{expected_prefix}-"):
        return None
    return raw_entry_id


def _json_payload(json_text: Optional[str]) -> Optional[dict[str, object]]:
    if not json_text:
        return None
    parsed = json.loads(json_text)
    if not isinstance(parsed, dict):
        raise SystemExit("--json must be a JSON object")
    return parsed


def _common_from_args(args: argparse.Namespace) -> CommonPitfall:
    return CommonPitfall(
        title=(args.title or "").strip(),
        tags=(args.tags or "").strip(),
        conclusion=(args.conclusion or "").strip(),
        reasons=[value.strip() for value in (args.reason or []) if value.strip()],
        wrong=[value.strip() for value in (args.wrong or []) if value.strip()],
        right=[value.strip() for value in (args.right or []) if value.strip()],
        min_examples=[value.strip() for value in (args.min_example or []) if value.strip()],
        scope_ok=(args.scope_ok or "").strip(),
        scope_no=(args.scope_no or "").strip(),
    )


def _print_diff_if_changed(before: str, after: str, repo_root: Path, path: Path) -> None:
    if before == after:
        return
    print(_unified_diff(before, after, _rel(repo_root, path), _rel(repo_root, path)))


def _handle_common_upsert(args: argparse.Namespace, payload_obj: Optional[dict[str, object]], references_dir: Path, repo_root: Path) -> int:
    index_path = references_dir / "INDEX.md"
    index_before = _read_text(index_path) if index_path.exists() else _ensure_global_index_header("")
    index_rows = _parse_index_rows(index_before, repo_index=False)
    desired_entry_id = _desired_id(payload_obj, "P")
    entry = _common_from_json(payload_obj) if payload_obj is not None else _common_from_args(args)
    if not entry.title:
        raise SystemExit("missing title")

    existing = _find_by_title(index_rows, entry.title)
    if existing is None and desired_entry_id:
        existing = _find_by_id(index_rows, desired_entry_id)

    if existing is not None:
        target_path = references_dir / existing.file_name
        if not target_path.exists():
            raise SystemExit("target file not found")
        ref_before = _read_text(target_path)
        ref_after = _update_existing_entry_block(ref_before, existing.entry_id)
        if ref_before == ref_after:
            raise SystemExit("existing pitfall found but block not updated")
        updated_row = IndexRow(entry_id=existing.entry_id, title=entry.title, tags=entry.tags or existing.tags, file_name=existing.file_name)
        index_after = _update_index_row(index_before, updated_row, repo_index=False)
        if args.dry_run:
            _print_diff_if_changed(ref_before, ref_after, repo_root, target_path)
            _print_diff_if_changed(index_before, index_after, repo_root, index_path)
            return 0
        _write_text(target_path, ref_after)
        if index_after != index_before:
            _write_text(index_path, index_after)
        return 0

    file_name = (args.file or "").strip()
    if not file_name:
        if not args.type:
            raise SystemExit("missing --type or --file")
        file_name = TYPE_TO_FILE[args.type]
    if "/" in file_name or "\\" in file_name:
        raise SystemExit("file must be a filename under references/")
    target_path = references_dir / file_name
    if not target_path.exists():
        raise SystemExit("target file not found")

    next_entry_id = desired_entry_id or _next_id([row.entry_id for row in index_rows], "P")
    block = _format_common_pitfall(next_entry_id, entry)
    ref_before = _read_text(target_path)
    ref_after = _insert_after_first_h2(ref_before, block)
    index_after = _append_global_index_row(index_before, IndexRow(entry_id=next_entry_id, title=entry.title, tags=entry.tags, file_name=file_name))
    if args.dry_run:
        _print_diff_if_changed(ref_before, ref_after, repo_root, target_path)
        _print_diff_if_changed(index_before, index_after, repo_root, index_path)
        return 0
    _write_text(target_path, ref_after)
    _write_text(index_path, index_after)
    return 0


def _handle_repo_upsert(args: argparse.Namespace, payload_obj: Optional[dict[str, object]], references_dir: Path, repo_root: Path) -> int:
    if not args.repo or not args.kind:
        raise SystemExit("repo mode requires --repo and --kind")
    paths = _repo_paths(references_dir, args.repo)
    _ensure_repo_scaffold(paths)
    repo_index_before = _read_text(paths.index_path)
    repo_index_rows = _parse_index_rows(repo_index_before, repo_index=True)
    entry_id_prefix = "G" if args.kind == "glossary" else "C"
    desired_entry_id = _desired_id(payload_obj, entry_id_prefix)

    if payload_obj is None:
        raise SystemExit("repo mode requires --json")
    if args.kind == "glossary":
        entry = _glossary_from_json(payload_obj)
        target_path = paths.glossary_path
        block_builder = _format_glossary_entry
        file_name = "glossary.md"
    else:
        entry = _correction_from_json(payload_obj)
        target_path = paths.corrections_path
        block_builder = _format_correction_entry
        file_name = "corrections.md"

    if not entry.title:
        raise SystemExit("missing title")

    existing = _find_by_title(repo_index_rows, entry.title)
    if existing is None and desired_entry_id:
        existing = _find_by_id(repo_index_rows, desired_entry_id)

    if existing is not None:
        ref_before = _read_text(target_path)
        ref_after = _update_existing_entry_block(ref_before, existing.entry_id)
        if ref_before == ref_after:
            raise SystemExit("existing repo entry found but block not updated")
        updated_row = IndexRow(
            entry_id=existing.entry_id,
            kind=args.kind,
            title=entry.title,
            tags=entry.tags or existing.tags,
            file_name=file_name,
        )
        repo_index_after = _update_index_row(repo_index_before, updated_row, repo_index=True)
        if args.dry_run:
            _print_diff_if_changed(ref_before, ref_after, repo_root, target_path)
            _print_diff_if_changed(repo_index_before, repo_index_after, repo_root, paths.index_path)
            return 0
        _write_text(target_path, ref_after)
        if repo_index_after != repo_index_before:
            _write_text(paths.index_path, repo_index_after)
        return 0

    next_entry_id = desired_entry_id or _next_id([row.entry_id for row in repo_index_rows], entry_id_prefix)
    block = block_builder(next_entry_id, entry)
    ref_before = _read_text(target_path)
    ref_after = _insert_after_first_h2(ref_before, block)
    repo_index_after = _append_repo_index_row(
        repo_index_before,
        IndexRow(
            entry_id=next_entry_id,
            kind=args.kind,
            title=entry.title,
            tags=entry.tags,
            file_name=file_name,
        ),
    )
    if args.dry_run:
        _print_diff_if_changed(ref_before, ref_after, repo_root, target_path)
        _print_diff_if_changed(repo_index_before, repo_index_after, repo_root, paths.index_path)
        return 0
    _write_text(target_path, ref_after)
    _write_text(paths.index_path, repo_index_after)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="写入或更新 team-pitfalls 条目")
    parser.add_argument("--type", choices=sorted(TYPE_TO_FILE.keys()))
    parser.add_argument("--file", help="references 下的文件名（例如 git-and-commit.md）")
    parser.add_argument("--repo", help="仓库名，用于写入 references/repos/<repo-name>/")
    parser.add_argument("--kind", choices=("glossary", "corrections"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", help="JSON 字符串")
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

    payload_obj = _json_payload(args.json)
    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    repo_root = skill_dir.parent.parent
    references_dir = skill_dir / "references"

    if args.repo:
        return _handle_repo_upsert(args, payload_obj, references_dir, repo_root)
    return _handle_common_upsert(args, payload_obj, references_dir, repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
