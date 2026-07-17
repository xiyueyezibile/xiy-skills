import argparse

from task_lifecycle import print_state, read_state, state_path, utc_now, validate_task_id, write_state


def main() -> int:
    parser = argparse.ArgumentParser(description="完成 team-pitfalls 后置复盘状态")
    parser.add_argument("--task-id", required=True, help="与 begin_task.py 相同的任务 ID")
    parser.add_argument("--result", required=True, choices=("recorded", "skipped"), help="本轮沉淀结果")
    parser.add_argument(
        "--confirmed-read",
        action="append",
        default=[],
        help="已读取的基础文件名或完整路径，至少确认 llms.txt 和 index.md，可重复",
    )
    parser.add_argument("--entry-id", action="append", default=[], help="recorded 时写入或更新的条目 ID，可重复")
    parser.add_argument("--reason", help="skipped 时必填，说明为什么不新增或更新知识")
    args = parser.parse_args()

    task_id = validate_task_id(args.task_id)
    path = state_path(task_id)
    state = read_state(path)
    if state.get("task_id") != task_id:
        raise SystemExit("任务状态与 --task-id 不一致")
    if state.get("status") != "begun":
        raise SystemExit(f"任务状态不是 begun，不能重复结束: {state.get('status')}")

    entry_ids = list(dict.fromkeys(value.strip() for value in args.entry_id if value.strip()))
    reason = (args.reason or "").strip()
    if args.result == "recorded" and not entry_ids:
        raise SystemExit("--result recorded 时至少提供一个 --entry-id")
    if args.result == "skipped" and not reason:
        raise SystemExit("--result skipped 时必须提供非空 --reason")

    required_reads = state.get("required_reads")
    if not isinstance(required_reads, list) or len(required_reads) < 2:
        raise SystemExit("前置状态没有完整记录 llms.txt 和 index.md")
    confirmed_reads = {value.strip() for value in args.confirmed_read if value.strip()}
    confirmed_names = {value.rsplit("/", 1)[-1] for value in confirmed_reads}
    missing_reads = [
        str(value)
        for value in required_reads
        if str(value) not in confirmed_reads and str(value).rsplit("/", 1)[-1] not in confirmed_names
    ]
    if missing_reads:
        raise SystemExit(f"缺少 --confirmed-read: {', '.join(missing_reads)}")

    state.update(
        {
            "status": "completed",
            "completed_at": utc_now(),
            "result": args.result,
            "entry_ids": entry_ids,
            "reason": reason,
            "confirmed_reads": sorted(confirmed_reads),
        }
    )
    write_state(path, state)
    print_state(state, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
