import argparse
import json
import sys
from pathlib import Path

from cli_support import artifact_reference, safe_slug
from task_lifecycle import STATE_SCHEMA_VERSION, file_sha256, state_path, utc_now, validate_task_id, write_state
from upsert_pitfall import IndexRow, _ensure_wiki_scaffold, _parse_index_rows, _read_text, _resolve_wiki_root


def _page_info(wiki_root: Path, relative_path: str) -> dict[str, object]:
    return {"file": relative_path, "exists": (wiki_root / relative_path).is_file()}


def _repo_domain_from_path(file_path: str, repo: str) -> str:
    parts = file_path.split("/")
    if len(parts) >= 5 and parts[0] == "repos" and parts[1] == repo and parts[2] == "domains":
        return parts[3]
    return ""


def _global_domain_from_path(file_path: str) -> str:
    parts = file_path.split("/")
    if len(parts) >= 3 and parts[0] == "domains":
        return parts[1]
    return ""


def _repo_domain_names(wiki_root: Path, rows: list[IndexRow], repo: str) -> list[str]:
    names = {_repo_domain_from_path(row.file_path, repo) for row in rows}
    domain_root = wiki_root / "repos" / repo / "domains"
    if domain_root.is_dir():
        names.update(path.name for path in domain_root.iterdir() if path.is_dir())
    names.discard("")
    return sorted(names)


def _global_domain_names(wiki_root: Path, rows: list[IndexRow]) -> list[str]:
    names = {_global_domain_from_path(row.file_path) for row in rows}
    domain_root = wiki_root / "domains"
    if domain_root.is_dir():
        names.update(path.name for path in domain_root.iterdir() if path.is_dir())
    names.discard("")
    return sorted(names)


def _selected_domain_names(raw_domains: list[str]) -> list[str]:
    domains: list[str] = []
    for raw_domain in raw_domains:
        value = (raw_domain or "").strip()
        if not value:
            continue
        domain = safe_slug(value, "domain")
        if domain not in domains:
            domains.append(domain)
    return domains


def _repo_domain_navigation(wiki_root: Path, repo: str, domains: list[str]) -> list[dict[str, object]]:
    return [
        {
            "domain": domain,
            "index": _page_info(wiki_root, f"repos/{repo}/domains/{domain}/index.md"),
            "glossary": _page_info(wiki_root, f"repos/{repo}/domains/{domain}/glossary.md"),
            "corrections": _page_info(wiki_root, f"repos/{repo}/domains/{domain}/corrections.md"),
        }
        for domain in domains
    ]


def _global_domain_navigation(wiki_root: Path, domains: list[str]) -> list[dict[str, object]]:
    return [
        {
            "domain": domain,
            "index": _page_info(wiki_root, f"domains/{domain}/index.md"),
            "glossary": _page_info(wiki_root, f"domains/{domain}/glossary.md"),
            "corrections": _page_info(wiki_root, f"domains/{domain}/corrections.md"),
        }
        for domain in domains
    ]


