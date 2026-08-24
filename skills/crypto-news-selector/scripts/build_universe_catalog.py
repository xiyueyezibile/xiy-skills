#!/usr/bin/env python3
"""Build the complete Binance USD-M contract catalog with news-source routing."""

import argparse
import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


BASE_URLS = (
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
)
SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_OUTPUT = SKILL_ROOT / "references" / "binance-usdm-universe.json"
DEFAULT_MARKDOWN_OUTPUT = SKILL_ROOT / "references" / "binance-usdm-universe.md"

MARKET_LABELS = {
    "CRYPTO": "加密币",
    "US_EQUITY": "美股/美股 ETF/ADR",
    "KR_EQUITY": "韩股",
    "HK_EQUITY": "港股",
    "CN_EQUITY": "A 股",
    "COMMODITY": "商品",
    "PREMARKET": "Pre-IPO",
    "OTHER_TRADFI": "其他 TradFi",
}

SOURCE_CATALOG = {
    "binance_contract": {
        "name": "Binance 合约公告",
        "level": "L0",
        "url": "https://www.binance.com/en/support/announcement/list/93",
        "purpose": "合约上线、下架、结算、规则和交易参数",
    },
    "crypto_official": {
        "name": "项目官网与官方治理入口",
        "level": "L0",
        "url": "https://www.coingecko.com/en/search?query={base_asset}",
        "purpose": "从资产资料页定位官网、文档、官方社媒和治理入口；最终引用原始页面",
    },
    "crypto_calendar": {
        "name": "CoinMarketCal",
        "level": "L2",
        "url": "https://coinmarketcal.com/en/?form%5Bkeyword%5D={base_asset}",
        "purpose": "发现升级、上线、治理和产品排期线索，需回到官方来源确认",
    },
    "token_unlocks": {
        "name": "Tokenomist",
        "level": "L2",
        "url": "https://tokenomist.ai/",
        "purpose": "发现解锁线索，具体日期与数量需用官方归属规则或链上数据消歧",
    },
    "sec_edgar": {
        "name": "SEC EDGAR",
        "level": "L0",
        "url": "https://www.sec.gov/edgar/search/#/q={base_asset}",
        "purpose": "美股公司监管文件、8-K、10-Q、10-K 和发行文件",
    },
    "nasdaq_news": {
        "name": "Nasdaq 公司新闻",
        "level": "L1",
        "url": "https://www.nasdaq.com/market-activity/stocks/{base_asset_lower}/news-headlines",
        "purpose": "美股公司新闻、财报和市场报道补充",
    },
    "sina_us": {
        "name": "新浪财经美股",
        "level": "L1",
        "url": "https://finance.sina.com.cn/stock/usstock/",
        "purpose": "中文美股滚动消息，需与公司 IR 或 SEC 原文交叉验证",
    },
    "dart_kr": {
        "name": "韩国 DART",
        "level": "L0",
        "url": "https://englishdart.fss.or.kr/",
        "purpose": "韩股公司法定披露",
    },
    "krx_kind": {
        "name": "KRX KIND",
        "level": "L0",
        "url": "https://global.krx.co.kr/",
        "purpose": "韩股交易所公告、上市与市场数据",
    },
    "naver_finance": {
        "name": "Naver Finance",
        "level": "L1",
        "url": "https://finance.naver.com/item/main.naver?code={exchange_code}",
        "purpose": "韩股行情、公告聚合与本地新闻入口",
    },
    "hkex_news": {
        "name": "HKEXnews",
        "level": "L0",
        "url": "https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=en",
        "purpose": "港股法定公告、财报与公司行动",
    },
    "sina_hk": {
        "name": "新浪财经港股",
        "level": "L1",
        "url": "https://finance.sina.com.cn/stock/hkstock/",
        "purpose": "中文港股滚动消息，需回到 HKEX 或公司公告确认",
    },
    "cninfo": {
        "name": "巨潮资讯",
        "level": "L0",
        "url": "https://www.cninfo.com.cn/new/index",
        "purpose": "A 股法定公告与定期报告",
    },
    "sse": {
        "name": "上海证券交易所",
        "level": "L0",
        "url": "https://www.sse.com.cn/disclosure/listedinfo/announcement/",
        "purpose": "沪市公司公告与监管信息",
    },
    "szse": {
        "name": "深圳证券交易所",
        "level": "L0",
        "url": "https://www.szse.cn/disclosure/listed/notice/index.html",
        "purpose": "深市公司公告与监管信息",
    },
    "sina_cn": {
        "name": "新浪财经 A 股",
        "level": "L1",
        "url": "https://finance.sina.com.cn/stock/",
        "purpose": "中文 A 股滚动消息，需回到交易所或公司公告确认",
    },
    "cme": {
        "name": "CME Group",
        "level": "L0",
        "url": "https://www.cmegroup.com/markets.html",
        "purpose": "贵金属、能源等期货合约与市场公告",
    },
    "ice": {
        "name": "ICE",
        "level": "L0",
        "url": "https://www.ice.com/products",
        "purpose": "布伦特原油等商品合约与市场公告",
    },
    "eia": {
        "name": "U.S. EIA",
        "level": "L0",
        "url": "https://www.eia.gov/todayinenergy/",
        "purpose": "原油、天然气库存和能源供需数据",
    },
    "company_newsroom": {
        "name": "公司官网/IR 检索",
        "level": "L0",
        "url": "https://www.google.com/search?q={base_asset}+official+investor+relations",
        "purpose": "定位底层公司官方公告、财报日历和投资者关系页面",
    },
    "reuters": {
        "name": "Reuters 检索",
        "level": "L1",
        "url": "https://www.reuters.com/site-search/?query={base_asset}",
        "purpose": "跨市场主流媒体交叉验证",
    },
}

