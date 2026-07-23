import argparse
import dataclasses
import datetime as _dt
import difflib
import re
from pathlib import Path
from typing import Optional

from cli_support import add_json_source_arguments, load_json_object


DEFAULT_WIKI_ROOT = Path("~/.team-pitfalls-wiki")

TYPE_TO_FILE: dict[str, str] = {
    "mcp": "pitfalls/tools-and-internal-platforms.md",
    "tools": "pitfalls/tools-and-internal-platforms.md",
    "git": "pitfalls/git-and-commit.md",
    "docs": "pitfalls/docs-and-portability.md",
}
DOMAIN_KIND_TO_FILE: dict[str, str] = {
    "glossary": "glossary.md",
    "corrections": "corrections.md",
}

ENTRY_ID_RE = re.compile(r"^(P|G|C)-\d{3}$")
ENTRY_HEADER_RE = re.compile(r"^###\s+((?:P|G|C)-\d{3})\s*:\s*(.+?)\s*$")
INDEX_ROW_RE = re.compile(
    r"^\|\s*((?:P|G|C)-\d{3})\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$"
)


@dataclasses.dataclass(frozen=True)
class PitfallEntry:
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
    kind: str
    title: str
    tags: str
    file_path: str


def _today() -> str:
    return _dt.date.today().isoformat()


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


def _find_string_in_obj(obj: Optional[dict[str, object]], keys: tuple[str, ...]) -> str:
    if obj is None:
        return ""
    for key in keys:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _existing_intro(path: Path, default_intro: str) -> str:
    if not path.exists():
        return default_intro
    lines = _read_text(path).splitlines()
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped in {"暂无条目。", default_intro}:
            return default_intro
        return stripped
    return default_intro


def _unified_diff(before: str, after: str, from_name: str, to_name: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=from_name,
            tofile=to_name,
        )
    )


def _resolve_wiki_root() -> Path:
    return DEFAULT_WIKI_ROOT.expanduser().resolve()


def _sanitize_slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    normalized = normalized.strip("._-")
    if normalized:
        return normalized
    raise SystemExit("slug is empty after normalization")


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


def _scope_values(obj: dict[str, object]) -> tuple[str, str]:
    scope_ok = str(obj.get("scope_ok", "")).strip()
    scope_no = str(obj.get("scope_no", "")).strip()
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


