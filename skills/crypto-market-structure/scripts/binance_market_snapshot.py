#!/usr/bin/env python3
"""Fetch read-only Binance USD-M crypto or TradFi futures market data and indicators."""

import argparse
import datetime as dt
import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


BASE_URLS = (
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
)
INTERVALS = ("1d", "4h", "1h", "15m")
EXCLUDED_BASE_ASSETS = {"USDC", "FDUSD", "TUSD", "USDP", "DAI", "USDE", "BUSD"}
DEFAULT_CONTRACT_TYPES = {"PERPETUAL"}
TRADFI_CONTRACT_TYPES = {"TRADIFI_PERPETUAL"}
ALL_SUPPORTED_CONTRACT_TYPES = DEFAULT_CONTRACT_TYPES | TRADFI_CONTRACT_TYPES


def utc_iso(timestamp_ms: Optional[int] = None) -> str:
    value = dt.datetime.now(dt.timezone.utc) if timestamp_ms is None else dt.datetime.fromtimestamp(timestamp_ms / 1000, dt.timezone.utc)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def request_json(path: str, params: Optional[Dict[str, str]] = None) -> Tuple[object, str]:
    query = urllib.parse.urlencode(params or {})
    suffix = "%s?%s" % (path, query) if query else path
    failures: List[str] = []
    for base_url in BASE_URLS:
        request = urllib.request.Request(
            base_url + suffix,
            headers={"User-Agent": "crypto-news-selector/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8")), base_url
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as error:
            failures.append("%s: %s" % (base_url, error))
    raise RuntimeError("Binance public endpoints unavailable: %s" % "; ".join(failures))


def as_float(value: object) -> float:
    number = float(str(value))
    if not math.isfinite(number):
        raise ValueError("non-finite numeric value")
    return number


