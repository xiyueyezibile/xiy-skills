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
from typing import Dict, List, Tuple


CONFIG = Path.home() / ".crypto" / "config.json"
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


def signed_get(path: str, api_key: str, api_secret: str) -> object:
    params = {"timestamp": str(int(time.time() * 1000)), "recvWindow": "5000"}
    query = urllib.parse.urlencode(params)
    signature = hmac.new(api_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
    request = urllib.request.Request(BASE_URL + path + "?" + query + "&signature=" + signature, headers={"X-MBX-APIKEY": api_key, "User-Agent": "crypto-news-selector/1.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


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
        output = {"source": BASE_URL, "fetchedAt": int(time.time() * 1000), "account": {"totalWalletBalance": account.get("totalWalletBalance"), "availableBalance": account.get("availableBalance"), "totalUnrealizedProfit": account.get("totalUnrealizedProfit"), "totalMaintMargin": account.get("totalMaintMargin")}, "activePositions": active_positions}
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
