#!/usr/bin/env python3
"""Validate a component-validation Mock change manifest."""

import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Dict


CASE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
BLOCKED_PARTS = {".git", ".vscode"}


def fail(message: str) -> None:
    raise ValueError(message)


def require_dict(value: Any, field: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        fail("{} 必须是对象".format(field))
    return value


def require_text(value: Any, field: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        fail("{} 必须是{}字符串".format(field, "" if allow_empty else "非空"))
    return value


def require_hash(value: Any, field: str, allow_null: bool = False) -> None:
    if allow_null and value is None:
        return
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        fail("{} 必须是 64 位小写 SHA-256".format(field))


def validate_entry(value: Any, index: int) -> None:
    prefix = "entries[{}]".format(index)
    entry = require_dict(value, prefix)
    raw_path = require_text(entry.get("path"), "{}.path".format(prefix))
    path = PurePosixPath(raw_path)
    if path.is_absolute() or ".." in path.parts or any(
        part in BLOCKED_PARTS for part in path.parts
    ):
        fail("{}.path 必须是安全的仓库相对路径".format(prefix))

    operation = entry.get("operation")
    if operation not in {"modified", "created"}:
        fail("{}.operation 必须是 modified 或 created".format(prefix))

    location = require_dict(entry.get("location"), "{}.location".format(prefix))
    start_line = location.get("startLine")
    end_line = location.get("endLine")
    if isinstance(start_line, bool) or not isinstance(start_line, int) or start_line < 1:
        fail("{}.location.startLine 必须是正整数".format(prefix))
    if isinstance(end_line, bool) or not isinstance(end_line, int) or end_line < start_line:
        fail("{}.location.endLine 必须不小于 startLine".format(prefix))
    require_text(location.get("symbol"), "{}.location.symbol".format(prefix), True)
    require_text(location.get("anchor"), "{}.location.anchor".format(prefix))

    require_text(entry.get("summary"), "{}.summary".format(prefix))
    require_text(entry.get("beforeSnippet"), "{}.beforeSnippet".format(prefix), operation == "created")
    require_text(entry.get("afterSnippet"), "{}.afterSnippet".format(prefix))
    require_hash(
        entry.get("beforeFileSha256"),
        "{}.beforeFileSha256".format(prefix),
        operation == "created",
    )
    if operation == "created" and entry.get("beforeFileSha256") is not None:
        fail("created 条目的 beforeFileSha256 必须为 null")
    require_hash(entry.get("afterFileSha256"), "{}.afterFileSha256".format(prefix))


def validate(payload: Any) -> None:
    root = require_dict(payload, "root")
    if root.get("version") != 1:
        fail("version 当前必须为 1")
    case_name = root.get("caseName")
    if not isinstance(case_name, str) or not CASE_NAME_PATTERN.fullmatch(case_name):
        fail("caseName 只能包含字母、数字、点、下划线和短横线")
    repo_root = Path(require_text(root.get("repoRoot"), "repoRoot"))
    if not repo_root.is_absolute():
        fail("repoRoot 必须是绝对路径")
    entries = root.get("entries")
    if not isinstance(entries, list) or not entries:
        fail("entries 必须是非空数组")
    for index, entry in enumerate(entries):
        validate_entry(entry, index)


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: validate_mock_changes.py <mock-changes.json>", file=sys.stderr)
        return 2
    input_path = Path(sys.argv[1])
    try:
        with input_path.open("r", encoding="utf-8-sig") as input_file:
            validate(json.load(input_file))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print("校验失败: {}".format(error), file=sys.stderr)
        return 1
    print("校验通过: {}".format(input_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
