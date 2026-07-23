import argparse
import json
import re
import sys
from pathlib import Path

from cli_support import artifact_reference, safe_slug
from task_lifecycle import STATE_SCHEMA_VERSION, file_sha256, state_path, utc_now, validate_task_id, write_state
from upsert_pitfall import IndexRow, _ensure_wiki_scaffold, _parse_index_rows, _read_text, _resolve_wiki_root


ENTRY_HEADER_RE = re.compile(r"^###\s+((?:P|G|C)-\d{3})\s*:")
CONCLUSION_PREFIXES = ("- **一句话结论**:", "- **修正结论**:", "- **标准含义**:")


def _conclusion(doc_text: str, entry_id: str) -> str:
    active = False
    for line in doc_text.splitlines():
        header = ENTRY_HEADER_RE.match(line)
        if header:
            active = header.group(1) == entry_id
            continue
        if active:
            for prefix in CONCLUSION_PREFIXES:
                if line.startswith(prefix):
                    return line[len(prefix):].strip()
    return ""


def _entry_summary(row: IndexRow, wiki_root: Path, page_cache: dict[str, str], scope: str) -> dict[str, str]:
    if row.file_path not in page_cache:
        page_cache[row.file_path] = _read_text(wiki_root / row.file_path)
    doc_text = page_cache[row.file_path]
    return {
        "id": row.entry_id,
        "kind": row.kind,
        "title": row.title,
        "tags": row.tags,
        "scope": scope,
        "file": row.file_path,
        "conclusion": _conclusion(doc_text, row.entry_id),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="创建 team-pitfalls 分层前置检查状态并返回仓库领域/全局领域/仓库/全局摘要")
    parser.add_argument("--task-id", required=True, help="本轮稳定任务 ID，不要包含敏感信息")
    parser.add_argument("--query", help="兼容旧调用保留；分层查找不再使用 query 做召回")
    parser.add_argument("--repo", help="当前仓库名，用于读取仓库级记录")
    parser.add_argument("--domain", help="当前领域名；可单独用于读取全局领域级记录，配合 --repo 时优先读取仓库领域级记录")
    parser.add_argument("--skill-root", help="team-pitfalls skill 根目录；默认从当前脚本反查")
    parser.add_argument("--artifact-root", default="artifacts/repos", help="对外产物相对根目录")
    parser.add_argument("--force", action="store_true", help="覆盖同 task-id 的未完成状态")
    parser.add_argument("--verbose", action="store_true", help="输出完整预检状态，默认只输出紧凑摘要")
    args = parser.parse_args()

    task_id = validate_task_id(args.task_id)
    query = (args.query or "").strip()
    if len(query) > 256:
        raise SystemExit("--query 最多 256 字符")
    if sys.version_info < (3, 9):
        raise SystemExit(f"team-pitfalls 需要 Python >= 3.9，当前为 {sys.version.split()[0]}")

    skill_root = Path(args.skill_root).expanduser().resolve() if args.skill_root else Path(__file__).resolve().parent.parent
    skill_path = skill_root / "SKILL.md"
    required_scripts = ("begin_task.py", "end_task.py", "record_pitfall_usage.py", "upsert_pitfall.py")
    required_files = [skill_path] + [skill_root / "scripts" / name for name in required_scripts]
    missing_skill_files = [path for path in required_files if not path.is_file()]
    if missing_skill_files:
        raise SystemExit(f"Skill 文件不完整: {', '.join(str(path) for path in missing_skill_files)}")

    wiki_root = _resolve_wiki_root()
    _ensure_wiki_scaffold(wiki_root)
    llms_path = wiki_root / "llms.txt"
    index_path = wiki_root / "index.md"
    missing_wiki_files = [path for path in (llms_path, index_path) if not path.is_file()]
    if missing_wiki_files:
        raise SystemExit(f"LLM Wiki 缺少基础入口文件: {', '.join(str(path) for path in missing_wiki_files)}")

    path = state_path(task_id)
    if path.exists() and not args.force:
        raise SystemExit(f"task-id 已存在；请复用原任务、换新 ID，或显式传 --force: {path}")

    raw_repo = (args.repo or "").strip()
    repo = safe_slug(raw_repo, "repo") if raw_repo else ""
    raw_domain = (args.domain or "").strip()
    domain = safe_slug(raw_domain, "domain") if raw_domain else ""
    rows = _parse_index_rows(_read_text(index_path))
    page_cache: dict[str, str] = {}
    levels: list[dict[str, object]] = []

    if repo and domain:
        domain_prefix = f"repos/{repo}/domains/{domain}/"
        domain_entries = [
            _entry_summary(row, wiki_root, page_cache, "domain")
            for row in rows
            if row.file_path.startswith(domain_prefix)
        ]
        levels.append({"scope": "domain", "repo": repo, "domain": domain, "entry_count": len(domain_entries), "entries": domain_entries})

    if domain:
        global_domain_prefix = f"domains/{domain}/"
        global_domain_entries = [
            _entry_summary(row, wiki_root, page_cache, "global_domain")
            for row in rows
            if row.file_path.startswith(global_domain_prefix)
        ]
        levels.append({"scope": "global_domain", "domain": domain, "entry_count": len(global_domain_entries), "entries": global_domain_entries})

    if repo:
        repo_prefix = f"repos/{repo}/"
        repo_entries = [
            _entry_summary(row, wiki_root, page_cache, "repo")
            for row in rows
            if row.file_path.startswith(repo_prefix) and f"{repo_prefix}domains/" not in row.file_path
        ]
        levels.append({"scope": "repo", "repo": repo, "entry_count": len(repo_entries), "entries": repo_entries})

    global_entries = [
        _entry_summary(row, wiki_root, page_cache, "global")
        for row in rows
        if row.file_path.startswith("pitfalls/")
    ]
    levels.append({"scope": "global", "entry_count": len(global_entries), "entries": global_entries})

    entry_ids = [
        str(entry["id"])
        for level in levels
        for entry in level["entries"]  # type: ignore[index]
    ]

    state: dict[str, object] = {
        "schema_version": STATE_SCHEMA_VERSION,
        "task_id": task_id,
        "status": "begun",
        "started_at": utc_now(),
        "wiki_root": str(wiki_root),
        "repo": repo,
        "domain": domain,
        "query": query,
        "entry_ids": entry_ids,
        "skill_sha256": file_sha256(skill_path),
        "index_sha256": file_sha256(index_path),
        "artifact_repo_root": artifact_reference("task.json", repo or "repo", args.artifact_root).rsplit("/", 1)[0],
    }
    write_state(path, state)

    output: dict[str, object] = {
        "task_id": task_id,
        "lookup_order": [str(level["scope"]) for level in levels],
        "entry_count": len(entry_ids),
        "levels": levels,
        "next": "read levels in order: repo domain -> global domain -> repo -> global; apply relevant records; finish with end_task.py",
    }
    if args.verbose:
        output["state"] = state
        output["state_file"] = str(path)
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.verbose else None, separators=None if args.verbose else (",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