KR_EXCHANGE_CODES = {
    "SKHYNIX": "000660",
    "SAMSUNG": "005930",
    "HYUNDAI": "005380",
    "SAMSUNGEM": "009150",
    "HANMI": "042700",
    "LGELECTRONICS": "066570",
    "NAVER": "035420",
    "KODEX200": "069500",
}


def utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def request_json(path: str) -> Tuple[object, str]:
    failures: List[str] = []
    for base_url in BASE_URLS:
        request = urllib.request.Request(
            base_url + path,
            headers={"User-Agent": "crypto-news-selector/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8")), base_url
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as error:
            failures.append("%s: %s" % (base_url, error))
    raise RuntimeError("Binance public endpoints unavailable: %s" % "; ".join(failures))


def classify_market(contract_type: str, underlying_type: str) -> str:
    if contract_type != "TRADIFI_PERPETUAL":
        return "CRYPTO"
    if underlying_type == "EQUITY":
        return "US_EQUITY"
    if underlying_type in {"KR_EQUITY", "HK_EQUITY", "CN_EQUITY", "COMMODITY", "PREMARKET"}:
        return underlying_type
    return "OTHER_TRADFI"


def source_ids_for_market(market_type: str) -> List[str]:
    source_ids = {
        "CRYPTO": ["crypto_official", "binance_contract", "crypto_calendar", "token_unlocks"],
        "US_EQUITY": ["company_newsroom", "sec_edgar", "nasdaq_news", "sina_us", "reuters", "binance_contract"],
        "KR_EQUITY": ["company_newsroom", "dart_kr", "krx_kind", "naver_finance", "reuters", "binance_contract"],
        "HK_EQUITY": ["company_newsroom", "hkex_news", "sina_hk", "reuters", "binance_contract"],
        "CN_EQUITY": ["company_newsroom", "cninfo", "sse", "szse", "sina_cn", "binance_contract"],
        "COMMODITY": ["cme", "ice", "eia", "reuters", "binance_contract"],
        "PREMARKET": ["company_newsroom", "sec_edgar", "reuters", "binance_contract"],
        "OTHER_TRADFI": ["company_newsroom", "reuters", "binance_contract"],
    }
    return source_ids[market_type]


def render_url(template: str, base_asset: str, exchange_code: str) -> str:
    values = {
        "base_asset": urllib.parse.quote(base_asset),
        "base_asset_lower": urllib.parse.quote(base_asset.lower()),
        "exchange_code": urllib.parse.quote(exchange_code),
    }
    return template.format(**values)


def build_catalog() -> Dict[str, object]:
    exchange_raw, exchange_source = request_json("/fapi/v1/exchangeInfo")
    ticker_raw, ticker_source = request_json("/fapi/v1/ticker/24hr")
    if not isinstance(exchange_raw, dict) or not isinstance(exchange_raw.get("symbols"), list):
        raise RuntimeError("Unexpected exchangeInfo response")
    if not isinstance(ticker_raw, list):
        raise RuntimeError("Unexpected ticker response")

    tickers: Dict[str, Dict[str, object]] = {
        str(item.get("symbol")): item
        for item in ticker_raw
        if isinstance(item, dict) and item.get("symbol")
    }
    contracts: List[Dict[str, object]] = []
    counts: Dict[str, int] = {}
    market_counts: Dict[str, int] = {}

    for item in exchange_raw["symbols"]:
        if not isinstance(item, dict):
            continue
        if item.get("status") != "TRADING" or item.get("quoteAsset") != "USDT":
            continue
        symbol = str(item.get("symbol", ""))
        base_asset = str(item.get("baseAsset", ""))
        contract_type = str(item.get("contractType", ""))
        underlying_type = str(item.get("underlyingType", ""))
        market_type = classify_market(contract_type, underlying_type)
        ticker = tickers.get(symbol, {})
        exchange_code = KR_EXCHANGE_CODES.get(base_asset, "")
        source_ids = source_ids_for_market(market_type)
        sources = [
            {
                "id": source_id,
                "name": SOURCE_CATALOG[source_id]["name"],
                "level": SOURCE_CATALOG[source_id]["level"],
                "url": render_url(str(SOURCE_CATALOG[source_id]["url"]), base_asset, exchange_code),
            }
            for source_id in source_ids
            if source_id != "naver_finance" or exchange_code
        ]
        contracts.append({
            "symbol": symbol,
            "base_asset": base_asset,
            "quote_asset": "USDT",
            "contract_type": contract_type,
            "underlying_type": underlying_type,
            "underlying_sub_type": item.get("underlyingSubType") or [],
            "market_type": market_type,
            "market_label_cn": MARKET_LABELS[market_type],
            "exchange_code": exchange_code or None,
            "last_price": float(str(ticker.get("lastPrice", 0))),
            "change_24h_percent": float(str(ticker.get("priceChangePercent", 0))),
            "quote_volume_24h_usdt": float(str(ticker.get("quoteVolume", 0))),
            "news_sources": sources,
        })
        counts[contract_type] = counts.get(contract_type, 0) + 1
        market_counts[market_type] = market_counts.get(market_type, 0) + 1

    contracts.sort(key=lambda row: (str(row["market_type"]), str(row["symbol"])))
    return {
        "generated_at": utc_iso(),
        "market": "Binance USD-M Futures",
        "scope": "All TRADING contracts quoted in USDT; no liquidity or asset exclusion applied.",
        "total": len(contracts),
        "contract_type_counts": dict(sorted(counts.items())),
        "market_type_counts": dict(sorted(market_counts.items())),
        "sources": [exchange_source, ticker_source],
        "source_catalog": SOURCE_CATALOG,
        "contracts": contracts,
    }