def _entry_from_json(obj: dict[str, object]) -> PitfallEntry:
    scope_ok, scope_no = _scope_values(obj)
    return PitfallEntry(
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


def _entry_from_args(args: argparse.Namespace) -> PitfallEntry:
    return PitfallEntry(
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


def _validate_new_common_entry(entry: PitfallEntry) -> None:
    missing: list[str] = []
    required_values = {
        "tags": entry.tags,
        "conclusion": entry.conclusion,
        "reasons": entry.reasons,
        "wrong": entry.wrong,
        "right": entry.right,
        "scope_ok": entry.scope_ok,
        "scope_no": entry.scope_no,
    }
    for field_name, value in required_values.items():
        if not value:
            missing.append(field_name)
    if len(entry.min_examples) < 2:
        missing.append("min_examples (至少包含原场景抽象和一个跨场景迁移例)")
    if missing:
        rendered = ", ".join(missing)
        raise SystemExit(f"通用坑位信息不足，缺少: {rendered}")


def _validate_new_glossary_entry(entry: GlossaryEntry) -> None:
    missing: list[str] = []
    required_values = {
        "tags": entry.tags,
        "standard_meaning": entry.standard_meaning,
        "common_misunderstandings": entry.common_misunderstandings,
        "correct_understanding": entry.correct_understanding,
        "min_examples": entry.min_examples,
        "scope_ok": entry.scope_ok,
        "scope_no": entry.scope_no,
    }
    for field_name, value in required_values.items():
        if not value:
            missing.append(field_name)
    if missing:
        rendered = ", ".join(missing)
        raise SystemExit(f"仓库术语信息不足，缺少: {rendered}")


def _validate_new_correction_entry(entry: CorrectionEntry) -> None:
    missing: list[str] = []
    required_values = {
        "tags": entry.tags,
        "wrong_understanding": entry.wrong_understanding,
        "user_correction": entry.user_correction,
        "correction_conclusion": entry.correction_conclusion,
        "trigger_clues": entry.trigger_clues,
        "min_examples": entry.min_examples,
        "scope_ok": entry.scope_ok,
        "scope_no": entry.scope_no,
    }
    for field_name, value in required_values.items():
        if not value:
            missing.append(field_name)
    if missing:
        rendered = ", ".join(missing)
        raise SystemExit(f"仓库纠错信息不足，缺少: {rendered}")


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


def _read_index(wiki_root: Path) -> str:
    index_path = wiki_root / "index.md"
    if not index_path.exists():
        return _index_header()
    return _read_text(index_path)


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
    global_domain_names = sorted(
        {
            row.file_path.split("/")[1]
            for row in rows
            if row.file_path.startswith("domains/") and len(row.file_path.split("/")) >= 3
        }
    )
    lines = [
        "# Team Pitfalls",
        "",
        "> Curated team pitfalls and layered business knowledge for coding agents.",
        "",
        "This file is a curated map, not a sitemap. Follow the reading order and open only linked Markdown pages needed for the current task.",
        "",
        "## Entry Points",
        "",
        "- [Index](index.md): canonical list of all records",
        "- [Global Domains](domains/): cross-repo business domains",
        "- [Common Pitfalls](pitfalls/): cross-project reusable pitfalls",
        "- [Repositories](repos/): repo-specific domains, glossary, and corrections",
        "",
        "## Reading Order",
        "",
        "1. Read repo-domain records under `repos/<repo>/domains/<domain>/` first when repo and domain are known.",
        "2. Then read global-domain records under `domains/<domain>/`.",
        "3. Then read repo records under `repos/<repo>/`.",
        "4. Finally read global records under `pitfalls/`.",
        "",
    ]
    if global_domain_names:
        lines.extend(["## Known Global Domains", ""])
        lines.extend(f"- [{domain}](domains/{domain}/index.md)" for domain in global_domain_names)
        lines.append("")
    if repo_names:
        lines.extend(["## Known Repositories", ""])
        lines.extend(f"- [{repo}](repos/{repo}/index.md)" for repo in repo_names)
        lines.append("")
    _write_text(wiki_root / "llms.txt", "\n".join(lines))


def _global_domain_names(rows: list[IndexRow]) -> list[str]:
    names = set()
    for row in rows:
        parts = row.file_path.split("/")
        if row.file_path.startswith("domains/") and len(parts) >= 3:
            names.add(parts[1])
        if row.file_path.startswith("repos/") and len(parts) >= 5 and parts[2] == "domains":
            names.add(parts[3])
    return sorted(names)


def _write_domains_index(wiki_root: Path, rows: list[IndexRow]) -> None:
    domain_names = _global_domain_names(rows)
    lines = ["# Global Domains", "", "跨仓库业务领域入口。", ""]
    for domain in domain_names:
        lines.append(f"- [{domain}]({domain}/index.md)")
    lines.append("")
    _write_text(wiki_root / "domains" / "index.md", "\n".join(lines))


def _write_global_domain_index(wiki_root: Path, domain: str, rows: list[IndexRow], description: str = "") -> None:
    domain_prefix = f"domains/{domain}/"
    domain_rows = [row for row in rows if row.file_path.startswith(domain_prefix)]
    related_repos = sorted(
        {
            row.file_path.split("/")[1]
            for row in rows
            if row.file_path.startswith("repos/") and f"/domains/{domain}/" in row.file_path
        }
    )
    index_path = wiki_root / "domains" / domain / "index.md"
    default_intro = f"{domain} 跨仓库业务领域知识。"
    intro = description or _existing_intro(index_path, default_intro)
    lines = [f"# {domain} Global Domain", "", intro, ""]
    if related_repos:
        lines.extend(["## Related Repositories", ""])
        lines.extend(f"- [{repo}](../../repos/{repo}/domains/{domain}/index.md)" for repo in related_repos)
        lines.append("")
    lines.extend(["## Global Domain Records", ""])
    for row in sorted(domain_rows, key=lambda item: item.entry_id):
        lines.append(f"- `{row.entry_id}` `{row.kind}` [{row.title}]({Path(row.file_path).name})")
    lines.append("")
    _write_text(index_path, "\n".join(lines))


def _domain_names_for_repo(rows: list[IndexRow], repo: str) -> list[str]:
    prefix = f"repos/{repo}/domains/"
    names = set()
    for row in rows:
        if not row.file_path.startswith(prefix):
            continue
        parts = row.file_path.split("/")
        if len(parts) >= 5:
            names.add(parts[3])
    return sorted(names)


def _write_repo_index(wiki_root: Path, repo: str, rows: list[IndexRow]) -> None:
    repo_rows = [
        row
        for row in rows
        if row.file_path.startswith(f"repos/{repo}/") and f"repos/{repo}/domains/" not in row.file_path
    ]
    repo_lines = [f"# {repo} Index", "", f"{repo} 的仓库级踩坑、术语和纠错记录。", ""]
    domain_names = _domain_names_for_repo(rows, repo)
    if domain_names:
        repo_lines.extend(["## Domains", ""])
        repo_lines.extend(f"- [{domain}](domains/{domain}/index.md)" for domain in domain_names)
        repo_lines.append("")
    repo_lines.extend(["## Repo Records", ""])
    for row in sorted(repo_rows, key=lambda item: item.entry_id):
        repo_lines.append(f"- `{row.entry_id}` `{row.kind}` [{row.title}](../../{row.file_path})")
    repo_lines.append("")
    _write_text(wiki_root / "repos" / repo / "index.md", "\n".join(repo_lines))


def _write_domain_index(wiki_root: Path, repo: str, domain: str, rows: list[IndexRow], description: str = "") -> None:
    domain_prefix = f"repos/{repo}/domains/{domain}/"
    domain_rows = [row for row in rows if row.file_path.startswith(domain_prefix)]
    index_path = wiki_root / "repos" / repo / "domains" / domain / "index.md"
    default_intro = f"{repo} 仓库 {domain} 领域的踩坑、术语和纠错记录。"
    intro = description or _existing_intro(index_path, default_intro)
    domain_lines = [f"# {repo} / {domain} Index", "", intro, ""]
    for row in sorted(domain_rows, key=lambda item: item.entry_id):
        domain_lines.append(f"- `{row.entry_id}` `{row.kind}` [{row.title}](../../../../{row.file_path})")
    domain_lines.append("")
    _write_text(index_path, "\n".join(domain_lines))


def _ensure_page(path: Path, title: str, description: str) -> None:
    if path.exists():
        return
    _write_text(path, f"# {title}\n\n{description}\n\n")


def _ensure_wiki_scaffold(wiki_root: Path) -> None:
    _ensure_page(wiki_root / "SCHEMA.md", "Team Pitfalls Schema", "Team Pitfalls LLM Wiki 的结构、层级和维护规则见 skill references/knowledge-authoring.md。")
    _ensure_page(wiki_root / "pitfalls" / "tools-and-internal-platforms.md", "Tools And Internal Platforms", "工具、鉴权、内部平台读取相关通用坑位。")
    _ensure_page(wiki_root / "pitfalls" / "git-and-commit.md", "Git And Commit", "Git、提交信息、分支和发布流程相关通用坑位。")
    _ensure_page(wiki_root / "pitfalls" / "docs-and-portability.md", "Docs And Portability", "文档、路径、脚本和可移植性相关通用坑位。")
    _write_index(wiki_root, _parse_index_rows(_read_index(wiki_root)))
    _write_llms_txt(wiki_root, _parse_index_rows(_read_index(wiki_root)))
    _write_domains_index(wiki_root, _parse_index_rows(_read_index(wiki_root)))


def _find_by_title(rows: list[IndexRow], title: str, kind: Optional[str]) -> Optional[IndexRow]:
    expected = title.strip()
    for row in rows:
        if row.title == expected and (kind is None or row.kind == kind):
            return row
    return None


def _find_by_id(rows: list[IndexRow], entry_id: str) -> Optional[IndexRow]:
    expected = entry_id.strip()
    for row in rows:
        if row.entry_id == expected:
            return row
    return None


def _find_by_title_in_file(rows: list[IndexRow], title: str, kind: str, file_path: str) -> Optional[IndexRow]:
    expected = title.strip()
    for row in rows:
        if row.title == expected and row.kind == kind and row.file_path == file_path:
            return row
    return None


def _find_by_id_in_file(rows: list[IndexRow], entry_id: str, file_path: str) -> Optional[IndexRow]:
    expected = entry_id.strip()
    for row in rows:
        if row.entry_id == expected and row.file_path == file_path:
            return row
    return None


def _next_id(rows: list[IndexRow], prefix: str) -> str:
    max_n = 0
    expected_prefix = f"{prefix}-"
    for row in rows:
        if not row.entry_id.startswith(expected_prefix):
            continue
        number_part = row.entry_id[len(expected_prefix):]
        if number_part.isdigit():
            max_n = max(max_n, int(number_part))
    return f"{prefix}-{max_n + 1:03d}"


def _desired_id(payload_obj: Optional[dict[str, object]], prefix: str) -> Optional[str]:
    if payload_obj is None:
        return None
    raw_entry_id = str(payload_obj.get("id", "")).strip()
    if ENTRY_ID_RE.match(raw_entry_id) and raw_entry_id.startswith(f"{prefix}-"):
        return raw_entry_id
    return None


def _insert_block(doc_text: str, block: str) -> str:
    sep = "" if doc_text.endswith("\n") else "\n"
    return f"{doc_text}{sep}\n{block}\n"


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

    updated: list[str] = []
    for line in [item.rstrip("\n") for item in lines[start:end]]:
        if line.startswith("- **首次出现**:") or line.startswith("- **最近出现**:"):
            continue
        if line.startswith("- **出现次数**:"):
            match = re.search(r"(\d+)", line)
            count = int(match.group(1)) if match else 0
            updated.append(f"- **出现次数**: {count + 1}")
            continue
        updated.append(line)
    return "".join(lines[:start]) + "\n".join(updated) + "\n" + "".join(lines[end:])


def _format_pitfall(entry_id: str, entry: PitfallEntry) -> str:
    return "\n".join(
        [
            f"### {entry_id}: {entry.title}",
            f"- **标签**: {entry.tags or 'TODO'}",
            "- **出现次数**: 1",
            "- **最近使用**: 从未",
            "- **使用次数**: 0",
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


def _format_glossary(entry_id: str, entry: GlossaryEntry) -> str:
    return "\n".join(
        [
            f"### {entry_id}: {entry.title}",
            f"- **标签**: {entry.tags or 'TODO'}",
            "- **出现次数**: 1",
            "- **最近使用**: 从未",
            "- **使用次数**: 0",
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


def _format_correction(entry_id: str, entry: CorrectionEntry) -> str:
    return "\n".join(
        [
            f"### {entry_id}: {entry.title}",
            f"- **标签**: {entry.tags or 'TODO'}",
            "- **出现次数**: 1",
            "- **最近使用**: 从未",
            "- **使用次数**: 0",
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


def _print_diff_if_changed(before: str, after: str, root: Path, path: Path) -> None:
    if before == after:
        return
    print(_unified_diff(before, after, _rel(root, path), _rel(root, path)))


def _upsert_row(rows: list[IndexRow], row: IndexRow) -> list[IndexRow]:
    output: list[IndexRow] = []
    replaced = False
    for existing in rows:
        if existing.entry_id == row.entry_id:
            output.append(row)
            replaced = True
            continue
        output.append(existing)
    if not replaced:
        output.append(row)
    return output


def _handle_common(args: argparse.Namespace, payload_obj: Optional[dict[str, object]], wiki_root: Path) -> int:
    entry = _entry_from_json(payload_obj) if payload_obj is not None else _entry_from_args(args)
    if not entry.title:
        raise SystemExit("missing title")

    index_before = _read_index(wiki_root)
    rows = _parse_index_rows(index_before)
    desired_id = _desired_id(payload_obj, "P")
    existing = _find_by_title(rows, entry.title, "pitfall")
    if existing is None and desired_id:
        existing = _find_by_id(rows, desired_id)

    file_path = args.file or TYPE_TO_FILE.get(args.type or "")
    if not file_path:
        raise SystemExit("missing --type or --file")
    if file_path.startswith("/") or ".." in Path(file_path).parts:
        raise SystemExit("file must be a relative path inside wiki root")
    target_path = wiki_root / file_path
    _ensure_page(target_path, Path(file_path).stem.replace("-", " ").title(), "通用踩坑记录。")

    if existing is not None:
        target_path = wiki_root / existing.file_path
        doc_before = _read_text(target_path)
        doc_after = _update_existing_entry_block(doc_before, existing.entry_id)
        updated_row = IndexRow(existing.entry_id, "pitfall", entry.title, entry.tags or existing.tags, existing.file_path)
        rows_after = _upsert_row(rows, updated_row)
    else:
        _validate_new_common_entry(entry)
        entry_id = desired_id or _next_id(rows, "P")
        doc_before = _read_text(target_path)
        doc_after = _insert_block(doc_before, _format_pitfall(entry_id, entry))
        updated_row = IndexRow(entry_id, "pitfall", entry.title, entry.tags, file_path)
        rows_after = _upsert_row(rows, updated_row)

    if args.dry_run:
        _print_diff_if_changed(doc_before, doc_after, wiki_root, target_path)
        print("index.md / llms.txt would be refreshed")
        return 0

    _write_text(target_path, doc_after)
    _write_index(wiki_root, rows_after)
    _write_llms_txt(wiki_root, rows_after)
    return 0


def _handle_global_domain(args: argparse.Namespace, payload_obj: Optional[dict[str, object]], wiki_root: Path) -> int:
    if payload_obj is None:
        raise SystemExit("global domain mode requires --json or --json-file")
    if not args.domain or not args.kind:
        raise SystemExit("global domain mode requires --domain and --kind")

    domain = _sanitize_slug(args.domain)
    if args.kind == "glossary":
        entry = _glossary_from_json(payload_obj)
        prefix = "G"
        kind = "glossary"
        file_path = f"domains/{domain}/glossary.md"
        formatter = _format_glossary
        page_title = f"{domain} Global Glossary"
    else:
        entry = _correction_from_json(payload_obj)
        prefix = "C"
        kind = "correction"
        file_path = f"domains/{domain}/corrections.md"
        formatter = _format_correction
        page_title = f"{domain} Global Corrections"

    if not entry.title:
        raise SystemExit("missing title")

    rows = _parse_index_rows(_read_index(wiki_root))
    desired_id = _desired_id(payload_obj, prefix)
    domain_description = _find_string_in_obj(payload_obj, ("domain_description", "domain_summary", "domain_intro"))
    domain_index_path = wiki_root / "domains" / domain / "index.md"
    _ensure_page(domain_index_path, f"{domain} Global Domain", domain_description or f"{domain} 跨仓库业务领域知识。")
    target_path = wiki_root / file_path
    _ensure_page(target_path, page_title, f"{domain} 的全局领域 {kind} 记录。")

    existing = _find_by_title_in_file(rows, entry.title, kind, file_path)
    if existing is None and desired_id:
        existing = _find_by_id_in_file(rows, desired_id, file_path)

    if existing is not None:
        target_path = wiki_root / existing.file_path
        doc_before = _read_text(target_path)
        doc_after = _update_existing_entry_block(doc_before, existing.entry_id)
        updated_row = IndexRow(existing.entry_id, kind, entry.title, entry.tags or existing.tags, existing.file_path)
        rows_after = _upsert_row(rows, updated_row)
    else:
        if args.kind == "glossary":
            _validate_new_glossary_entry(entry)
        else:
            _validate_new_correction_entry(entry)
        entry_id = desired_id or _next_id(rows, prefix)
        doc_before = _read_text(target_path)
        doc_after = _insert_block(doc_before, formatter(entry_id, entry))
        updated_row = IndexRow(entry_id, kind, entry.title, entry.tags, file_path)
        rows_after = _upsert_row(rows, updated_row)

    if args.dry_run:
        _print_diff_if_changed(doc_before, doc_after, wiki_root, target_path)
        print("index.md / llms.txt / domains index / global domain index would be refreshed")
        return 0

    _write_text(target_path, doc_after)
    _write_global_domain_index(wiki_root, domain, rows_after, domain_description)
    _write_domains_index(wiki_root, rows_after)
    _write_index(wiki_root, rows_after)
    _write_llms_txt(wiki_root, rows_after)
    return 0


def _handle_repo(args: argparse.Namespace, payload_obj: Optional[dict[str, object]], wiki_root: Path) -> int:
    if payload_obj is None:
        raise SystemExit("repo mode requires --json or --json-file")
    if not args.repo or not args.kind:
        raise SystemExit("repo mode requires --repo and --kind")

    repo = _sanitize_slug(args.repo)
    domain = _sanitize_slug(args.domain) if args.domain else ""
    if args.kind == "glossary":
        entry = _glossary_from_json(payload_obj)
        prefix = "G"
        kind = "glossary"
        file_path = f"repos/{repo}/domains/{domain}/glossary.md" if domain else f"repos/{repo}/glossary.md"
        formatter = _format_glossary
        page_title = f"{repo} {domain} Glossary" if domain else f"{repo} Glossary"
    else:
        entry = _correction_from_json(payload_obj)
        prefix = "C"
        kind = "correction"
        file_path = f"repos/{repo}/domains/{domain}/corrections.md" if domain else f"repos/{repo}/corrections.md"
        formatter = _format_correction
        page_title = f"{repo} {domain} Corrections" if domain else f"{repo} Corrections"

    if not entry.title:
        raise SystemExit("missing title")

    index_before = _read_index(wiki_root)
    rows = _parse_index_rows(index_before)
    desired_id = _desired_id(payload_obj, prefix)
    domain_description = _find_string_in_obj(payload_obj, ("domain_description", "domain_summary", "domain_intro"))
    repo_index_path = wiki_root / "repos" / repo / "index.md"
    _ensure_page(repo_index_path, f"{repo} Index", f"{repo} 的仓库级踩坑、术语和纠错记录。")
    if domain:
        domain_index_path = wiki_root / "repos" / repo / "domains" / domain / "index.md"
        _ensure_page(domain_index_path, f"{repo} / {domain} Index", domain_description or f"{repo} 仓库 {domain} 领域的踩坑、术语和纠错记录。")
    target_path = wiki_root / file_path
    _ensure_page(target_path, page_title, f"{repo} 的 {kind} 记录。")

    existing = _find_by_title_in_file(rows, entry.title, kind, file_path)
    if existing is None and desired_id:
        existing = _find_by_id_in_file(rows, desired_id, file_path)

    if existing is not None:
        target_path = wiki_root / existing.file_path
        doc_before = _read_text(target_path)
        doc_after = _update_existing_entry_block(doc_before, existing.entry_id)
        updated_row = IndexRow(existing.entry_id, kind, entry.title, entry.tags or existing.tags, existing.file_path)
        rows_after = _upsert_row(rows, updated_row)
    else:
        if args.kind == "glossary":
            _validate_new_glossary_entry(entry)
        else:
            _validate_new_correction_entry(entry)
        entry_id = desired_id or _next_id(rows, prefix)
        doc_before = _read_text(target_path)
        doc_after = _insert_block(doc_before, formatter(entry_id, entry))
        updated_row = IndexRow(entry_id, kind, entry.title, entry.tags, file_path)
        rows_after = _upsert_row(rows, updated_row)

    if args.dry_run:
        _print_diff_if_changed(doc_before, doc_after, wiki_root, target_path)
        print("index.md / llms.txt / repo index / domain index would be refreshed")
        return 0

    _write_text(target_path, doc_after)
    _write_repo_index(wiki_root, repo, rows_after)
    if domain:
        _write_domain_index(wiki_root, repo, domain, rows_after, domain_description)
        _write_global_domain_index(wiki_root, domain, rows_after)
        _write_domains_index(wiki_root, rows_after)
    _write_index(wiki_root, rows_after)
    _write_llms_txt(wiki_root, rows_after)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="写入或更新 team-pitfalls LLM Wiki 条目")
    parser.add_argument("--type", choices=sorted(TYPE_TO_FILE.keys()))
    parser.add_argument("--file", help="wiki root 下的相对文件路径，例如 pitfalls/custom.md")
    parser.add_argument("--repo", help="仓库名，用于写入 repos/<repo-name>/")
    parser.add_argument("--domain", help="领域名；配合 --repo 写入仓库领域级，配合 --global-domain 写入全局领域级")
    parser.add_argument("--global-domain", action="store_true", help="写入 domains/<domain>/ 跨仓库领域级")
    parser.add_argument("--kind", choices=("glossary", "corrections"))
    parser.add_argument("--dry-run", action="store_true")
    add_json_source_arguments(parser)
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

    wiki_root = _resolve_wiki_root()
    _ensure_wiki_scaffold(wiki_root)
    payload_obj = load_json_object(args.json, args.json_file)

    if args.global_domain and args.repo:
        raise SystemExit("--global-domain cannot be used with --repo")
    if args.global_domain:
        return _handle_global_domain(args, payload_obj, wiki_root)
    if args.domain and not args.repo:
        raise SystemExit("--domain requires --repo unless --global-domain is set")
    if args.repo:
        return _handle_repo(args, payload_obj, wiki_root)
    return _handle_common(args, payload_obj, wiki_root)


if __name__ == "__main__":
    raise SystemExit(main())
