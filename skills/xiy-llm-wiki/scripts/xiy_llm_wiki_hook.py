#!/usr/bin/env python3
"""Codex hook adapter for configured Xiy LLM Wiki repository watchers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".xiy" / "config.json"
SKILL_SCRIPT = Path(__file__).with_name("llm_wiki.py")
EXTRACT_SCRIPT = Path(__file__).with_name("xiy_llm_wiki_extract.py")


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


def start_background_extraction(payload: dict[str, object], status: dict[str, object]) -> None:
    transcript_path = payload.get("transcript_path")
    if not isinstance(transcript_path, str) or not transcript_path:
        return
    job = {
        "source_repo": status.get("source_repo", ""),
        "wiki_repo": status.get("wiki_repo", ""),
        "transcript_path": transcript_path,
    }
    try:
        subprocess.Popen(
            [sys.executable, str(EXTRACT_SCRIPT), json.dumps(job, ensure_ascii=False)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return


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
            start_background_extraction(payload, status)
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