def markdown_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(catalog: Dict[str, object]) -> str:
    lines = [
        "# Binance USD-M 全量可交易合约清单",
        "",
        "> 此文件由 `scripts/build_universe_catalog.py` 生成。每次全市场选币前必须刷新；不要手工维护数量或把 `scan --limit` 当作全量底池。",
        "",
        "- 生成时间（UTC）：`%s`" % catalog["generated_at"],
        "- 可交易合约总数：`%s`" % catalog["total"],
        "- 范围：%s" % catalog["scope"],
        "- 合约类型统计：`%s`" % json.dumps(catalog["contract_type_counts"], ensure_ascii=False, sort_keys=True),
        "- 市场类型统计：`%s`" % json.dumps(catalog["market_type_counts"], ensure_ascii=False, sort_keys=True),
        "",
        "## 消息源目录",
        "",
        "| ID | 渠道 | 等级 | 用途 | 网址 |",
        "| --- | --- | --- | --- | --- |",
    ]
    source_catalog = catalog["source_catalog"]
    if not isinstance(source_catalog, dict):
        raise RuntimeError("Invalid source catalog")
    for source_id, source in source_catalog.items():
        if not isinstance(source, dict):
            continue
        lines.append(
            "| `%s` | %s | %s | %s | %s |"
            % (
                markdown_escape(source_id),
                markdown_escape(source["name"]),
                markdown_escape(source["level"]),
                markdown_escape(source["purpose"]),
                markdown_escape(source["url"]),
            )
        )

    contracts = catalog["contracts"]
    if not isinstance(contracts, list):
        raise RuntimeError("Invalid contracts")
    for market_type, label in MARKET_LABELS.items():
        rows = [row for row in contracts if isinstance(row, dict) and row.get("market_type") == market_type]
        if not rows:
            continue
        lines.extend([
            "",
            "## %s（%d）" % (label, len(rows)),
            "",
            "| 合约 | 底层 | 合约类型 | underlyingType | 子类型 | 交易所代码 | 24h 成交额 USDT | 消息渠道 |",
            "| --- | --- | --- | --- | --- | --- | ---: | --- |",
        ])
        for row in rows:
            news_sources = row.get("news_sources")
            source_links: List[str] = []
            if isinstance(news_sources, list):
                for source in news_sources:
                    if isinstance(source, dict):
                        source_links.append("[%s](%s)" % (source["id"], source["url"]))
            sub_types = row.get("underlying_sub_type")
            lines.append(
                "| `%s` | `%s` | `%s` | `%s` | %s | %s | %.2f | %s |"
                % (
                    markdown_escape(row["symbol"]),
                    markdown_escape(row["base_asset"]),
                    markdown_escape(row["contract_type"]),
                    markdown_escape(row["underlying_type"]),
                    markdown_escape(", ".join(str(value) for value in sub_types) if isinstance(sub_types, list) else ""),
                    markdown_escape(row.get("exchange_code") or "-"),
                    float(row["quote_volume_24h_usdt"]),
                    "<br>".join(source_links),
                )
            )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        catalog = build_catalog()
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.markdown_output.write_text(render_markdown(catalog), encoding="utf-8")
        print(json.dumps({
            "status": "ok",
            "total": catalog["total"],
            "contract_type_counts": catalog["contract_type_counts"],
            "market_type_counts": catalog["market_type_counts"],
            "json_output": str(args.json_output.resolve()),
            "markdown_output": str(args.markdown_output.resolve()),
        }, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, ValueError, OSError) as error:
        print(json.dumps({"status": "error", "error": str(error), "generated_at": utc_iso()}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
