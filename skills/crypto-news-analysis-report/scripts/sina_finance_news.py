#!/usr/bin/env python3
"""Fetch public Sina Finance rolling news and filter by keywords.

This script uses only public Sina Finance endpoints. It does not read local
credentials, accounts, cookies, or private trading state.
"""

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List, Optional, Sequence


BASE_URL = "https://feed.mix.sina.com.cn/api/roll/get"
CATEGORY_LIDS = {
    "finance": "2515",
    "us_stock": "2516",
    "hk_stock": "2517",
    "stock": "2518",
    "industry": "2509",
}


def cst_iso(timestamp: Optional[object]) -> str:
    if timestamp in (None, ""):
        return ""
    try:
        value = int(str(timestamp))
    except ValueError:
        return str(timestamp)
    return dt.datetime.fromtimestamp(value, dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")


def request_json(params: Dict[str, str]) -> Dict[str, object]:
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.sina.com.cn/",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        value = json.loads(response.read().decode("utf-8", errors="replace"))
    if not isinstance(value, dict):
        raise RuntimeError("Unexpected Sina Finance response")
    return value


def normalize_queries(values: Sequence[str]) -> List[str]:
    queries: List[str] = []
    for raw in values:
        for part in raw.split(","):
            value = part.strip().lower()
            if value and value not in queries:
                queries.append(value)
    return queries


def matches(item: Dict[str, object], queries: Sequence[str]) -> bool:
    if not queries:
        return True
    haystack = " ".join(
        str(item.get(key, ""))
        for key in ("title", "url", "wapurl", "wapsummary", "media_name", "keywords")
    ).lower()
    return any(query in haystack for query in queries)


def normalize_item(item: Dict[str, object], category: str) -> Dict[str, object]:
    return {
        "source_name": "新浪财经",
        "category": category,
        "title": item.get("title", ""),
        "url": item.get("url") or item.get("wapurl") or "",
        "wapurl": item.get("wapurl") or "",
        "published_at_cst": cst_iso(item.get("ctime") or item.get("intime")),
        "updated_at_cst": cst_iso(item.get("mtime")),
        "docid": item.get("docid", ""),
    }


def fetch_category(category: str, page_size: int, max_pages: int, queries: Sequence[str]) -> List[Dict[str, object]]:
    lid = CATEGORY_LIDS[category]
    results: List[Dict[str, object]] = []
    for page in range(1, max_pages + 1):
        payload = request_json({"pageid": "153", "lid": lid, "num": str(page_size), "page": str(page)})
        result = payload.get("result")
        if not isinstance(result, dict):
            continue
        status = result.get("status")
        if isinstance(status, dict) and status.get("code") not in (0, "0"):
            continue
        data = result.get("data")
        if not isinstance(data, list) or not data:
            break
        for raw_item in data:
            if isinstance(raw_item, dict) and matches(raw_item, queries):
                results.append(normalize_item(raw_item, category))
    return results


def dedupe(items: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    seen = set()
    output: List[Dict[str, object]] = []
    for item in items:
        key = str(item.get("url") or item.get("docid") or item.get("title"))
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--query", action="append", default=[], help="Keyword filter; may repeat or use comma-separated values")
    result.add_argument("--category", action="append", choices=sorted(CATEGORY_LIDS), help="Sina Finance category; default searches all configured categories")
    result.add_argument("--limit", type=int, default=30)
    result.add_argument("--page-size", type=int, default=30)
    result.add_argument("--max-pages", type=int, default=2)
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parser().parse_args(argv)
    categories = args.category or list(CATEGORY_LIDS)
    queries = normalize_queries(args.query)
    fetched_at = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")
    items: List[Dict[str, object]] = []
    errors: List[Dict[str, str]] = []
    for category in categories:
        try:
            items.extend(fetch_category(category, args.page_size, args.max_pages, queries))
        except (OSError, RuntimeError, json.JSONDecodeError, urllib.error.URLError) as error:
            errors.append({"category": category, "error": str(error)})
    output = {
        "source": "新浪财经",
        "endpoint": BASE_URL,
        "fetched_at_cst": fetched_at,
        "queries": queries,
        "categories": categories,
        "items": dedupe(items)[: args.limit],
        "errors": errors,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["items"] or not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
