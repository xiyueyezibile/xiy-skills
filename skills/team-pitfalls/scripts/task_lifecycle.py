import datetime as dt
import hashlib
import json
import re
import tempfile
from pathlib import Path


STATE_SCHEMA_VERSION = 1
SAFE_TASK_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def validate_task_id(task_id: str) -> str:
    value = task_id.strip()
    if not SAFE_TASK_ID_RE.fullmatch(value):
        raise SystemExit("--task-id 只能包含字母、数字、点、下划线和短横线，长度不超过 128")
    return value


def state_path(task_id: str) -> Path:
    digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()
    return Path(tempfile.gettempdir()) / "team-pitfalls-lifecycle" / f"{digest}.json"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_state(path: Path) -> dict[str, object]:
    if not path.exists():
        raise SystemExit(f"未找到任务前置状态，请先运行 begin_task.py: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != STATE_SCHEMA_VERSION:
        raise SystemExit(f"任务状态格式无效: {path}")
    return value


def write_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_state(state: dict[str, object], path: Path) -> None:
    payload = {"state_file": str(path), **state}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
