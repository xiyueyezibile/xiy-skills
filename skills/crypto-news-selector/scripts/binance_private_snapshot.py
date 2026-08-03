#!/usr/bin/env python3
"""Fetch Binance USD-M account and position data through signed read-only GET requests."""

import hashlib
import hmac
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


CONFIG = Path.home() / ".crypto" / "config.json"
LEDGER = Path.home() / ".crypto" / "trades" / "ledger.jsonl"
BASE_URL = "https://fapi.binance.com"


def credentials() -> Tuple[str, str]:
    if not CONFIG.is_file():
        raise RuntimeError("Missing ~/.crypto/config.json; run crypto_memory.py configure-binance")
    mode = CONFIG.stat().st_mode & 0o777
    if mode & 0o077:
        raise RuntimeError("Unsafe config permissions; run chmod 600 ~/.crypto/config.json")
    value = json.loads(CONFIG.read_text(encoding="utf-8"))
    binance = value.get("binance") if isinstance(value, dict) else None
    if not isinstance(binance, dict) or not binance.get("apiKey") or not binance.get("apiSecret"):
        raise RuntimeError("Binance credentials are not configured")
    return str(binance["apiKey"]), str(binance["apiSecret"])


def signed_get(path: str, api_key: str, api_secret: str, extra_params: Optional[Dict[str, str]] = None) -> object:
    params = dict(extra_params or {})
    params.update({"timestamp": str(int(time.time() * 1000)), "recvWindow": "5000"})
    query = urllib.parse.urlencode(params)
    signature = hmac.new(api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
    request = urllib.request.Request(BASE_URL + path + "?" + query + "&signature=" + signature, headers={"X-MBX-APIKEY": api_key, "User-Agent": "crypto-news-selector/1.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def ledger_open_trades() -> List[Dict[str, object]]:
    if not LEDGER.is_file():
        return []
    events: List[Dict[str, object]] = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            events.append(value)
    closed_ids = {str(item.get("tradeId")) for item in events if item.get("type") == "CLOSE"}
    result: List[Dict[str, object]] = []
    for item in events:
        trade_id = str(item.get("tradeId"))
        if item.get("type") != "OPEN" or trade_id in closed_ids:
            continue
        remaining_quantity = float(item.get("quantity", 0)) + sum(float(event.get("quantityDelta", 0)) for event in events if event.get("type") == "ADJUST" and str(event.get("tradeId")) == trade_id)
        if remaining_quantity <= 0:
            continue
        open_item = dict(item)
        open_item["originalQuantity"] = item.get("quantity")
        open_item["quantity"] = remaining_quantity
        result.append(open_item)
    return result


def position_side(amount: float) -> str:
    return "LONG" if amount > 0 else "SHORT"


def reconciliation(active_positions: List[Dict[str, object]], open_trades: List[Dict[str, object]]) -> Dict[str, object]:
    active_by_key: Dict[Tuple[str, str], float] = {}
    for item in active_positions:
        amount = float(item.get("positionAmt", 0))
        key = (str(item.get("symbol", "")), position_side(amount))
        active_by_key[key] = active_by_key.get(key, 0.0) + abs(amount)

    logged_by_key: Dict[Tuple[str, str], float] = {}
    trade_ids_by_key: Dict[Tuple[str, str], List[str]] = {}
    for item in open_trades:
        key = (str(item.get("symbol", "")), str(item.get("side", "")))
        logged_by_key[key] = logged_by_key.get(key, 0.0) + float(item.get("quantity", 0))
        trade_ids_by_key.setdefault(key, []).append(str(item.get("tradeId", "")))

    discrepancies: List[Dict[str, object]] = []
    for key in sorted(set(active_by_key) | set(logged_by_key)):
        active_quantity = active_by_key.get(key, 0.0)
        logged_quantity = logged_by_key.get(key, 0.0)
        tolerance = max(1e-8, active_quantity * 1e-8, logged_quantity * 1e-8)
        if abs(active_quantity - logged_quantity) <= tolerance:
            continue
        if logged_quantity == 0:
            kind = "UNTRACKED_ACTIVE_POSITION"
        elif active_quantity == 0:
            kind = "LOGGED_POSITION_NOT_ACTIVE"
        else:
            kind = "QUANTITY_CHANGED"
        discrepancies.append({"kind": kind, "symbol": key[0], "side": key[1], "activeQuantity": active_quantity, "loggedOpenQuantity": logged_quantity, "tradeIds": trade_ids_by_key.get(key, [])})
    return {"status": "ALIGNED" if not discrepancies else "REVIEW_REQUIRED", "discrepancies": discrepancies}


def recent_user_trades(symbols: Set[str], api_key: str, api_secret: str) -> Dict[str, List[Dict[str, object]]]:
    result: Dict[str, List[Dict[str, object]]] = {}
    for symbol in sorted(symbols):
        response = signed_get("/fapi/v1/userTrades", api_key, api_secret, {"symbol": symbol, "limit": "100"})
        if not isinstance(response, list):
            raise RuntimeError("Unexpected Binance userTrades response for %s" % symbol)
        result[symbol] = [{"time": item.get("time"), "side": item.get("side"), "positionSide": item.get("positionSide"), "price": item.get("price"), "quantity": item.get("qty"), "realizedPnl": item.get("realizedPnl"), "commission": item.get("commission"), "commissionAsset": item.get("commissionAsset"), "maker": item.get("maker")} for item in response if isinstance(item, dict)]
    return result


def main() -> int:
    try:
        api_key, api_secret = credentials()
        account = signed_get("/fapi/v2/account", api_key, api_secret)
        positions = signed_get("/fapi/v2/positionRisk", api_key, api_secret)
        if not isinstance(account, dict) or not isinstance(positions, list):
            raise RuntimeError("Unexpected Binance private response")
        active_positions: List[Dict[str, object]] = []
        for item in positions:
            if isinstance(item, dict) and float(item.get("positionAmt", 0)) != 0:
                active_positions.append({"symbol": item.get("symbol"), "positionAmt": item.get("positionAmt"), "entryPrice": item.get("entryPrice"), "markPrice": item.get("markPrice"), "unRealizedProfit": item.get("unRealizedProfit"), "liquidationPrice": item.get("liquidationPrice"), "leverage": item.get("leverage"), "marginType": item.get("marginType")})
        open_trades = ledger_open_trades()
        audit = reconciliation(active_positions, open_trades)
        discrepancy_symbols = {str(item.get("symbol")) for item in audit["discrepancies"] if isinstance(item, dict) and item.get("symbol")}
        output = {"source": BASE_URL, "fetchedAt": int(time.time() * 1000), "account": {"totalWalletBalance": account.get("totalWalletBalance"), "availableBalance": account.get("availableBalance"), "totalUnrealizedProfit": account.get("totalUnrealizedProfit"), "totalMaintMargin": account.get("totalMaintMargin")}, "activePositions": active_positions, "ledgerOpenTrades": open_trades, "lifecycleAudit": audit, "recentUserTradesForDiscrepancies": recent_user_trades(discrepancy_symbols, api_key, api_secret)}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except urllib.error.HTTPError as error:
        print(json.dumps({"error": "Binance private API returned HTTP %s" % error.code}, ensure_ascii=False), file=sys.stderr)
        return 1
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
