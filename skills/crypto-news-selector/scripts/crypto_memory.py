#!/usr/bin/env python3
"""Manage ~/.crypto credentials, trade events, and LLM Wiki skeleton."""

import argparse
import datetime as dt
import getpass
import json
import os
import secrets
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence


ROOT = Path.home() / ".crypto"
CONFIG = ROOT / "config.json"
WIKI = ROOT / "llm-wiki"
LEDGER = ROOT / "trades" / "ledger.jsonl"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def secure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def atomic_write(path: Path, content: str, mode: int) -> None:
    secure_directory(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".%s." % path.name, dir=str(path.parent))
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        os.chmod(path, mode)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def ensure_file(path: Path, content: str) -> None:
    if not path.exists():
        atomic_write(path, content, 0o600)


def initialize() -> None:
    secure_directory(ROOT)
    secure_directory(WIKI)
    secure_directory(WIKI / "knowledge")
    secure_directory(WIKI / "sources")
    secure_directory(WIKI / "reviews")
    secure_directory(LEDGER.parent)
    ensure_file(WIKI / "llms.txt", "# Crypto LLM Wiki\n\nRead index.md, knowledge/rules.md, knowledge/advantages.md and knowledge/pitfalls.md before every recommendation.\n")
    ensure_file(WIKI / "index.md", "# Crypto Research Index\n\n## Knowledge\n- [Rules](knowledge/rules.md)\n- [Advantages](knowledge/advantages.md)\n- [Pitfalls](knowledge/pitfalls.md)\n\n## Reviews\n\n## Sources\n")
    ensure_file(WIKI / "knowledge" / "rules.md", "# Decision Rules\n\n")
    ensure_file(WIKI / "knowledge" / "advantages.md", "# Verified Advantages\n\n")
    ensure_file(WIKI / "knowledge" / "pitfalls.md", "# Repeated Pitfalls\n\n")
    ensure_file(LEDGER, "")
    print(json.dumps({"status": "ready", "root": str(ROOT)}, ensure_ascii=False))


