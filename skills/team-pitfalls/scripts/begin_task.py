import argparse
import json
import re
import sys
from pathlib import Path

from cli_support import artifact_reference, safe_slug
from task_lifecycle import STATE_SCHEMA_VERSION, file_sha256, state_path, utc_now, validate_task_id, write_state
from upsert_pitfall import IndexRow, _parse_index_rows, _read_text, _resolve_wiki_root


TERM_SPLIT_RE = re.compile(r"[,，、\s/|:：;；()（）\[\]{}]+")
ENTRY_HEADER_RE = re.compile(r"^###\s+((?:P|G|C)-\d{3})\s*:")
CONCLUSION_PREFIXES = ("- **一句话结论**:", "- **修正结论**:", "- **标准含义**:")
HAN_RE = re.compile(r"^[\u3400-\u9fff]+$")
ATOM_RE = re.compile(r"[a-z0-9._-]+|[\u3400-\u9fff]+")
STOP_TERMS = {
    "team-pitfalls",
    "skill",
    "top3",
    "任务",
    "问题",
    "相关",
    "候选",
    "摘要",
    "踩坑",
    "记录",
}


def _terms(value: str) -> list[str]:
    output: set[str] = set()
    for raw_item in TERM_SPLIT_RE.split(value.lower()):
        for item in ATOM_RE.findall(raw_item):
            if len(item) < 2:
                continue
            output.add(item)
            if HAN_RE.fullmatch(item):
                for size in (2, 3, 4):
                    output.update(item[index : index + size] for index in range(len(item) - size + 1))
    return sorted(output.difference(STOP_TERMS))


def _matching_terms(query_terms: set[str], value: str) -> list[str]:
    return sorted(query_terms.intersection(_terms(value)))


def _score(
    query_terms: set[str], title: str, tags: str, conclusion: str, block: str, repo_match: bool
) -> tuple[int, dict[str, list[str]]]:
    evidence = {
        "title_tags": _matching_terms(query_terms, f"{title},{tags}"),
        "conclusion": _matching_terms(query_terms, conclusion),
        "body": _matching_terms(query_terms, block),
    }
    evidence = {field: terms for field, terms in evidence.items() if terms}
    score = 3 * sum(min(len(term), 8) for term in evidence.get("title_tags", []))
    score += 2 * sum(min(len(term), 8) for term in evidence.get("conclusion", []))
    score += sum(min(len(term), 8) for term in evidence.get("body", []))
    if score and repo_match:
        score += 4
    return score, evidence


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


def _entry_block(doc_text: str, entry_id: str) -> str:
    lines: list[str] = []
    active = False
    for line in doc_text.splitlines():
        header = ENTRY_HEADER_RE.match(line)
        if header:
            if active:
                break
            active = header.group(1) == entry_id
        if active:
            lines.append(line)
    return "\n".join(lines)


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("必须大于或等于 0")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="低成本创建 team-pitfalls 前置检查状态并返回候选摘要")
    parser.add_argument("--task-id", required=True, help="本轮稳定任务 ID，不要包含敏感信息")
    parser.add_argument("--query", required=True, help="本轮任务的一句话关键词摘要，不要传完整用户正文")
    parser.add_argument("--wiki-root", help="LLM Wiki 根目录；未传时读取环境变量或配置文件")
    parser.add_argument("--repo", help="当前仓库名，用于提升仓库级候选优先级")
    parser.add_argument("--skill-root", help="team-pitfalls skill 根目录；默认从当前脚本反查")
    parser.add_argument("--artifact-root", default="artifacts/repos", help="对外产物相对根目录")
    parser.add_argument("--max-candidates", type=_non_negative_int, default=0, help="默认 0 表示不截断；大于 0 时显式限流")
    parser.add_argument("--min-score", type=_non_negative_int, default=4, help="最低相关分；默认过滤仅正文弱碰撞")
    parser.add_argument("--force", action="store_true", help="覆盖同 task-id 的未完成状态")
    parser.add_argument("--verbose", action="store_true", help="输出完整预检状态，默认只输出紧凑摘要")
    args = parser.parse_args()

    task_id = validate_task_id(args.task_id)
    query = args.query.strip()
    if not query or len(query) > 256:
        raise SystemExit("--query 必须是 1-256 字符的一句话关键词摘要")
    if sys.version_info < (3, 9):
        raise SystemExit(f"team-pitfalls 需要 Python >= 3.9，当前为 {sys.version.split()[0]}")

    skill_root = Path(args.skill_root).expanduser().resolve() if args.skill_root else Path(__file__).resolve().parent.parent
    skill_path = skill_root / "SKILL.md"
    required_scripts = ("begin_task.py", "end_task.py", "record_pitfall_usage.py", "upsert_pitfall.py")
    required_files = [skill_path] + [skill_root / "scripts" / name for name in required_scripts]
    missing_skill_files = [path for path in required_files if not path.is_file()]
    if missing_skill_files:
        raise SystemExit(f"Skill 文件不完整: {', '.join(str(path) for path in missing_skill_files)}")

    wiki_root = _resolve_wiki_root(args.wiki_root)
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
    rows = _parse_index_rows(_read_text(index_path))
    query_terms = set(_terms(query))
    page_cache: dict[str, str] = {}
    ranked: list[tuple[int, IndexRow, str, dict[str, list[str]]]] = []
    for row in rows:
        if row.file_path not in page_cache:
            page_cache[row.file_path] = _read_text(wiki_root / row.file_path)
        doc_text = page_cache[row.file_path]
        conclusion = _conclusion(doc_text, row.entry_id)
        block = _entry_block(doc_text, row.entry_id)
        repo_match = bool(repo and row.file_path.startswith(f"repos/{repo}/"))
        if row.file_path.startswith("repos/") and not repo_match:
            continue
        score, evidence = _score(query_terms, row.title, row.tags, conclusion, block, repo_match)
        if score >= args.min_score:
            ranked.append((score, row, conclusion, evidence))
    ranked.sort(key=lambda item: (-item[0], item[1].entry_id))

    candidates: list[dict[str, object]] = []
    for score, row, conclusion, evidence in ranked:
        if args.max_candidates and len(candidates) >= args.max_candidates:
            break
        candidates.append(
            {
                "id": row.entry_id,
                "title": row.title,
                "conclusion": conclusion,
                "scope": "repo" if row.file_path.startswith("repos/") else "common",
                "score": score,
                "matches": evidence,
            }
        )

    state: dict[str, object] = {
        "schema_version": STATE_SCHEMA_VERSION,
        "task_id": task_id,
        "status": "begun",
        "started_at": utc_now(),
        "wiki_root": str(wiki_root),
        "repo": repo,
        "query": query,
        "candidate_ids": [str(item["id"]) for item in candidates],
        "skill_sha256": file_sha256(skill_path),
        "index_sha256": file_sha256(index_path),
        "artifact_repo_root": artifact_reference("task.json", repo or "repo", args.artifact_root).rsplit("/", 1)[0],
    }
    write_state(path, state)

    output: dict[str, object] = {
        "task_id": task_id,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "next": (
            "retry once with expanded synonyms and failure mechanisms before concluding no match"
            if not candidates
            else "review all candidates; apply relevant records; finish with end_task.py"
        ),
    }
    if args.verbose:
        output["state"] = state
        output["state_file"] = str(path)
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.verbose else None, separators=None if args.verbose else (",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