def _common_pitfall_pages(wiki_root: Path) -> list[dict[str, object]]:
    pitfall_root = wiki_root / "pitfalls"
    if not pitfall_root.is_dir():
        return []
    return [
        _page_info(wiki_root, f"pitfalls/{path.name}")
        for path in sorted(pitfall_root.glob("*.md"))
        if path.is_file()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="创建 team-pitfalls 前置状态并返回 Wiki 导航入口")
    parser.add_argument("--task-id", required=True, help="本轮稳定任务 ID，不要包含敏感信息")
    parser.add_argument("--query", help="兼容旧调用保留；仅记录是否提供，不参与召回或过滤")
    parser.add_argument("--repo", help="当前仓库名，用于返回仓库级导航入口")
    parser.add_argument("--domain", action="append", default=[], help="当前领域名；可重复传入多个领域")
    parser.add_argument("--skill-root", help="team-pitfalls skill 根目录；默认从当前脚本反查")
    parser.add_argument("--artifact-root", default="artifacts/repos", help="对外产物相对根目录")
    parser.add_argument("--force", action="store_true", help="覆盖同 task-id 的未完成状态")
    parser.add_argument("--verbose", action="store_true", help="输出完整前置状态，默认只输出紧凑导航")
    args = parser.parse_args()

    task_id = validate_task_id(args.task_id)
    query = (args.query or "").strip()
    if len(query) > 256:
        raise SystemExit("--query 最多 256 字符")
    if sys.version_info < (3, 9):
        raise SystemExit(f"team-pitfalls 需要 Python >= 3.9，当前为 {sys.version.split()[0]}")

    skill_root = Path(args.skill_root).expanduser().resolve() if args.skill_root else Path(__file__).resolve().parent.parent
    skill_path = skill_root / "SKILL.md"
    required_scripts = ("begin_task.py", "end_task.py")
    required_files = [skill_path] + [skill_root / "scripts" / name for name in required_scripts]
    missing_skill_files = [path for path in required_files if not path.is_file()]
    if missing_skill_files:
        raise SystemExit(f"Skill 文件不完整: {', '.join(str(path) for path in missing_skill_files)}")

    wiki_root = _resolve_wiki_root()
    llms_path = wiki_root / "llms.txt"
    index_path = wiki_root / "index.md"
    if not llms_path.exists() or not index_path.exists():
        _ensure_wiki_scaffold(wiki_root)
    missing_wiki_files = [path for path in (llms_path, index_path) if not path.is_file()]
    if missing_wiki_files:
        raise SystemExit(f"LLM Wiki 缺少基础入口文件: {', '.join(str(path) for path in missing_wiki_files)}")

    path = state_path(task_id)
    if path.exists() and not args.force:
        raise SystemExit(f"task-id 已存在；请复用原任务、换新 ID，或显式传 --force: {path}")

    raw_repo = (args.repo or "").strip()
    repo = safe_slug(raw_repo, "repo") if raw_repo else ""
    selected_domains = _selected_domain_names(args.domain)
    rows = _parse_index_rows(_read_text(index_path))

    repo_domains = _repo_domain_names(wiki_root, rows, repo) if repo else []
    global_domains = _global_domain_names(wiki_root, rows)
    selected_global_domains = selected_domains or global_domains
    selected_repo_domains = selected_domains or repo_domains

    state: dict[str, object] = {
        "schema_version": STATE_SCHEMA_VERSION,
        "task_id": task_id,
        "status": "begun",
        "started_at": utc_now(),
        "wiki_root": str(wiki_root),
        "repo": repo,
        "domain": selected_domains[0] if selected_domains else "",
        "domains": selected_domains,
        "query": query,
        "entry_ids": [],
        "skill_sha256": file_sha256(skill_path),
        "index_sha256": file_sha256(index_path),
        "artifact_repo_root": artifact_reference("task.json", repo or "repo", args.artifact_root).rsplit("/", 1)[0],
    }
    write_state(path, state)

    navigation: dict[str, object] = {
        "root": {
            "llms": _page_info(wiki_root, "llms.txt"),
            "index": _page_info(wiki_root, "index.md"),
            "schema": _page_info(wiki_root, "SCHEMA.md"),
        },
        "global_domains_index": _page_info(wiki_root, "domains/index.md"),
        "global_domains": _global_domain_navigation(wiki_root, selected_global_domains),
        "common_pitfalls": _common_pitfall_pages(wiki_root),
    }
    if repo:
        navigation["repo"] = {
            "repo": repo,
            "index": _page_info(wiki_root, f"repos/{repo}/index.md"),
            "glossary": _page_info(wiki_root, f"repos/{repo}/glossary.md"),
            "corrections": _page_info(wiki_root, f"repos/{repo}/corrections.md"),
            "domains": _repo_domain_navigation(wiki_root, repo, selected_repo_domains),
        }

    output: dict[str, object] = {
        "task_id": task_id,
        "mode": "navigation",
        "repo": repo,
        "domains": selected_domains,
        "navigation": navigation,
        "next": "read index pages first; open glossary/corrections/pitfall pages only when their introduction or links are relevant; finish with end_task.py",
    }
    if args.verbose:
        output["state"] = state
        output["state_file"] = str(path)
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.verbose else None, separators=None if args.verbose else (",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
