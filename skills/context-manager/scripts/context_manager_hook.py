#!/usr/bin/env python3
"""Emit saved context as a Codex/Trae-style additionalContext JSON field."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from context_manager import ContextStore


def main() -> None:
    data_dir = Path.home() / ".context-manage"
    try:
        incoming = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        incoming = {}
    context = ContextStore(data_dir).markdown()
    output = dict(incoming) if isinstance(incoming, dict) else {}
    output["additionalContext"] = context
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