def configure_binance() -> None:
    initialize()
    api_key = getpass.getpass("Binance API Key (hidden): ").strip()
    api_secret = getpass.getpass("Binance API Secret (hidden): ").strip()
    if not api_key or not api_secret:
        raise ValueError("API Key and Secret are required")
    payload = {"binance": {"apiKey": api_key, "apiSecret": api_secret}, "updatedAt": now_iso()}
    atomic_write(CONFIG, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", 0o600)
    print(json.dumps({"status": "configured", "config": str(CONFIG), "permissions": "0600"}, ensure_ascii=False))


def append_event(event: Dict[str, object]) -> None:
    initialize()
    descriptor = os.open(str(LEDGER), os.O_WRONLY | os.O_APPEND, 0o600)
    try:
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.chmod(LEDGER, 0o600)


def read_events() -> List[Dict[str, object]]:
    initialize()
    events: List[Dict[str, object]] = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                events.append(value)
    return events


def read_rationale(path_value: str) -> Dict[str, object]:
    path = Path(path_value).expanduser()
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Rationale file must contain a JSON object")
    required_text_fields = (
        "strategyMode",
        "batchId",
        "portfolioContext",
        "summary",
        "catalyst",
        "technicalSetup",
        "derivativesConfirmation",
        "tradePlan",
        "positionSizingReason",
        "invalidation",
        "confidence",
        "dataCutoff",
    )
    missing = [field for field in required_text_fields if not isinstance(value.get(field), str) or not str(value[field]).strip()]
    if missing:
        raise ValueError("Rationale is missing non-empty fields: %s" % ", ".join(missing))
    sources = value.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Rationale sources must be a non-empty list")
    return value


def open_trade(args: argparse.Namespace) -> None:
    trade_id = "T-%s-%s" % (dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S"), secrets.token_hex(3))
    rationale = read_rationale(args.rationale_file)
    event: Dict[str, object] = {"type": "OPEN", "tradeId": trade_id, "timestamp": now_iso(), "symbol": args.symbol.upper(), "side": args.side, "entry": args.entry, "quantity": args.quantity, "planId": args.plan_id, "strategyMode": rationale["strategyMode"], "batchId": rationale["batchId"], "rationale": rationale, "note": args.note}
    append_event(event)
    print(json.dumps({"status": "recorded", "tradeId": trade_id}, ensure_ascii=False))


def close_trade(args: argparse.Namespace) -> None:
    events = read_events()
    opened = next((event for event in events if event.get("type") == "OPEN" and event.get("tradeId") == args.trade_id), None)
    already_closed = any(event.get("type") == "CLOSE" and event.get("tradeId") == args.trade_id for event in events)
    if opened is None:
        raise ValueError("Trade ID not found")
    if already_closed:
        raise ValueError("Trade is already closed")
    entry = float(opened["entry"])
    quantity = float(opened["quantity"]) + sum(float(event.get("quantityDelta", 0)) for event in events if event.get("type") == "ADJUST" and event.get("tradeId") == args.trade_id)
    if quantity <= 0:
        raise ValueError("Trade has no remaining quantity to close")
    direction = 1.0 if opened["side"] == "LONG" else -1.0
    gross_pnl = (args.exit - entry) * quantity * direction
    net_pnl = gross_pnl - args.fees
    event: Dict[str, object] = {"type": "CLOSE", "tradeId": args.trade_id, "timestamp": now_iso(), "exit": args.exit, "fees": args.fees, "grossPnl": round(gross_pnl, 8), "netPnl": round(net_pnl, 8), "note": args.note}
    append_event(event)
    print(json.dumps({"status": "closed", "tradeId": args.trade_id, "netPnl": round(net_pnl, 8), "reviewRequired": str(WIKI / "reviews" / (args.trade_id + ".md"))}, ensure_ascii=False))


def adjust_trade(args: argparse.Namespace) -> None:
    events = read_events()
    opened = next((event for event in events if event.get("type") == "OPEN" and event.get("tradeId") == args.trade_id), None)
    if opened is None:
        raise ValueError("Trade ID not found")
    if any(event.get("type") == "CLOSE" and event.get("tradeId") == args.trade_id for event in events):
        raise ValueError("Trade is already closed")
    current_quantity = float(opened["quantity"]) + sum(float(event.get("quantityDelta", 0)) for event in events if event.get("type") == "ADJUST" and event.get("tradeId") == args.trade_id)
    remaining_quantity = current_quantity + args.quantity_delta
    if remaining_quantity <= 0:
        raise ValueError("Use close for a full exit; adjust must leave a positive quantity")
    event: Dict[str, object] = {"type": "ADJUST", "tradeId": args.trade_id, "timestamp": now_iso(), "quantityDelta": args.quantity_delta, "price": args.price, "fees": args.fees, "remainingQuantity": remaining_quantity, "note": args.note}
    append_event(event)
    print(json.dumps({"status": "adjusted", "tradeId": args.trade_id, "remainingQuantity": remaining_quantity}, ensure_ascii=False))


def show_context() -> None:
    initialize()
    required = [WIKI / "llms.txt", WIKI / "index.md", WIKI / "knowledge" / "rules.md", WIKI / "knowledge" / "advantages.md", WIKI / "knowledge" / "pitfalls.md"]
    missing = [str(path) for path in required if not path.is_file() or not os.access(path, os.R_OK)]
    if missing:
        raise RuntimeError("Unreadable required Wiki files: %s" % ", ".join(missing))
    print(json.dumps({"status": "ready", "mustRead": [str(path) for path in required], "reviewsDirectory": str(WIKI / "reviews"), "sourcesDirectory": str(WIKI / "sources"), "ledger": str(LEDGER)}, ensure_ascii=False, indent=2))


def positive_number(value: str) -> float:
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def non_negative_number(value: str) -> float:
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return number


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("configure-binance")
    commands.add_parser("context")
    open_parser = commands.add_parser("open")
    open_parser.add_argument("--symbol", required=True)
    open_parser.add_argument("--side", choices=("LONG", "SHORT"), required=True)
    open_parser.add_argument("--entry", type=positive_number, required=True)
    open_parser.add_argument("--quantity", type=positive_number, required=True)
    open_parser.add_argument("--plan-id", required=True)
    open_parser.add_argument("--rationale-file", required=True, help="JSON file containing the complete recommendation rationale snapshot")
    open_parser.add_argument("--note", default="")
    close_parser = commands.add_parser("close")
    close_parser.add_argument("--trade-id", required=True)
    close_parser.add_argument("--exit", type=positive_number, required=True)
    close_parser.add_argument("--fees", type=non_negative_number, default=0.0)
    close_parser.add_argument("--note", default="")
    adjust_parser = commands.add_parser("adjust")
    adjust_parser.add_argument("--trade-id", required=True)
    adjust_parser.add_argument("--quantity-delta", type=float, required=True, help="Positive for adding, negative for partial closing")
    adjust_parser.add_argument("--price", type=positive_number, required=True)
    adjust_parser.add_argument("--fees", type=non_negative_number, default=0.0)
    adjust_parser.add_argument("--note", default="")
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init": initialize()
        elif args.command == "configure-binance": configure_binance()
        elif args.command == "context": show_context()
        elif args.command == "open": open_trade(args)
        elif args.command == "adjust": adjust_trade(args)
        else: close_trade(args)
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
