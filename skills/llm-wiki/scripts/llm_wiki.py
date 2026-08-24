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


@dataclass(frozen=True)
class Snapshot:
    root: Path
    repo_name: str
    branch: str
    head: str
    recent_commit: str
    changed_files: tuple[str, ...]

    @property
    def summary(self) -> str:
        if self.changed_files:
            return f"正在处理 {len(self.changed_files)} 个未提交文件的改动"
        if self.recent_commit:
            return f"当前工作聚焦于最近提交：{self.recent_commit}"
        return "正在处理未命名改动"


def git(root: Path, args: Sequence[str], check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git 命令执行失败")
    return result.stdout.strip()


def git_root(path: Path) -> Path:
    value = git(path, ["rev-parse", "--show-toplevel"], check=False)
    if not value:
        raise RuntimeError(f"{path} 不是 Git 仓库")
    return Path(value).resolve()


def snapshot(root: Path) -> Snapshot:
    head = git(root, ["rev-parse", "--short", "HEAD"], check=False) or "(no commit)"
    status = git(root, ["status", "--short"], check=False)
    changed = tuple(
        line[3:] for line in status.splitlines() if len(line) >= 4
    )
    return Snapshot(
        root=root,
        repo_name=root.name,
        branch=git(root, ["branch", "--show-current"], check=False)
        or "(detached HEAD)",
        head=head,
        recent_commit=git(root, ["log", "-1", "--pretty=%s"], check=False)
        if head != "(no commit)"
        else "",
        changed_files=changed,
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
    files = "\n".join(f"- `{item}`" for item in source.changed_files)
    return (
        "# 当前工作\n\n"
        f"- 识别时间：{datetime.now().astimezone().isoformat(timespec='seconds')}\n"
        f"- 业务仓库：`{source.repo_name}`\n"
        f"- 分支：`{source.branch}`\n"
        f"- HEAD：`{source.head}`\n"
        f"- 工作摘要：{source.summary}\n"
        f"- 最近提交：{source.recent_commit or '无'}\n\n"
        "## 未提交文件\n\n"
        f"{files or '- 无未提交文件'}\n"
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


def link_command() -> None:
    config = load_config()
    source = current_source()
    repositories = config.setdefault("repositories", {})
    if not isinstance(repositories, dict):
        raise RuntimeError("配置中的 repositories 必须是对象")
    repositories[str(source.root)] = {"name": source.repo_name}
    save_config(config)
    print(f"已关联业务仓库：{source.root}")


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
        "current_work": source.summary,
        "changed_files": list(source.changed_files),
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
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
