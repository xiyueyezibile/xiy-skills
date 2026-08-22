#!/usr/bin/env python3
"""Prepare and execute one confirmed Binance USD-M market entry with TP/SL.

The script is deliberately two-phase. ``prepare`` only persists an expiring
proposal. ``execute`` requires the exact proposal token and is the only command
that can call Binance write endpoints.
"""

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


DEFAULT_DIR_NAME = ".crypto"


def find_workspace_root(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / "AGENTS.md").is_file():
            return candidate
    return current


def crypto_root() -> Path:
    override = os.environ.get("CRYPTO_ROOT") or os.environ.get("CRYPTO_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return find_workspace_root() / DEFAULT_DIR_NAME


ROOT = crypto_root()
CONFIG = ROOT / "config.json"
CONFIRMATIONS = ROOT / "confirmations"
DEFAULT_BASE_URL = "https://fapi.binance.com"
USER_AGENT = "crypto-news-selector-confirmed-trade/1.0"


def now_ms() -> int:
    return int(time.time() * 1000)


def iso_from_ms(value: int) -> str:
    return dt.datetime.fromtimestamp(value / 1000, dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def secure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def atomic_json(path: Path, value: Dict[str, object]) -> None:
    secure_directory(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".%s." % path.name, dir=str(path.parent))
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def load_config() -> Dict[str, object]:
    if not CONFIG.is_file():
        raise RuntimeError("Missing %s; configure Binance credentials first" % CONFIG)
    if CONFIG.stat().st_mode & 0o077:
        raise RuntimeError("Unsafe config permissions; run chmod 600 %s" % CONFIG)
    value = json.loads(CONFIG.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Invalid %s" % CONFIG)
    return value


def credentials(config: Dict[str, object]) -> Tuple[str, str]:
    value = config.get("binance")
    if not isinstance(value, dict) or not value.get("apiKey") or not value.get("apiSecret"):
        raise RuntimeError("Binance credentials are not configured")
    return str(value["apiKey"]), str(value["apiSecret"])


def binance_base_url(config: Dict[str, object]) -> str:
    value = config.get("binance")
    if isinstance(value, dict) and value.get("baseUrl"):
        return str(value["baseUrl"]).rstrip("/")
    return DEFAULT_BASE_URL


def public_request(base_url: str, path: str, params: Optional[Dict[str, str]] = None) -> object:
    query = urllib.parse.urlencode(params or {})
    url = base_url + path + (("?" + query) if query else "")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def signed_request(base_url: str, method: str, path: str, api_key: str, api_secret: str, params: Optional[Dict[str, str]] = None) -> object:
    values = dict(params or {})
    values.update({"timestamp": str(now_ms()), "recvWindow": "5000"})
    query = urllib.parse.urlencode(values)
    signature = hmac.new(api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
    request = urllib.request.Request(
        base_url + path + "?" + query + "&signature=" + signature,
        method=method,
        headers={"X-MBX-APIKEY": api_key, "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def as_decimal(value: object) -> Decimal:
    return Decimal(str(value))


def step_floor(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def symbol_rules(base_url: str, symbol: str) -> Dict[str, Decimal]:
    response = public_request(base_url, "/fapi/v1/exchangeInfo")
    if not isinstance(response, dict) or not isinstance(response.get("symbols"), list):
        raise RuntimeError("Unexpected exchangeInfo response")
    item = next((entry for entry in response["symbols"] if isinstance(entry, dict) and entry.get("symbol") == symbol), None)
    if not isinstance(item, dict) or item.get("status") != "TRADING" or item.get("contractType") != "PERPETUAL":
        raise RuntimeError("Symbol is not a TRADING perpetual contract")
    filters = {entry.get("filterType"): entry for entry in item.get("filters", []) if isinstance(entry, dict)}
    lot = filters.get("MARKET_LOT_SIZE") or filters.get("LOT_SIZE")
    price_filter = filters.get("PRICE_FILTER")
    min_notional = filters.get("MIN_NOTIONAL")
    if not isinstance(lot, dict) or not isinstance(price_filter, dict) or not isinstance(min_notional, dict):
        raise RuntimeError("Required Binance symbol filters are missing")
    return {
        "stepSize": as_decimal(lot["stepSize"]),
        "minQty": as_decimal(lot["minQty"]),
        "maxQty": as_decimal(lot["maxQty"]),
        "tickSize": as_decimal(price_filter["tickSize"]),
        "minNotional": as_decimal(min_notional.get("notional", "5")),
    }


def mark_price(base_url: str, symbol: str) -> Decimal:
    response = public_request(base_url, "/fapi/v1/premiumIndex", {"symbol": symbol})
    if not isinstance(response, dict) or not response.get("markPrice"):
        raise RuntimeError("Unexpected premiumIndex response")
    return as_decimal(response["markPrice"])


def proposal_path(token: str) -> Path:
    if not token or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in token):
        raise ValueError("Invalid confirmation token")
    return CONFIRMATIONS / (token + ".json")


def load_proposal(token: str) -> Dict[str, object]:
    path = proposal_path(token)
    if not path.is_file():
        raise RuntimeError("Confirmation proposal not found")
    if path.stat().st_mode & 0o077:
        raise RuntimeError("Unsafe confirmation file permissions")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Invalid confirmation proposal")
    return value


def prepare(args: argparse.Namespace) -> None:
    config = load_config()
    credentials(config)
    base_url = binance_base_url(config)
    symbol = args.symbol.upper()
    rules = symbol_rules(base_url, symbol)
    current_mark = mark_price(base_url, symbol)
    quantity = step_floor(as_decimal(args.quantity), rules["stepSize"])
    stop_loss = step_floor(as_decimal(args.stop_loss), rules["tickSize"])
    raw_levels = args.take_profit_level or []
    if args.take_profit is not None:
        raw_levels = [(args.take_profit, quantity)]
    if not raw_levels or len(raw_levels) > 3:
        raise ValueError("Provide between one and three take-profit levels")
    take_profit_levels: List[Dict[str, str]] = []
    total_take_profit_quantity = Decimal("0")
    previous_take_profit_price: Optional[Decimal] = None
    for index, (raw_price, raw_quantity) in enumerate(raw_levels, start=1):
        level_price = step_floor(as_decimal(raw_price), rules["tickSize"])
        level_quantity = step_floor(as_decimal(raw_quantity), rules["stepSize"])
        if level_quantity < rules["minQty"]:
            raise ValueError("Take-profit level quantity is below Binance minimum")
        if level_price * level_quantity < rules["minNotional"]:
            raise ValueError("Take-profit level notional is below Binance minimum")
        if args.side == "LONG" and level_price <= current_mark:
            raise ValueError("LONG take-profit levels must be above current mark")
        if args.side == "SHORT" and level_price >= current_mark:
            raise ValueError("SHORT take-profit levels must be below current mark")
        if previous_take_profit_price is not None:
            if args.side == "LONG" and level_price <= previous_take_profit_price:
                raise ValueError("LONG take-profit levels must be ordered from near to far")
            if args.side == "SHORT" and level_price >= previous_take_profit_price:
                raise ValueError("SHORT take-profit levels must be ordered from near to far")
        previous_take_profit_price = level_price
        total_take_profit_quantity += level_quantity
        take_profit_levels.append({"level": str(index), "triggerPrice": decimal_text(level_price), "quantity": decimal_text(level_quantity)})
    if quantity < rules["minQty"] or quantity > rules["maxQty"]:
        raise ValueError("Quantity is outside Binance MARKET_LOT_SIZE")
    if current_mark * quantity < rules["minNotional"] * Decimal("1.10"):
        raise ValueError("Order notional must keep at least a 10% buffer above Binance minimum")
    if total_take_profit_quantity > quantity:
        raise ValueError("Take-profit quantities exceed entry quantity")
    if args.side == "LONG" and stop_loss >= current_mark:
        raise ValueError("LONG stopLoss must be below current mark")
    if args.side == "SHORT" and stop_loss <= current_mark:
        raise ValueError("SHORT stopLoss must be above current mark")
    created_at = now_ms()
    token = secrets.token_urlsafe(12).replace("-", "").replace("_", "")
    proposal: Dict[str, object] = {
        "schemaVersion": 1,
        "token": token,
        "status": "PENDING",
        "createdAt": iso_from_ms(created_at),
        "expiresAt": iso_from_ms(created_at + args.ttl_seconds * 1000),
        "expiresAtMs": created_at + args.ttl_seconds * 1000,
        "planId": args.plan_id,
        "symbol": symbol,
        "side": args.side,
        "orderType": "MARKET",
        "quantity": decimal_text(quantity),
        "leverage": args.leverage,
        "marginType": args.margin_type,
        "stopLoss": decimal_text(stop_loss),
        "takeProfitLevels": take_profit_levels,
        "tailQuantity": decimal_text(quantity - total_take_profit_quantity),
        "workingType": "MARK_PRICE",
        "referenceMarkPrice": decimal_text(current_mark),
        "marketExecutionAtConfirmation": True,
        "requiresExactConfirmation": "确认执行 " + token,
    }
    atomic_json(proposal_path(token), proposal)
    print(json.dumps(proposal, ensure_ascii=False, indent=2))


def account_position_mode(base_url: str, api_key: str, api_secret: str) -> bool:
    response = signed_request(base_url, "GET", "/fapi/v1/positionSide/dual", api_key, api_secret)
    if not isinstance(response, dict):
        raise RuntimeError("Unexpected position mode response")
    value = response.get("dualSidePosition")
    return value is True or str(value).lower() == "true"


def active_symbol_positions(base_url: str, symbol: str, api_key: str, api_secret: str) -> List[Dict[str, object]]:
    response = signed_request(base_url, "GET", "/fapi/v2/positionRisk", api_key, api_secret, {"symbol": symbol})
    if not isinstance(response, list):
        raise RuntimeError("Unexpected positionRisk response")
    return [item for item in response if isinstance(item, dict) and as_decimal(item.get("positionAmt", "0")) != 0]


def active_symbol_algo_orders(base_url: str, symbol: str, api_key: str, api_secret: str) -> List[Dict[str, object]]:
    response = signed_request(base_url, "GET", "/fapi/v1/openAlgoOrders", api_key, api_secret, {"symbol": symbol})
    if not isinstance(response, list):
        raise RuntimeError("Unexpected openAlgoOrders response")
    return [item for item in response if isinstance(item, dict)]


def set_leverage(base_url: str, symbol: str, leverage: int, api_key: str, api_secret: str) -> object:
    return signed_request(base_url, "POST", "/fapi/v1/leverage", api_key, api_secret, {"symbol": symbol, "leverage": str(leverage)})


def set_margin_type(base_url: str, symbol: str, margin_type: str, api_key: str, api_secret: str) -> object:
    api_value = "CROSSED" if margin_type == "CROSS" else "ISOLATED"
    try:
        return signed_request(base_url, "POST", "/fapi/v1/marginType", api_key, api_secret, {"symbol": symbol, "marginType": api_value})
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8", errors="replace")
        if error.code == 400 and "No need to change margin type" in payload:
            return {"status": "UNCHANGED"}
        raise RuntimeError("Margin type change failed: HTTP %s %s" % (error.code, payload[:240]))


def entry_position_side(side: str, dual: bool) -> str:
    if not dual:
        return "BOTH"
    return "LONG" if side == "LONG" else "SHORT"


def entry_order_side(side: str) -> str:
    return "BUY" if side == "LONG" else "SELL"


def exit_order_side(side: str) -> str:
    return "SELL" if side == "LONG" else "BUY"


def place_market(base_url: str, symbol: str, side: str, position_side: str, quantity: str, client_order_id: str, api_key: str, api_secret: str, reduce_only: bool = False) -> Dict[str, object]:
    params = {
        "symbol": symbol,
        "side": side,
        "positionSide": position_side,
        "type": "MARKET",
        "quantity": quantity,
        "newOrderRespType": "RESULT",
        "newClientOrderId": client_order_id,
    }
    if reduce_only and position_side == "BOTH":
        params["reduceOnly"] = "true"
    response = signed_request(base_url, "POST", "/fapi/v1/order", api_key, api_secret, params)
    if not isinstance(response, dict):
        raise RuntimeError("Unexpected market order response")
    return response


def place_protection(base_url: str, symbol: str, side: str, position_side: str, order_type: str, trigger_price: str, client_algo_id: str, api_key: str, api_secret: str, quantity: Optional[str] = None) -> Dict[str, object]:
    params = {
        "algoType": "CONDITIONAL",
        "symbol": symbol,
        "side": side,
        "positionSide": position_side,
        "type": order_type,
        "triggerPrice": trigger_price,
        "workingType": "MARK_PRICE",
        "clientAlgoId": client_algo_id,
    }
    if quantity is None:
        params["closePosition"] = "true"
    else:
        params["quantity"] = quantity
        if position_side == "BOTH":
            params["reduceOnly"] = "true"
    response = signed_request(
        base_url,
        "POST",
        "/fapi/v1/algoOrder",
        api_key,
        api_secret,
        params,
    )
    if not isinstance(response, dict):
        raise RuntimeError("Unexpected algo order response")
    return response


def cancel_algo(base_url: str, algo_id: object, api_key: str, api_secret: str) -> None:
    if algo_id is None:
        return
    signed_request(base_url, "DELETE", "/fapi/v1/algoOrder", api_key, api_secret, {"algoId": str(algo_id)})


def execute(args: argparse.Namespace) -> None:
    proposal = load_proposal(args.token)
    if args.confirm != args.token:
        raise RuntimeError("Exact confirmation token mismatch")
    if proposal.get("status") != "PENDING":
        raise RuntimeError("Proposal is not pending; execution is idempotently blocked")
    if now_ms() > int(proposal["expiresAtMs"]):
        proposal["status"] = "EXPIRED"
        atomic_json(proposal_path(args.token), proposal)
        raise RuntimeError("Proposal expired; prepare a fresh order")
    config = load_config()
    api_key, api_secret = credentials(config)
    base_url = binance_base_url(config)
    symbol = str(proposal["symbol"])
    current_mark = mark_price(base_url, symbol)
    proposal["finalMarkPrice"] = decimal_text(current_mark)
    positions = active_symbol_positions(base_url, symbol, api_key, api_secret)
    if positions:
        raise RuntimeError("Existing symbol position detected; closePosition protection would not be order-exclusive")
    algo_orders = active_symbol_algo_orders(base_url, symbol, api_key, api_secret)
    if algo_orders:
        raise RuntimeError("Existing symbol algo order detected; clean up stale protection orders before preparing a fresh order")
    proposal["status"] = "EXECUTING"
    proposal["executionStartedAt"] = iso_from_ms(now_ms())
    atomic_json(proposal_path(args.token), proposal)
    dual = account_position_mode(base_url, api_key, api_secret)
    position_side = entry_position_side(str(proposal["side"]), dual)
    leverage_result = set_leverage(base_url, symbol, int(proposal["leverage"]), api_key, api_secret)
    margin_result = set_margin_type(base_url, symbol, str(proposal["marginType"]), api_key, api_secret)
    prefix = "cns" + args.token[:12]
    try:
        entry = place_market(base_url, symbol, entry_order_side(str(proposal["side"])), position_side, str(proposal["quantity"]), prefix + "e", api_key, api_secret)
    except urllib.error.HTTPError as error:
        proposal["status"] = "ENTRY_REJECTED_OR_UNKNOWN"
        proposal["error"] = "HTTP %s" % error.code
        atomic_json(proposal_path(args.token), proposal)
        raise RuntimeError("Entry request failed or has unknown execution state; do not retry automatically, inspect Binance orders")
    executed_quantity = str(entry.get("executedQty") or entry.get("origQty") or proposal["quantity"])
    protection_side = exit_order_side(str(proposal["side"]))
    take_profits: List[Dict[str, object]] = []
    stop_loss: Optional[Dict[str, object]] = None
    tp_errors: List[str] = []
    sl_error = ""
    levels = proposal.get("takeProfitLevels")
    if not isinstance(levels, list):
        levels = [{"level": "1", "triggerPrice": str(proposal["takeProfit"]), "quantity": executed_quantity}]
    planned_take_profit_quantity = sum(
        (as_decimal(level.get("quantity", "0")) for level in levels if isinstance(level, dict)),
        Decimal("0"),
    )
    if planned_take_profit_quantity > as_decimal(executed_quantity):
        tp_errors.append("planned take-profit quantity exceeds actual executed entry quantity")
        levels = []
    for index, level in enumerate(levels, start=1):
        if not isinstance(level, dict):
            tp_errors.append("invalid take-profit level")
            continue
        try:
            take_profits.append(place_protection(base_url, symbol, protection_side, position_side, "TAKE_PROFIT_MARKET", str(level["triggerPrice"]), prefix + "t" + str(index), api_key, api_secret, str(level["quantity"])))
        except (RuntimeError, urllib.error.HTTPError, urllib.error.URLError) as error:
            tp_errors.append(str(error))
    try:
        stop_loss = place_protection(base_url, symbol, protection_side, position_side, "STOP_MARKET", str(proposal["stopLoss"]), prefix + "s", api_key, api_secret)
    except (RuntimeError, urllib.error.HTTPError, urllib.error.URLError) as error:
        sl_error = str(error)
    emergency_close: Optional[Dict[str, object]] = None
    if stop_loss is None:
        for take_profit in take_profits:
            try:
                cancel_algo(base_url, take_profit.get("algoId"), api_key, api_secret)
            except (RuntimeError, urllib.error.HTTPError, urllib.error.URLError):
                pass
        try:
            emergency_close = place_market(base_url, symbol, protection_side, position_side, executed_quantity, prefix + "x", api_key, api_secret, reduce_only=True)
            proposal["status"] = "EMERGENCY_CLOSED_STOP_FAILED"
        except (RuntimeError, urllib.error.HTTPError, urllib.error.URLError):
            proposal["status"] = "CRITICAL_UNPROTECTED_POSITION"
    elif not take_profits:
        proposal["status"] = "OPEN_WITH_STOP_ONLY"
    elif tp_errors:
        proposal["status"] = "OPEN_WITH_STOP_PARTIAL_TP"
    else:
        proposal["status"] = "OPEN_WITH_MULTI_TP_SL"
    proposal["completedAt"] = iso_from_ms(now_ms())
    proposal["positionSide"] = position_side
    proposal["leverageResult"] = leverage_result
    proposal["marginTypeResult"] = margin_result
    proposal["entryOrder"] = entry
    proposal["takeProfitOrders"] = take_profits
    proposal["stopLossOrder"] = stop_loss
    proposal["takeProfitErrors"] = tp_errors
    proposal["stopLossError"] = sl_error
    proposal["emergencyCloseOrder"] = emergency_close
    atomic_json(proposal_path(args.token), proposal)
    print(json.dumps(proposal, ensure_ascii=False, indent=2))
    if proposal["status"] != "OPEN_WITH_MULTI_TP_SL":
        raise RuntimeError("Order workflow did not complete normally; inspect returned status and Binance immediately")


def positive_decimal(value: str) -> Decimal:
    result = as_decimal(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return result


def take_profit_level(value: str) -> Tuple[Decimal, Decimal]:
    parts = value.split(":", 1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("use PRICE:QUANTITY")
    return positive_decimal(parts[0]), positive_decimal(parts[1])


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--plan-id", required=True)
    prepare_parser.add_argument("--symbol", required=True)
    prepare_parser.add_argument("--side", choices=("LONG", "SHORT"), required=True)
    prepare_parser.add_argument("--quantity", type=positive_decimal, required=True)
    prepare_parser.add_argument("--leverage", type=int, choices=range(1, 11), required=True)
    prepare_parser.add_argument("--margin-type", choices=("CROSS", "ISOLATED"), required=True)
    prepare_parser.add_argument("--stop-loss", type=positive_decimal, required=True)
    take_profit_group = prepare_parser.add_mutually_exclusive_group(required=True)
    take_profit_group.add_argument("--take-profit", type=positive_decimal)
    take_profit_group.add_argument("--take-profit-level", type=take_profit_level, action="append")
    prepare_parser.add_argument("--ttl-seconds", type=int, default=600, choices=range(60, 901))
    execute_parser = commands.add_parser("execute")
    execute_parser.add_argument("--token", required=True)
    execute_parser.add_argument("--confirm", required=True)
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(args)
        else:
            execute(args)
        return 0
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8", errors="replace")
        print(json.dumps({"error": "Binance HTTP %s" % error.code, "detail": payload[:500]}, ensure_ascii=False), file=sys.stderr)
        return 1
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
