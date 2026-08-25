#!/usr/bin/env python3
"""Codex hook adapter for configured Xiy LLM Wiki repository watchers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".xiy" / "config.json"
SKILL_SCRIPT = Path(__file__).with_name("llm_wiki.py")


def emit_codex_context(status: dict[str, object]) -> None:
    source_repo = status.get("source_repo", "")
    wiki_repo = status.get("wiki_repo", "")
    current_work = status.get("current_work", "")
    branch = status.get("branch", "")
    context = (
        "Xiy LLM Wiki 监听已命中当前仓库。请在本轮自动使用 `xiy-llm-wiki` 的只读规则："
        "先读取 Wiki 的 `WIKI_SCHEMA.md`、`wiki/current-work.md`、`wiki/index.md`，"
        "再按问题读取相关页面；不得自动 record、sync、commit 或 push。\n"
        f"- 业务仓库：`{source_repo}`\n"
        f"- 分支：`{branch}`\n"
        f"- 当前工作：{current_work}\n"
        f"- Wiki 仓库：`{wiki_repo}`"
    )
    print(json.dumps({
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        },
    }, ensure_ascii=False))


def emit_codex_extraction_prompt(status: dict[str, object]) -> None:
    source_repo = status.get("source_repo", "")
    wiki_repo = status.get("wiki_repo", "")
    message = (
        "Xiy LLM Wiki 会话收尾：当前仓库已启用自动知识提取。回看本轮会话，"
        "仅提炼可跨任务复用且已有事实依据的结论、决策、规则、踩坑或资料摘要。"
        "忽略普通进度、一次性实现细节、未经确认的推测，以及任何 token、cookie、密码、个人或敏感信息。"
        "先检查 Wiki 是否已有等价结论；有新内容时，调用 `xiy-llm-wiki` 的 `record` 写入简洁、可验证的笔记，"
        "该命令会自动 pull、commit、push。没有新内容时不要写入。\n"
        f"- 业务仓库：`{source_repo}`\n"
        f"- Wiki 仓库：`{wiki_repo}`"
    )
    print(json.dumps({
        "decision": "block",
        "reason": message,
    }, ensure_ascii=False))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(payload, dict) or not isinstance(config, dict):
        return 0
    event = payload.get("hook_event_name")
    cwd = Path(payload.get("cwd") or Path.cwd()).expanduser().resolve()
    try:
        root = Path(subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=True, capture_output=True, text=True, timeout=2,
        ).stdout.strip()).resolve()
    except (OSError, subprocess.SubprocessError):
        return 0
    repositories = config.get("repositories", {})
    setting = repositories.get(str(root)) if isinstance(repositories, dict) else None
    watch = setting.get("session_watch") if isinstance(setting, dict) else None
    if not isinstance(watch, dict) or watch.get("enabled") is not True:
        return 0
    events = watch.get("events", [])
    if event not in events:
        return 0
    action = watch.get("action", "extract")
    if event == "Stop" and action == "extract":
        if payload.get("stop_hook_active") is True:
            return 0
        command = [sys.executable, str(SKILL_SCRIPT), "status"]
        result = subprocess.run(command, cwd=root, check=False, capture_output=True, text=True, timeout=12)
        if result.returncode != 0:
            return 0
        try:
            status = json.loads(result.stdout)
        except json.JSONDecodeError:
            return 0
        if isinstance(status, dict):
            emit_codex_extraction_prompt(status)
        return 0
    command = [sys.executable, str(SKILL_SCRIPT), "status" if action == "extract" else action]
    result = subprocess.run(command, cwd=root, check=False, capture_output=True, text=True, timeout=12)
    if event != "UserPromptSubmit" or result.returncode != 0:
        return 0
    try:
        status = json.loads(result.stdout)
    except json.JSONDecodeError:
        return 0
    if isinstance(status, dict):
        emit_codex_context(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
