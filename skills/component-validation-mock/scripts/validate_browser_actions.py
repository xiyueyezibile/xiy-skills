#!/usr/bin/env python3
"""Validate component-validation browser action files."""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse


ALLOWED_ACTIONS = {
    "open",
    "waitFor",
    "click",
    "fill",
    "press",
    "select",
    "scroll",
    "screenshot",
}
LOCATOR_ACTIONS = {"waitFor", "click", "fill", "press", "select"}
ALLOWED_LOCATORS = {"testId", "role", "label", "text", "css"}
CASE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def fail(message: str) -> None:
    raise ValueError(message)


def require_dict(value: Any, field: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        fail("{} 必须是对象".format(field))
    return value


def require_positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        fail("{} 必须是正整数".format(field))
    return value


def validate_locator(value: Any, field: str) -> None:
    locator = require_dict(value, field)
    by = locator.get("by")
    target = locator.get("value")
    if by not in ALLOWED_LOCATORS:
        fail("{}.by 不受支持: {}".format(field, by))
    if not isinstance(target, str) or not target.strip():
        fail("{}.value 必须是非空字符串".format(field))
    if "name" in locator and (
        not isinstance(locator["name"], str) or not locator["name"].strip()
    ):
        fail("{}.name 必须是非空字符串".format(field))


def validate_screenshot_path(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        fail("{} 必须是非空相对路径".format(field))
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        fail("{} 不得是绝对路径或包含 '..'".format(field))
    if path.suffix.lower() != ".png":
        fail("{} 必须使用 .png 扩展名".format(field))


def parse_open_url(value: str, field: str) -> Any:
    if not isinstance(value, str) or not value.strip():
        fail("{} 必须是非空字符串".format(field))
    parsed = urlparse(value)
    if value.startswith("/"):
        return parsed
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return parsed
    fail("{} 必须是站内绝对路径或 http(s) URL".format(field))


def validate_action(action: Any, index: int) -> str:
    item = require_dict(action, "actions[{}]".format(index))
    action_type = item.get("type")
    prefix = "actions[{}]".format(index)
    if action_type not in ALLOWED_ACTIONS:
        fail("{}.type 不受支持: {}".format(prefix, action_type))

    if action_type in LOCATOR_ACTIONS:
        validate_locator(item.get("locator"), "{}.locator".format(prefix))
    elif action_type == "scroll" and "locator" in item:
        validate_locator(item["locator"], "{}.locator".format(prefix))
    elif action_type == "screenshot" and "locator" in item:
        validate_locator(item["locator"], "{}.locator".format(prefix))

    if action_type == "open":
        parse_open_url(item.get("path"), "{}.path".format(prefix))
    elif action_type == "waitFor":
        if item.get("state") not in {"visible", "hidden", "attached"}:
            fail("{}.state 不受支持".format(prefix))
        timeout = item.get("timeoutMs", 10000)
        require_positive_int(timeout, "{}.timeoutMs".format(prefix))
        if timeout > 30000:
            fail("{}.timeoutMs 不得超过 30000".format(prefix))
    elif action_type in {"fill", "select"}:
        if not isinstance(item.get("value"), str):
            fail("{}.value 必须是字符串".format(prefix))
    elif action_type == "press":
        if not isinstance(item.get("key"), str) or not item["key"].strip():
            fail("{}.key 必须是非空字符串".format(prefix))
    elif action_type == "scroll":
        x = item.get("x", 0)
        y = item.get("y", 0)
        if isinstance(x, bool) or not isinstance(x, int):
            fail("{}.x 必须是整数".format(prefix))
        if isinstance(y, bool) or not isinstance(y, int):
            fail("{}.y 必须是整数".format(prefix))
    elif action_type == "screenshot":
        validate_screenshot_path(item.get("path"), "{}.path".format(prefix))
        if "fullPage" in item and not isinstance(item["fullPage"], bool):
            fail("{}.fullPage 必须是布尔值".format(prefix))

    return action_type


def validate_open_matches_target(action: Any, index: int, target_url: str) -> None:
    item = require_dict(action, "actions[{}]".format(index))
    if item.get("type") != "open":
        return
    prefix = "actions[{}]".format(index)
    target = urlparse(target_url)
    opened = parse_open_url(item.get("path"), "{}.path".format(prefix))
    if (opened.path, opened.query, opened.fragment) != (
        target.path,
        target.query,
        target.fragment,
    ):
        fail(
            "{}.path 必须与 targetUrl 保持相同 pathname/query/hash；不得为了 Mock 追加、删除或重排 URL 参数".format(
                prefix
            )
        )


def validate(payload: Any) -> None:
    root = require_dict(payload, "root")
    if root.get("version") != 1:
        fail("version 当前必须为 1")

    case_name = root.get("caseName")
    if not isinstance(case_name, str) or not CASE_NAME_PATTERN.fullmatch(case_name):
        fail("caseName 只能包含字母、数字、点、下划线和短横线")

    base_url = root.get("baseUrl")
    if not isinstance(base_url, str):
        fail("baseUrl 必须是字符串")
    parsed_url = urlparse(base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        fail("baseUrl 必须是有效的 http(s) URL")

    target_url = root.get("targetUrl")
    if not isinstance(target_url, str):
        fail("targetUrl 必须是用户目标页面完整 URL")
    parsed_target_url = urlparse(target_url)
    if parsed_target_url.scheme not in {"http", "https"} or not parsed_target_url.netloc:
        fail("targetUrl 必须是有效的 http(s) URL")

    device = require_dict(root.get("device"), "device")
    if device.get("kind") not in {"desktop", "mobile"}:
        fail("device.kind 必须是 desktop 或 mobile")
    viewport = require_dict(device.get("viewport"), "device.viewport")
    require_positive_int(viewport.get("width"), "device.viewport.width")
    require_positive_int(viewport.get("height"), "device.viewport.height")

    scale = device.get("deviceScaleFactor")
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        fail("device.deviceScaleFactor 必须是数字")
    if scale < 2 or scale > 4:
        fail("device.deviceScaleFactor 必须在 2 到 4 之间")
    if device.get("requireNativeScale") is not True:
        fail("device.requireNativeScale 必须为 true")
    if "isTouch" in device and not isinstance(device["isTouch"], bool):
        fail("device.isTouch 必须是布尔值")
    if device["kind"] == "mobile" and device.get("isTouch") is not True:
        fail("mobile 设备必须设置 device.isTouch 为 true")

    actions = root.get("actions")
    if not isinstance(actions, list) or not actions:
        fail("actions 必须是非空数组")
    action_types: List[str] = [
        validate_action(action, index) for index, action in enumerate(actions)
    ]
    for index, action in enumerate(actions):
        validate_open_matches_target(action, index, target_url)
    if "open" not in action_types:
        fail("actions 至少包含一个 open")
    if "screenshot" not in action_types:
        fail("actions 至少包含一个 screenshot")


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: validate_browser_actions.py <browser-actions.json>", file=sys.stderr)
        return 2

    input_path = Path(sys.argv[1])
    try:
        with input_path.open("r", encoding="utf-8-sig") as input_file:
            payload = json.load(input_file)
        validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print("校验失败: {}".format(error), file=sys.stderr)
        return 1

    print("校验通过: {}".format(input_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
