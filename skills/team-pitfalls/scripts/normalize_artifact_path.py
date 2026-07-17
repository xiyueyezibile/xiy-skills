import argparse
import json

from cli_support import artifact_reference


def main() -> int:
    parser = argparse.ArgumentParser(description="生成稳定的 team-pitfalls 对外产物相对路径")
    parser.add_argument("--path", required=True, help="原始文件路径；仅使用最后一级文件名")
    parser.add_argument("--repo", required=True, help="仓库名，用于 artifacts/repos 下的隔离目录")
    parser.add_argument("--artifact-root", default="artifacts/repos", help="产物相对根目录")
    args = parser.parse_args()

    reference = artifact_reference(args.path, args.repo, args.artifact_root)
    print(json.dumps({"artifact_reference": reference, "encoding": "utf-8"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
