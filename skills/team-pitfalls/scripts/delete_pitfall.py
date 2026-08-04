import argparse
import dataclasses
import difflib
import re
from pathlib import Path
from typing import Optional


DEFAULT_WIKI_ROOT = Path("~/.team-pitfalls-wiki")

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


def _resolve_wiki_root() -> Path:
    return DEFAULT_WIKI_ROOT.expanduser().resolve()


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


def _global_domain_from_file_path(file_path: str) -> Optional[str]:
    parts = file_path.split("/")
    if len(parts) >= 3 and parts[0] == "domains":
        return parts[1]
    return None


def _domain_from_file_path(file_path: str) -> Optional[str]:
    parts = file_path.split("/")
    if len(parts) >= 5 and parts[0] == "repos" and parts[2] == "domains":
        return parts[3]
    return None


def _domain_names_for_repo(rows: list[IndexRow], repo: str) -> list[str]:
    prefix = f"repos/{repo}/domains/"
    names = set()
    for row in rows:
        if not row.file_path.startswith(prefix):
            continue
        domain = _domain_from_file_path(row.file_path)
        if domain:
            names.add(domain)
    return sorted(names)


def _global_domain_names(rows: list[IndexRow]) -> list[str]:
    names = set()
    for row in rows:
        domain = _global_domain_from_file_path(row.file_path)
        if domain:
            names.add(domain)
        repo_domain = _domain_from_file_path(row.file_path)
        if repo_domain:
            names.add(repo_domain)
    return sorted(names)


def _refresh_domains_index(wiki_root: Path, rows: list[IndexRow]) -> None:
    domain_names = _global_domain_names(rows)
    lines = ["# Global Domains", "", "跨仓库业务领域入口。", ""]
    for domain in domain_names:
        lines.append(f"- [{domain}]({domain}/index.md)")
    lines.append("")
    _write_text(wiki_root / "domains" / "index.md", "\n".join(lines))


def _refresh_global_domain_index(wiki_root: Path, domain: str, rows: list[IndexRow]) -> None:
    domain_prefix = f"domains/{domain}/"
    domain_rows = [row for row in rows if row.file_path.startswith(domain_prefix)]
    related_repos = sorted(
        {
            row.file_path.split("/")[1]
            for row in rows
            if row.file_path.startswith("repos/") and f"/domains/{domain}/" in row.file_path
        }
    )
    domain_index_path = wiki_root / "domains" / domain / "index.md"
    default_intro = f"{domain} 跨仓库业务领域知识。"
    intro = _existing_intro(domain_index_path, default_intro)
    if not domain_rows and not related_repos:
        if domain_index_path.exists():
            _write_text(domain_index_path, f"# {domain} Global Domain\n\n{intro}\n\n暂无条目。\n")
        return
    lines = [f"# {domain} Global Domain", "", intro, ""]
    if related_repos:
        lines.extend(["## Related Repositories", ""])
        lines.extend(f"- [{repo}](../../repos/{repo}/domains/{domain}/index.md)" for repo in related_repos)
        lines.append("")
    lines.extend(["## Global Domain Records", ""])
    for row in sorted(domain_rows, key=lambda item: item.entry_id):
        lines.append(f"- `{row.entry_id}` `{row.kind}` [{row.title}]({Path(row.file_path).name})")
    lines.append("")
    _write_text(domain_index_path, "\n".join(lines))


def _refresh_domain_index(wiki_root: Path, repo: str, domain: str, rows: list[IndexRow]) -> None:
    domain_prefix = f"repos/{repo}/domains/{domain}/"
    domain_rows = [row for row in rows if row.file_path.startswith(domain_prefix)]
    domain_index_path = wiki_root / "repos" / repo / "domains" / domain / "index.md"
    default_intro = f"{repo} 仓库 {domain} 领域的踩坑、术语和纠错记录。"
    intro = _existing_intro(domain_index_path, default_intro)
    if not domain_rows:
        if domain_index_path.exists():
            _write_text(domain_index_path, f"# {repo} / {domain} Index\n\n{intro}\n\n暂无条目。\n")
        return
    lines = [f"# {repo} / {domain} Index", "", intro, ""]
    for row in sorted(domain_rows, key=lambda item: item.entry_id):
        lines.append(f"- `{row.entry_id}` `{row.kind}` [{row.title}](../../../../{row.file_path})")
    lines.append("")
    _write_text(domain_index_path, "\n".join(lines))


def _refresh_repo_index(wiki_root: Path, repo: str, rows: list[IndexRow]) -> None:
    repo_rows = [
        row
        for row in rows
        if row.file_path.startswith(f"repos/{repo}/") and f"repos/{repo}/domains/" not in row.file_path
    ]
    repo_index_path = wiki_root / "repos" / repo / "index.md"
    domain_names = _domain_names_for_repo(rows, repo)
    if not repo_rows and not domain_names:
        if repo_index_path.exists():
            _write_text(repo_index_path, f"# {repo} Index\n\n暂无条目。\n")
        return
    lines = [f"# {repo} Index", "", f"{repo} 的仓库级踩坑、术语和纠错记录。", ""]
    if domain_names:
        lines.extend(["## Domains", ""])
        lines.extend(f"- [{domain}](domains/{domain}/index.md)" for domain in domain_names)
        lines.append("")
    lines.extend(["## Repo Records", ""])
    for row in sorted(repo_rows, key=lambda item: item.entry_id):
        lines.append(f"- `{row.entry_id}` `{row.kind}` [{row.title}](../../{row.file_path})")
    lines.append("")
    _write_text(repo_index_path, "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="默认写入链路：删除 team-pitfalls LLM Wiki 条目，并刷新相关索引")
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--id", help="要删除的条目 ID，例如 P-001 / G-001 / C-001")
    target_group.add_argument("--title", help="要删除的条目标题")
    parser.add_argument("--dry-run", action="store_true", help="仅预览变更，不写入文件")
    args = parser.parse_args()

    wiki_root = _resolve_wiki_root()
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
    domain = _domain_from_file_path(found.file_path)
    global_domain = _global_domain_from_file_path(found.file_path)

    if args.dry_run:
        if doc_before != doc_after:
            print(_unified_diff(doc_before, doc_after, _rel(wiki_root, target_path), _rel(wiki_root, target_path)))
        print("index.md / llms.txt would be refreshed")
        if repo:
            print(f"repos/{repo}/index.md would be refreshed")
        if repo and domain:
            print(f"repos/{repo}/domains/{domain}/index.md would be refreshed")
        if global_domain:
            print("domains/index.md would be refreshed")
            print(f"domains/{global_domain}/index.md would be refreshed")
        return 0

    _write_text(target_path, doc_after)
    _write_index(wiki_root, rows_after)
    _write_llms_txt(wiki_root, rows_after)
    if repo:
        _refresh_repo_index(wiki_root, repo, rows_after)
    if repo and domain:
        _refresh_domain_index(wiki_root, repo, domain, rows_after)
        _refresh_global_domain_index(wiki_root, domain, rows_after)
    if global_domain:
        _refresh_global_domain_index(wiki_root, global_domain, rows_after)
        _refresh_domains_index(wiki_root, rows_after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
