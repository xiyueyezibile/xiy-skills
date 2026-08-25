#!/usr/bin/env python3
"""Maintain an independent Git repository used as a personal LLM Wiki."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

CONFIG_PATH = Path.home() / ".xiy" / "config.json"
CODEX_HOOKS_PATH = Path.home() / ".codex" / "hooks.json"
HOOK_SCRIPT = Path(__file__).resolve().parent / "xiy_llm_wiki_hook.py"


@dataclass(frozen=True)
class Snapshot:
    root: Path
    repo_name: str
    branch: str
    head: str
    upstream: str
    ahead: int
    behind: int
    recent_commit: str
    recent_commits: tuple[str, ...]
    changed_files: tuple[str, ...]
    staged_files: tuple[str, ...]
    unstaged_files: tuple[str, ...]
    untracked_files: tuple[str, ...]
    changed_areas: tuple[str, ...]
    diff_stat: str

    @property
    def sync_summary(self) -> str:
        if not self.upstream:
            return "未配置 upstream"
        if self.ahead == 0 and self.behind == 0:
            return f"与 `{self.upstream}` 同步"
        return f"相对 `{self.upstream}` 领先 {self.ahead}、落后 {self.behind} 个提交"

    @property
    def summary(self) -> str:
        if self.changed_files:
            areas = "、".join(f"`{item}`" for item in self.changed_areas)
            focus = f"，主要集中在 {areas}" if areas else ""
            stat = f"；已跟踪改动规模为 {self.diff_stat}" if self.diff_stat else ""
            return (
                f"工作区共有 {len(self.changed_files)} 个改动文件"
                f"（暂存 {len(self.staged_files)}、未暂存 {len(self.unstaged_files)}、"
                f"未跟踪 {len(self.untracked_files)}）{focus}{stat}。{self.sync_summary}。"
            )
        if self.recent_commit:
            return (
                f"工作区干净。{self.sync_summary}。"
                f"最近可确认的工作落点是提交“{self.recent_commit}”。"
            )
        return f"工作区干净。{self.sync_summary}。Git 中没有足够事实确认具体工作目标。"


def git(
    root: Path,
    args: Sequence[str],
    check: bool = True,
    strip: bool = True,
) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git 命令执行失败")
    if strip:
        return result.stdout.strip()
    return result.stdout.rstrip("\r\n")


def git_root(path: Path) -> Path:
    value = git(path, ["rev-parse", "--show-toplevel"], check=False)
    if not value:
        raise RuntimeError(f"{path} 不是 Git 仓库")
    return Path(value).resolve()


def snapshot(root: Path) -> Snapshot:
    head = git(root, ["rev-parse", "--short", "HEAD"], check=False) or "(no commit)"
    status = git(root, ["status", "--porcelain=v1"], check=False, strip=False)
    status_lines = tuple(line for line in status.splitlines() if len(line) >= 4)
    changed = tuple(line[3:] for line in status_lines)
    staged = tuple(
        line[3:] for line in status_lines
        if not line.startswith("??") and line[0] != " "
    )
    unstaged = tuple(
        line[3:] for line in status_lines
        if not line.startswith("??") and line[1] != " "
    )
    untracked = tuple(line[3:] for line in status_lines if line.startswith("??"))
    changed_areas = tuple(dict.fromkeys(
        (path.rsplit(" -> ", 1)[-1].split("/", 1)[0] or ".")
        for path in changed
    ))[:8]
    upstream = git(
        root,
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        check=False,
    )
    ahead = behind = 0
    if upstream:
        counts = git(
            root,
            ["rev-list", "--left-right", "--count", f"HEAD...{upstream}"],
            check=False,
        ).split()
        if len(counts) == 2 and all(item.isdigit() for item in counts):
            ahead, behind = (int(item) for item in counts)
    recent_commits = tuple(filter(None, git(
        root,
        ["log", "-3", "--date=short", "--pretty=format:%h%x09%ad%x09%s"],
        check=False,
    ).splitlines())) if head != "(no commit)" else ()
    return Snapshot(
        root=root,
        repo_name=root.name,
        branch=git(root, ["branch", "--show-current"], check=False)
        or "(detached HEAD)",
        head=head,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        recent_commit=git(root, ["log", "-1", "--pretty=%s"], check=False)
        if head != "(no commit)"
        else "",
        recent_commits=recent_commits,
        changed_files=changed,
        staged_files=staged,
        unstaged_files=unstaged,
        untracked_files=untracked,
        changed_areas=changed_areas,
        diff_stat=git(root, ["diff", "HEAD", "--shortstat"], check=False)
        if head != "(no commit)"
        else "",
    )


def load_config() -> dict[str, object]:
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"未找到配置，请先执行 init：{CONFIG_PATH}")
    try:
        value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"配置格式错误：{CONFIG_PATH}") from error
    if not isinstance(value, dict):
        raise RuntimeError("配置根节点必须是 JSON 对象")
    return value


def save_config(config: dict[str, object]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def wiki_root(config: dict[str, object]) -> Path:
    wiki = config.get("llm_wiki")
    if not isinstance(wiki, dict) or not isinstance(wiki.get("repo"), str):
        raise RuntimeError("配置缺少 llm_wiki.repo")
    return Path(wiki["repo"]).expanduser().resolve()


def remote_name(config: dict[str, object]) -> str:
    wiki = config.get("llm_wiki")
    if isinstance(wiki, dict) and isinstance(wiki.get("remote"), str):
        return wiki["remote"]
    return "origin"


def pull_latest(config: dict[str, object]) -> Path:
    """Synchronize the Wiki before reading or changing it."""
    wiki = git_root(wiki_root(config))
    if git(wiki, ["status", "--short"], check=False):
        raise RuntimeError(
            f"Wiki 仓库存在未提交改动，已停止同步以保护本地内容：{wiki}"
        )
    remote = remote_name(config)
    remote_url = git(wiki, ["remote", "get-url", remote], check=False)
    branch = git(wiki, ["branch", "--show-current"])
    has_head = bool(git(wiki, ["rev-parse", "--verify", "HEAD"], check=False))
    if not remote_url or not branch or not has_head:
        return wiki
    git(wiki, ["pull", "--ff-only", remote, branch])
    return wiki


def current_source() -> Snapshot:
    return snapshot(git_root(Path.cwd()))


def current_work_markdown(source: Snapshot) -> str:
    def file_list(items: tuple[str, ...]) -> str:
        return "\n".join(f"- `{item}`" for item in items) or "- 无"

    commits = []
    for item in source.recent_commits:
        parts = item.split("\t", 2)
        if len(parts) == 3:
            commits.append(f"- `{parts[0]}`（{parts[1]}）{parts[2]}")
        else:
            commits.append(f"- {item}")
    areas = "、".join(f"`{item}`" for item in source.changed_areas) or "无"
    commits_text = "\n".join(commits) or "- 无"
    return (
        "# 当前工作\n\n"
        f"- 识别时间：{datetime.now().astimezone().isoformat(timespec='seconds')}\n"
        f"- 业务仓库：`{source.repo_name}`\n"
        f"- 仓库路径：`{source.root}`\n"
        f"- 分支：`{source.branch}`\n"
        f"- HEAD：`{source.head}`\n"
        f"- Upstream：`{source.upstream or '未配置'}`\n"
        f"- 同步关系：{source.sync_summary}\n\n"
        "## 工作摘要\n\n"
        f"{source.summary}\n\n"
        "## 改动概览\n\n"
        f"- 改动文件：{len(source.changed_files)} 个\n"
        f"- 暂存 / 未暂存 / 未跟踪：{len(source.staged_files)} / "
        f"{len(source.unstaged_files)} / {len(source.untracked_files)}\n"
        "- 分类说明：同一文件可能同时包含已暂存和未暂存改动\n"
        f"- 改动范围：{areas}\n"
        f"- 已跟踪改动规模：{source.diff_stat or '无'}\n\n"
        "## 改动文件\n\n"
        "### 已暂存\n\n"
        f"{file_list(source.staged_files)}\n\n"
        "### 未暂存\n\n"
        f"{file_list(source.unstaged_files)}\n\n"
        "### 未跟踪\n\n"
        f"{file_list(source.untracked_files)}\n\n"
        "## 最近提交\n\n"
        f"{commits_text}\n"
    )


def init_wiki(path: Path, remote: str | None) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        if remote:
            subprocess.run(["git", "clone", remote, str(path)], check=True)
        else:
            path.mkdir(parents=True)
            subprocess.run(["git", "-C", str(path), "init"], check=True)
    root = git_root(path)
    if git(root, ["status", "--short"], check=False):
        raise RuntimeError(
            f"Wiki 仓库存在未提交改动，已停止初始化同步：{root}"
        )
    branch = git(root, ["branch", "--show-current"])
    has_head = bool(git(root, ["rev-parse", "--verify", "HEAD"], check=False))
    if branch and has_head and git(root, ["remote", "get-url", "origin"], check=False):
        git(root, ["pull", "--ff-only", "origin", branch])
    for directory in ("raw", "wiki", "wiki/context", "wiki/decision",
                      "wiki/rule", "wiki/pitfall", "wiki/source"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    write_if_missing(
        root / "WIKI_SCHEMA.md",
        "# LLM Wiki 维护协议\n\n"
        "本仓库就是完整的个人 LLM Wiki。`raw/` 保存原始资料，`wiki/` 保存 LLM 编译后的结构化知识，"
        "`wiki/index.md` 是目录，`wiki/current-work.md` 标识当前工作，`log.md` 记录操作。\n\n"
        "知识应包含结论、依据、适用条件、反例或不确定性，并使用相对链接交叉引用。\n",
    )
    write_if_missing(
        root / "wiki/index.md",
        "# Wiki Index\n\n- [当前工作](current-work.md)\n",
    )
    write_if_missing(root / "log.md", "# Wiki Log\n")


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def init_command(args: argparse.Namespace) -> None:
    source = current_source()
    wiki_path = Path(args.wiki_repo).expanduser().resolve()
    init_wiki(wiki_path, args.wiki_remote)
    config = {
        "version": 2,
        "llm_wiki": {"repo": str(wiki_path), "remote": args.remote},
        "repositories": {
            str(source.root): {"name": source.repo_name},
        },
    }
    save_config(config)
    print(f"已初始化 Wiki 仓库：{wiki_path}")
    print(f"配置已写入：{CONFIG_PATH}")
    sync(config, source, already_pulled=True)


def link_command() -> None:
    config = load_config()
    source = current_source()
    repositories = config.setdefault("repositories", {})
    if not isinstance(repositories, dict):
        raise RuntimeError("配置中的 repositories 必须是对象")
    repositories[str(source.root)] = {"name": source.repo_name}
    save_config(config)
    print(f"已关联业务仓库：{source.root}")


def configure_watch_command(args: argparse.Namespace) -> None:
    config = load_config()
    root = git_root(Path(args.repo).expanduser()) if args.repo else git_root(Path.cwd())
    repositories = config.setdefault("repositories", {})
    if not isinstance(repositories, dict):
        raise RuntimeError("配置中的 repositories 必须是对象")
    value = repositories.setdefault(str(root), {"name": root.name})
    if not isinstance(value, dict):
        raise RuntimeError(f"仓库配置不是对象：{root}")
    value["session_watch"] = {
        "enabled": not args.disable,
        "action": args.action,
        "events": args.events,
    }
    save_config(config)
    state = "已启用" if not args.disable else "已停用"
    print(f"{state}会话监听：{root}（action={args.action}, events={','.join(args.events)}）")


def install_hooks_command(args: argparse.Namespace) -> None:
    path = Path(args.path).expanduser() if args.path else CODEX_HOOKS_PATH
    if path.exists():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Codex hooks 配置格式错误：{path}") from error
    else:
        config = {"hooks": {}}
    if not isinstance(config, dict):
        raise RuntimeError("Codex hooks 配置根节点必须是对象")
    hooks = config.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise RuntimeError("Codex hooks 配置中的 hooks 必须是对象")
    command = f"python3 {HOOK_SCRIPT}"
    entry = {"type": "command", "command": command, "timeout": 15}
    for event in args.events:
        items = hooks.setdefault(event, [])
        if not isinstance(items, list):
            raise RuntimeError(f"hooks.{event} 必须是数组")
        existing = next(
            (
                item
                for item in items
                if isinstance(item, dict)
                and isinstance(item.get("hooks"), list)
                and any(
                    isinstance(hook, dict)
                    and "xiy_llm_wiki_hook.py" in str(hook.get("command", ""))
                    for hook in item["hooks"]
                )
            ),
            None,
        )
        if existing is not None:
            existing["hooks"] = [entry]
        else:
            items.append({"hooks": [entry]})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已安装 Xiy LLM Wiki hooks：{path}（events={','.join(args.events)}）")
    if path == CODEX_HOOKS_PATH:
        print(
            "Codex 不会热加载新 hook：请重启 Codex 或启动一次普通交互式 codex，"
            "完成 hook 信任登记后再新建会话。"
        )


def sync(
    config: dict[str, object],
    source: Snapshot,
    already_pulled: bool = False,
) -> None:
    root = wiki_root(config)
    if not root.exists():
        raise RuntimeError(f"Wiki 仓库不存在：{root}")
    wiki = git_root(wiki_root(config)) if already_pulled else pull_latest(config)
    (wiki / "wiki/current-work.md").write_text(
        current_work_markdown(source), encoding="utf-8"
    )
    with (wiki / "log.md").open("a", encoding="utf-8") as handle:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        handle.write(f"\n- {now}｜sync｜{source.repo_name}\n")
    status = git(wiki, ["status", "--short"])
    if not status:
        print("Wiki 无变化，不创建空提交。")
        return
    branch = git(wiki, ["branch", "--show-current"]) or "HEAD"
    message = f"wiki: update {source.repo_name} context"
    git(wiki, ["add", "-A"])
    git(wiki, ["commit", "-m", message])
    remote = remote_name(config)
    if not git(wiki, ["remote", "get-url", remote], check=False):
        print(f"已提交：{message}（未配置远端，跳过 push）")
        return
    if branch == "HEAD":
        raise RuntimeError("Wiki 仓库处于 detached HEAD，已提交但无法安全 push")
    git(wiki, ["push", remote, f"HEAD:{branch}"])
    print(f"已提交并 push：{message}")


def record_command(args: argparse.Namespace) -> None:
    config = load_config()
    source = current_source()
    wiki = pull_latest(config)
    now = datetime.now().astimezone()
    category = args.category
    entry = wiki / "wiki" / category / f"{now:%Y-%m-%d}.md"
    entry.parent.mkdir(parents=True, exist_ok=True)
    with entry.open("a", encoding="utf-8") as handle:
        handle.write(
            f"\n## {now:%H:%M}｜{category}\n\n"
            f"- 当前工作：{source.summary}\n"
            f"- 业务仓库：`{source.repo_name}`\n"
            f"- 记录：{args.note.strip()}\n"
        )
    (wiki / "wiki/current-work.md").write_text(
        current_work_markdown(source), encoding="utf-8"
    )
    with (wiki / "log.md").open("a", encoding="utf-8") as handle:
        handle.write(
            f"\n- {now.isoformat(timespec='seconds')}｜record｜"
            f"{source.repo_name}｜{category}\n"
        )
    update_index(wiki)
    sync(config, source, already_pulled=True)


def update_index(wiki: Path) -> None:
    links = ["- [当前工作](current-work.md)"]
    for path in sorted((wiki / "wiki").glob("*/*.md")):
        if path.name == "current-work.md":
            continue
        links.append(f"- [{path.parent.name}/{path.name}]({path.relative_to(wiki / 'wiki')})")
    (wiki / "wiki/index.md").write_text(
        "# Wiki Index\n\n" + "\n".join(links) + "\n", encoding="utf-8"
    )


def status_command() -> None:
    config = load_config()
    source = current_source()
    wiki = pull_latest(config)
    print(json.dumps({
        "config": str(CONFIG_PATH),
        "source_repo": str(source.root),
        "wiki_repo": str(wiki),
        "branch": source.branch,
        "head": source.head,
        "upstream": source.upstream or None,
        "ahead": source.ahead,
        "behind": source.behind,
        "current_work": source.summary,
        "changed_files": list(source.changed_files),
        "staged_files": list(source.staged_files),
        "unstaged_files": list(source.unstaged_files),
        "untracked_files": list(source.untracked_files),
        "changed_areas": list(source.changed_areas),
        "diff_stat": source.diff_stat,
        "recent_commits": list(source.recent_commits),
        "wiki_clean": not bool(git(wiki, ["status", "--short"], check=False)),
        "write_performed": False,
        "remote_pulled": True,
    }, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="维护独立 Git 仓库形式的个人 LLM Wiki")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--wiki-repo", required=True)
    init.add_argument("--wiki-remote")
    init.add_argument("--remote", default="origin")
    sub.add_parser("link")
    sub.add_parser("status")
    record = sub.add_parser("record")
    record.add_argument("--category", choices=("context", "decision", "rule", "pitfall", "source"),
                        default="context")
    record.add_argument("--note", required=True)
    sub.add_parser("sync")
    watch = sub.add_parser("watch", help="配置当前仓库的会话监听")
    watch.add_argument("--repo")
    watch.add_argument("--action", choices=("extract", "status", "sync"), default="extract")
    watch.add_argument("--events", nargs="+", default=("UserPromptSubmit", "Stop"))
    watch.add_argument("--disable", action="store_true")
    hooks = sub.add_parser("hooks", help="安装 Codex hooks")
    hooks.add_argument("install", choices=("install",))
    hooks.add_argument("--path")
    hooks.add_argument("--events", nargs="+", default=("UserPromptSubmit", "Stop"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            init_command(args)
        elif args.command == "link":
            link_command()
        elif args.command == "status":
            status_command()
        elif args.command == "record":
            if not args.note.strip():
                raise RuntimeError("--note 不能为空")
            record_command(args)
        elif args.command == "sync":
            config = load_config()
            sync(config, current_source())
        elif args.command == "watch":
            configure_watch_command(args)
        elif args.command == "hooks":
            install_hooks_command(args)
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
