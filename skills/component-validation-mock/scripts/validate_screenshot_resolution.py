#!/usr/bin/env python3
"""校验 PNG 截图是否按 CSS viewport 和 DPR 输出原生像素。"""

import argparse
import struct
import sys
from pathlib import Path
from typing import Tuple


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def read_png_size(path: Path) -> Tuple[int, int]:
    with path.open("rb") as png_file:
        header = png_file.read(24)
    if len(header) < 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise ValueError("文件不是有效的 PNG")
    return struct.unpack(">II", header[16:24])


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须为正整数")
    return parsed


def scale_factor(value: str) -> float:
    parsed = float(value)
    if parsed < 2 or parsed > 4:
        raise argparse.ArgumentTypeError("必须在 2 到 4 之间")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png", type=Path)
    parser.add_argument("--css-width", type=positive_int, required=True)
    parser.add_argument("--css-height", type=positive_int, required=True)
    parser.add_argument("--dpr", type=scale_factor, required=True)
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="全页截图只严格校验宽度，高度允许超过最小视口高度",
    )
    args = parser.parse_args()

    try:
        actual_width, actual_height = read_png_size(args.png)
    except (OSError, ValueError) as error:
        print("校验失败: {}".format(error), file=sys.stderr)
        return 1

    expected_width = round(args.css_width * args.dpr)
    expected_height = round(args.css_height * args.dpr)
    width_matches = actual_width == expected_width
    height_matches = (
        actual_height >= expected_height
        if args.full_page
        else actual_height == expected_height
    )
    if not width_matches or not height_matches:
        relation = "至少" if args.full_page else "等于"
        print(
            "校验失败: 实际 {}x{}，期望宽度 {}、高度{} {}".format(
                actual_width,
                actual_height,
                expected_width,
                relation,
                expected_height,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        "校验通过: {} 为 {}x{}，CSS viewport {}x{}，DPR {}".format(
            args.png,
            actual_width,
            actual_height,
            args.css_width,
            args.css_height,
            args.dpr,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
