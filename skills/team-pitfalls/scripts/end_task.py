import argparse
import json

from task_lifecycle import read_state, state_path, utc_now, validate_task_id, write_state


def main() -> int:
    parser = argparse.ArgumentParser(description="低成本完成 team-pitfalls 后置复盘状态")
    parser.add_argument("--task-id", required=True, help="与 begin_task.py 相同的任务 ID")
    parser.add_argument("--result", required=True, choices=("recorded", "skipped"), help="本轮沉淀结果")
    parser.add_argument("--entry-id", action="append", default=[], help="recorded 时写入或更新的条目 ID，可重复")
    parser.add_argument("--reason", help="skipped 时必填，使用一句话说明原因")
    parser.add_argument("--verbose", action="store_true", help="输出完整状态，默认只输出紧凑摘要")
    args = parser.parse_args()

    task_id = validate_task_id(args.task_id)
    path = state_path(task_id)
    state = read_state(path)
    if state.get("task_id") != task_id or state.get("status") != "begun":
        raise SystemExit("任务状态无效或已经结束")

    entry_ids = list(dict.fromkeys(value.strip() for value in args.entry_id if value.strip()))
    reason = (args.reason or "").strip()
    if args.result == "recorded" and not entry_ids:
        raise SystemExit("--result recorded 时至少提供一个 --entry-id")
    if args.result == "skipped" and not reason:
        raise SystemExit("--result skipped 时必须提供非空 --reason")

    state.update(
        {
            "status": "completed",
            "completed_at": utc_now(),
            "result": args.result,
            "entry_ids": entry_ids,
            "reason": reason,
        }
    )
    write_state(path, state)
    output: dict[str, object] = {"task_id": task_id, "result": args.result, "entry_ids": entry_ids}
    if args.verbose:
        output["state"] = state
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.verbose else None, separators=None if args.verbose else (",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
