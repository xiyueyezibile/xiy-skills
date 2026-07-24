#!/usr/bin/env python3
"""Manage persistent URL mappings and screenshot retention for component validation."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qsl, urlparse


ROOT = Path.home() / ".component-validation"
URLS_FILE = ROOT / "page-urls.json"
CASES_DIR = ROOT / "cases"
NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
SENSITIVE_QUERY_KEYS = {
    "access_token",
    "auth",
    "authorization",
    "code",
    "cookie",
    "credential",
    "jwt",
    "password",
    "secret",
    "session",
    "signature",
    "sign",
    "ticket",
    "token",
}


def fail(message: str) -> None:
    raise ValueError(message)


def ensure_name(value: str, field: str) -> str:
    if not NAME_PATTERN.fullmatch(value):
        fail("{} 只能包含字母、数字、点、下划线和短横线".format(field))
    return value


def load_registry() -> Dict[str, Any]:
    if not URLS_FILE.exists():
        return {"version": 1, "entries": {}}
    with URLS_FILE.open("r", encoding="utf-8-sig") as input_file:
        payload = json.load(input_file)
    if payload.get("version") != 1 or not isinstance(payload.get("entries"), dict):
        fail("{} 格式无效".format(URLS_FILE))
    return payload


def write_registry(payload: Dict[str, Any]) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    temp_file = URLS_FILE.with_suffix(".json.tmp")
    with temp_file.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, ensure_ascii=False, indent=2, sort_keys=True)
        output_file.write("\n")
    temp_file.replace(URLS_FILE)


def validate_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        fail("url 必须是完整的 http(s) URL")
    sensitive_keys = sorted(
        key for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() in SENSITIVE_QUERY_KEYS
    )
    if sensitive_keys:
        fail("url 包含敏感 query 参数: {}".format(", ".join(sensitive_keys)))
    if parsed.username or parsed.password:
        fail("url 不得包含用户名或密码")
    return value


def command_record_url(args: argparse.Namespace) -> None:
    repo = ensure_name(args.repo, "repo")
    page = ensure_name(args.page, "page")
    url = validate_url(args.url)
    registry = load_registry()
    key = "{}::{}".format(repo, page)
    registry["entries"][key] = {
        "repo": repo,
        "page": page,
        "url": url,
        "source": args.source,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    write_registry(registry)
    print(json.dumps(registry["entries"][key], ensure_ascii=False))


def command_resolve_url(args: argparse.Namespace) -> None:
    repo = ensure_name(args.repo, "repo")
    page = ensure_name(args.page, "page")
    entry = load_registry()["entries"].get("{}::{}".format(repo, page))
    if entry is None:
        print("未找到页面 URL: {}::{}".format(repo, page), file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(entry, ensure_ascii=False))


def command_prepare_case(args: argparse.Namespace) -> None:
    case_name = ensure_name(args.case, "case")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    case_root = CASES_DIR / case_name
    run_dir = case_root / timestamp
    suffix = 2
    while run_dir.exists():
        run_dir = case_root / "{}-{}".format(timestamp, suffix)
        suffix += 1
    screenshots_dir = run_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=False)
    print(json.dumps({
        "runDir": str(run_dir),
        "screenshotsDir": str(screenshots_dir),
        "browserActions": str(run_dir / "browser-actions.json"),
        "mockChanges": str(run_dir / "mock-changes.json"),
        "report": str(run_dir / "report.md"),
    }, ensure_ascii=False))


def command_prune_screenshots(args: argparse.Namespace) -> None:
    if args.limit < 1:
        fail("limit 必须大于 0")
    screenshots = sorted(
        CASES_DIR.glob("**/*.png"),
        key=lambda path: (path.stat().st_mtime_ns, str(path)),
        reverse=True,
    ) if CASES_DIR.exists() else []
    removed = screenshots[args.limit:]
    for screenshot in removed:
        screenshot.unlink()
    print(json.dumps({
        "limit": args.limit,
        "found": len(screenshots),
        "kept": min(len(screenshots), args.limit),
        "removed": len(removed),
    }, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record-url")
    record.add_argument("--repo", required=True)
    record.add_argument("--page", required=True)
    record.add_argument("--url", required=True)
    record.add_argument(
        "--source",
        required=True,
        choices=["user", "browser", "config", "docs", "inferred-verified"],
    )
    record.set_defaults(handler=command_record_url)

    resolve = subparsers.add_parser("resolve-url")
    resolve.add_argument("--repo", required=True)
    resolve.add_argument("--page", required=True)
    resolve.set_defaults(handler=command_resolve_url)

    prepare = subparsers.add_parser("prepare-case")
    prepare.add_argument("--case", required=True)
    prepare.set_defaults(handler=command_prepare_case)

    prune = subparsers.add_parser("prune-screenshots")
    prune.add_argument("--limit", type=int, default=500)
    prune.set_defaults(handler=command_prune_screenshots)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        args.handler(args)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print("执行失败: {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
