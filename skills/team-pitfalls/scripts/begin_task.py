import argparse

from task_lifecycle import STATE_SCHEMA_VERSION, print_state, state_path, utc_now, validate_task_id, write_state
from upsert_pitfall import _resolve_wiki_root


def main() -> int:
    parser = argparse.ArgumentParser(description="创建 team-pitfalls 前置检查状态")
    parser.add_argument("--task-id", required=True, help="本轮稳定任务 ID，不要包含用户正文或敏感信息")
    parser.add_argument("--wiki-root", help="LLM Wiki 根目录；未传时读取环境变量或配置文件")
    parser.add_argument("--repo", help="当前仓库名，用于提示优先读取仓库级知识")
    parser.add_argument("--force", action="store_true", help="覆盖同 task-id 的未完成状态")
    args = parser.parse_args()

    task_id = validate_task_id(args.task_id)
    wiki_root = _resolve_wiki_root(args.wiki_root)
    required_reads = [wiki_root / "llms.txt", wiki_root / "index.md"]
    missing = [path for path in required_reads if not path.is_file()]
    if missing:
        rendered = ", ".join(str(path) for path in missing)
        raise SystemExit(f"LLM Wiki 缺少基础入口文件: {rendered}")

    path = state_path(task_id)
    if path.exists() and not args.force:
        raise SystemExit(f"task-id 已存在；请复用原任务、换新 ID，或显式传 --force: {path}")

    repo = (args.repo or "").strip()
    repo_reads: list[str] = []
    if repo:
        repo_root = wiki_root / "repos" / repo
        repo_reads = [
            str(repo_root / "index.md"),
            str(repo_root / "glossary.md"),
            str(repo_root / "corrections.md"),
        ]

    state: dict[str, object] = {
        "schema_version": STATE_SCHEMA_VERSION,
        "task_id": task_id,
        "status": "begun",
        "started_at": utc_now(),
        "wiki_root": str(wiki_root),
        "repo": repo,
        "required_reads": [str(item) for item in required_reads],
        "repo_reads_if_present": repo_reads,
    }
    write_state(path, state)
    print_state(state, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
