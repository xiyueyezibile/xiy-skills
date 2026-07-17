import argparse
import json
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Optional


def add_json_source_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", help="内联 JSON 对象；复杂内容优先使用 --json-file")
    group.add_argument("--json-file", help="UTF-8 JSON 文件路径；传 - 时从标准输入读取")


def load_json_object(json_text: Optional[str], json_file: Optional[str]) -> Optional[dict[str, object]]:
    if json_text is None and json_file is None:
        return None

    source = "--json"
    raw = json_text or ""
    if json_file is not None:
        source = "stdin" if json_file == "-" else json_file
        if json_file == "-":
            import sys

            raw = sys.stdin.read()
        else:
            path = Path(json_file).expanduser()
            if not path.is_file():
                raise SystemExit(f"--json-file 不存在或不是文件: {path}")
            try:
                raw = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError as error:
                raise SystemExit(f"--json-file 必须使用 UTF-8 编码: {path}: {error}") from error

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SystemExit(f"JSON 解析失败 ({source}:{error.lineno}:{error.colno}): {error.msg}") from error
    if not isinstance(parsed, dict):
        raise SystemExit(f"JSON 顶层必须是对象: {source}")
    return parsed


def safe_slug(value: str, fallback: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    output: list[str] = []
    pending_dash = False
    for character in normalized:
        if character.isalnum() or character in "._-":
            if pending_dash and output:
                output.append("-")
            output.append(character)
            pending_dash = False
        else:
            pending_dash = True
    rendered = "".join(output).strip("._-")
    return rendered or fallback


def artifact_reference(raw_path: str, repo: str, artifact_root: str = "artifacts/repos") -> str:
    source_name = Path(raw_path).name
    if not source_name or source_name in {".", ".."}:
        raise SystemExit("--path 必须包含文件名")
    source = Path(source_name)
    suffix = source.suffix.lower()
    stem = safe_slug(source.stem, "artifact")
    repo_slug = safe_slug(repo, "repo")

    root = PurePosixPath(artifact_root.replace("\\", "/"))
    if root.is_absolute() or ".." in root.parts:
        raise SystemExit("--artifact-root 必须是安全的相对路径")
    return str(root / repo_slug / f"{stem}{suffix}")