def ema(values: Sequence[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    result = sum(values[:period]) / period
    multiplier = 2.0 / (period + 1)
    for value in values[period:]:
        result = value * multiplier + result * (1 - multiplier)
    return result


def rsi(values: Sequence[float], period: int = 14) -> Optional[float]:
    if len(values) <= period:
        return None
    changes = [values[index] - values[index - 1] for index in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period
    for index in range(period, len(changes)):
        average_gain = (average_gain * (period - 1) + gains[index]) / period
        average_loss = (average_loss * (period - 1) + losses[index]) / period
    if average_loss == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + average_gain / average_loss)


def atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> Optional[float]:
    if len(closes) <= period:
        return None
    true_ranges: List[float] = []
    for index in range(1, len(closes)):
        true_ranges.append(max(highs[index] - lows[index], abs(highs[index] - closes[index - 1]), abs(lows[index] - closes[index - 1])))
    result = sum(true_ranges[:period]) / period
    for value in true_ranges[period:]:
        result = (result * (period - 1) + value) / period
    return result


def rounded(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(value, 8)


def selected_contract_types(include_tradfi: bool, tradfi_only: bool) -> set[str]:
    if tradfi_only:
        return set(TRADFI_CONTRACT_TYPES)
    if include_tradfi:
        return set(ALL_SUPPORTED_CONTRACT_TYPES)
    return set(DEFAULT_CONTRACT_TYPES)


def load_universe(include_tradfi: bool = False, tradfi_only: bool = False) -> Tuple[Dict[str, Dict[str, object]], str]:
    raw, source = request_json("/fapi/v1/exchangeInfo")
    if not isinstance(raw, dict) or not isinstance(raw.get("symbols"), list):
        raise RuntimeError("Unexpected exchangeInfo response")
    universe: Dict[str, Dict[str, object]] = {}
    allowed_contract_types = selected_contract_types(include_tradfi, tradfi_only)
    for item in raw["symbols"]:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", ""))
        base_asset = str(item.get("baseAsset", ""))
        if (
            item.get("status") == "TRADING"
            and item.get("contractType") in allowed_contract_types
            and item.get("quoteAsset") == "USDT"
            and base_asset not in EXCLUDED_BASE_ASSETS
        ):
            universe[symbol] = item
    return universe, source


def scan(limit: int, min_quote_volume: float, include_tradfi: bool, tradfi_only: bool) -> Dict[str, object]:
    universe, exchange_source = load_universe(include_tradfi, tradfi_only)
    raw, ticker_source = request_json("/fapi/v1/ticker/24hr")
    if not isinstance(raw, list):
        raise RuntimeError("Unexpected ticker response")
    candidates: List[Dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict) or str(item.get("symbol", "")) not in universe:
            continue
        quote_volume = as_float(item.get("quoteVolume", 0))
        if quote_volume < min_quote_volume:
            continue
        candidates.append({
            "symbol": str(item["symbol"]),
            "contract_type": universe[str(item["symbol"])].get("contractType"),
            "underlying_type": universe[str(item["symbol"])].get("underlyingType"),
            "underlying_sub_type": universe[str(item["symbol"])].get("underlyingSubType"),
            "last_price": as_float(item.get("lastPrice", 0)),
            "change_24h_percent": as_float(item.get("priceChangePercent", 0)),
            "high_24h": as_float(item.get("highPrice", 0)),
            "low_24h": as_float(item.get("lowPrice", 0)),
            "quote_volume_24h_usdt": quote_volume,
            "trade_count_24h": int(item.get("count", 0)),
        })
    candidates.sort(key=lambda item: float(item["quote_volume_24h_usdt"]), reverse=True)
    liquid = candidates[: max(limit * 4, limit)]
    liquid.sort(key=lambda item: abs(float(item["change_24h_percent"])), reverse=True)
    return {
        "generated_at": utc_iso(),
        "market": "Binance USD-M perpetual futures",
        "sources": [exchange_source, ticker_source],
        "filters": {
            "min_quote_volume_24h_usdt": min_quote_volume,
            "stable_assets_excluded": sorted(EXCLUDED_BASE_ASSETS),
            "contract_types": sorted(selected_contract_types(include_tradfi, tradfi_only)),
        },
        "candidates": liquid[:limit],
    }


def normalize_symbols(raw_symbols: str, universe: Dict[str, Dict[str, object]]) -> List[str]:
    symbols = []
    for raw_symbol in raw_symbols.split(","):
        symbol = raw_symbol.strip().upper()
        if symbol and symbol not in symbols:
            if symbol not in universe:
                raise ValueError("Not a trading Binance USD-M symbol in selected contract types: %s" % symbol)
            symbols.append(symbol)
    if not symbols:
        raise ValueError("At least one symbol is required")
    return symbols


def summarize_klines(raw: object, allow_partial: bool = False) -> Dict[str, object]:
    if not isinstance(raw, list):
        raise RuntimeError("Unexpected kline response")
    if len(raw) < 55 and not allow_partial:
        raise RuntimeError("Insufficient kline history")
    valid_rows = [row for row in raw if isinstance(row, list) and len(row) >= 11]
    current_time_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    rows = [row for row in valid_rows if int(row[6]) < current_time_ms]
    if len(rows) < 55 and not allow_partial:
        raise RuntimeError("Insufficient closed kline history")
    if len(rows) < 2:
        raise RuntimeError("Insufficient closed kline history")
    closes = [as_float(row[4]) for row in rows]
    highs = [as_float(row[2]) for row in rows]
    lows = [as_float(row[3]) for row in rows]
    volumes = [as_float(row[7]) for row in rows]
    previous_volumes = volumes[-21:-1]
    recent_volume_average = sum(previous_volumes) / len(previous_volumes) if previous_volumes else 0
    return {
        "history_status": "partial" if len(rows) < 55 else "complete",
        "closed_kline_count": len(rows),
        "last_closed_candle_close_time": utc_iso(int(rows[-1][6])),
        "last_price": closes[-1],
        "ema20": rounded(ema(closes, 20)),
        "ema50": rounded(ema(closes, 50)),
        "rsi14": rounded(rsi(closes, 14)),
        "atr14": rounded(atr(highs, lows, closes, 14)),
        "recent_high_20": max(highs[-20:]),
        "recent_low_20": min(lows[-20:]),
        "quote_volume_ratio_vs_previous_20": rounded(volumes[-1] / recent_volume_average if recent_volume_average else None),
    }


def analyze(raw_symbols: str, kline_limit: int, include_tradfi: bool, tradfi_only: bool, allow_partial: bool) -> Dict[str, object]:
    universe, exchange_source = load_universe(include_tradfi, tradfi_only)
    symbols = normalize_symbols(raw_symbols, universe)
    results: List[Dict[str, object]] = []
    sources = {exchange_source}
    for symbol in symbols:
        timeframes: Dict[str, object] = {}
        for interval in INTERVALS:
            raw, source = request_json("/fapi/v1/klines", {"symbol": symbol, "interval": interval, "limit": str(kline_limit)})
            sources.add(source)
            try:
                timeframes[interval] = summarize_klines(raw, allow_partial)
            except RuntimeError as error:
                if not allow_partial:
                    raise
                timeframes[interval] = {"history_status": "unavailable", "error": str(error)}
        results.append({
            "symbol": symbol,
            "contract_type": universe[symbol].get("contractType"),
            "underlying_type": universe[symbol].get("underlyingType"),
            "underlying_sub_type": universe[symbol].get("underlyingSubType"),
            "price_precision": universe[symbol].get("pricePrecision"),
            "timeframes": timeframes,
        })
    return {
        "generated_at": utc_iso(),
        "market": "Binance USD-M perpetual futures",
        "sources": sorted(sources),
        "symbols": results,
    }


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan_parser = subparsers.add_parser("scan", help="scan liquid, actively moving perpetual contracts")
    scan_parser.add_argument("--limit", type=positive_int, default=30)
    scan_parser.add_argument("--min-quote-volume", type=float, default=10_000_000)
    scan_parser.add_argument("--include-tradfi", action="store_true", help="include Binance TradFi perpetual contracts such as tokenized stock futures")
    scan_parser.add_argument("--tradfi-only", action="store_true", help="only include Binance TradFi perpetual contracts")
    analyze_parser = subparsers.add_parser("analyze", help="fetch multi-timeframe indicators for symbols")
    analyze_parser.add_argument("--symbols", required=True)
    analyze_parser.add_argument("--kline-limit", type=positive_int, default=120)
    analyze_parser.add_argument("--include-tradfi", action="store_true", help="allow Binance TradFi perpetual contracts such as tokenized stock futures")
    analyze_parser.add_argument("--tradfi-only", action="store_true", help="only allow Binance TradFi perpetual contracts")
    analyze_parser.add_argument("--allow-partial", action="store_true", help="return partial indicators when newly listed symbols have short kline history")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            result = scan(args.limit, args.min_quote_volume, args.include_tradfi, args.tradfi_only)
        else:
            result = analyze(args.symbols, args.kline_limit, args.include_tradfi, args.tradfi_only, args.allow_partial)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, ValueError, urllib.error.URLError) as error:
        print(json.dumps({"error": str(error), "generated_at": utc_iso()}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
