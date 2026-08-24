#!/usr/bin/env python3
"""Persist and classify public rumor leads for crypto news selection."""

import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence


SOURCE_KINDS = {
    "regulator",
    "exchange",
    "project",
    "company",
    "mainstream_media",
    "industry_media",
    "social_verified",
    "social_unverified",
    "anonymous",
}
OFFICIAL_KINDS = {"regulator", "exchange", "project", "company"}
RELIABLE_KINDS = OFFICIAL_KINDS | {"mainstream_media", "industry_media"}
STANCES = {"supports", "denies", "mentions"}
STATUSES = {"lead", "corroborated", "confirmed", "disputed", "rejected", "expired"}


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_time(value: str) -> dt.datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = dt.datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone: %s" % value)
    return parsed.astimezone(dt.timezone.utc)


def find_workspace_root(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / "AGENTS.md").is_file():
            return candidate
    return current


def watch_file() -> Path:
    override = os.environ.get("CRYPTO_RUMOR_WATCH_FILE")
    if override:
        return Path(override).expanduser().resolve()
    return find_workspace_root() / ".crypto" / "rumor-watch" / "watchlist.json"


def secure_directory(path: Path) -> None:
    created = not path.exists()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if created or path.name == "rumor-watch":
        os.chmod(path, 0o700)


def atomic_write(path: Path, value: Dict[str, object]) -> None:
    secure_directory(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".%s." % path.name, dir=str(path.parent))
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def empty_state() -> Dict[str, object]:
    return {"schema_version": 1, "updated_at": iso(utc_now()), "items": []}


def load_state(path: Path) -> Dict[str, object]:
    if not path.is_file():
        return empty_state()
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        raise ValueError("invalid rumor watch state: %s" % path)
    return value


def require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % field)
    return value.strip()


def optional_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def rumor_id(symbol: str, claim: str) -> str:
    normalized = "%s|%s" % (symbol.upper(), " ".join(claim.lower().split()))
    return "R-%s" % hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def normalize_evidence(raw: object, retrieved_at: str) -> Dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError("each evidence item must be an object")
    source_kind = require_text(raw.get("source_kind"), "evidence.source_kind")
    stance = require_text(raw.get("stance"), "evidence.stance")
    if source_kind not in SOURCE_KINDS:
        raise ValueError("unsupported source_kind: %s" % source_kind)
    if stance not in STANCES:
        raise ValueError("unsupported stance: %s" % stance)
    url = require_text(raw.get("url"), "evidence.url")
    if not url.startswith(("https://", "http://")):
        raise ValueError("evidence.url must be HTTP(S)")
    published_at = require_text(raw.get("published_at"), "evidence.published_at")
    parse_time(published_at)
    return {
        "source_kind": source_kind,
        "source_name": require_text(raw.get("source_name"), "evidence.source_name"),
        "url": url,
        "published_at": published_at,
        "retrieved_at": optional_text(raw.get("retrieved_at")) or retrieved_at,
        "stance": stance,
        "excerpt": optional_text(raw.get("excerpt")),
    }


def classify(evidence: List[Dict[str, object]], expires_at: str, now: dt.datetime) -> Dict[str, object]:
    if expires_at and parse_time(expires_at) <= now:
        return {"status": "expired", "confidence": "low", "core_eligible": False}

    supporting = [item for item in evidence if item["stance"] == "supports"]
    denying = [item for item in evidence if item["stance"] == "denies"]
    official_support = any(item["source_kind"] in OFFICIAL_KINDS for item in supporting)
    official_denial = any(item["source_kind"] in OFFICIAL_KINDS for item in denying)
    reliable_sources = {
        (str(item["source_kind"]), str(item["source_name"]).strip().lower())
        for item in supporting
        if item["source_kind"] in RELIABLE_KINDS
    }

    if official_denial and official_support:
        return {"status": "disputed", "confidence": "low", "core_eligible": False}
    if official_denial:
        return {"status": "rejected", "confidence": "high", "core_eligible": False}
    if official_support:
        return {"status": "confirmed", "confidence": "high", "core_eligible": True}
    if len(reliable_sources) >= 2:
        return {"status": "corroborated", "confidence": "medium", "core_eligible": False}
    return {"status": "lead", "confidence": "low", "core_eligible": False}


def merge_evidence(existing: object, incoming: List[Dict[str, object]]) -> List[Dict[str, object]]:
    merged: List[Dict[str, object]] = []
    seen_urls = set()
    if isinstance(existing, list):
        for item in existing:
            if isinstance(item, dict) and isinstance(item.get("url"), str):
                merged.append(dict(item))
                seen_urls.add(str(item["url"]))
    for item in incoming:
        url = str(item["url"])
        if url not in seen_urls:
            merged.append(item)
            seen_urls.add(url)
    return merged


def upsert(path: Path, input_path: Path) -> Dict[str, object]:
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("input must be a JSON object")

    now = utc_now()
    retrieved_at = optional_text(raw.get("retrieved_at")) or iso(now)
    parse_time(retrieved_at)
    symbol = require_text(raw.get("symbol"), "symbol").upper()
    claim = require_text(raw.get("claim"), "claim")
    identifier = optional_text(raw.get("id")) or rumor_id(symbol, claim)
    raw_evidence = raw.get("evidence")
    if not isinstance(raw_evidence, list) or not raw_evidence:
        raise ValueError("evidence must be a non-empty array")
    incoming_evidence = [normalize_evidence(item, retrieved_at) for item in raw_evidence]

    state = load_state(path)
    items = state["items"]
    if not isinstance(items, list):
        raise ValueError("invalid state items")
    existing = next(
        (item for item in items if isinstance(item, dict) and item.get("id") == identifier),
        None,
    )
    existing_entry = existing if isinstance(existing, dict) else {}
    first_seen_at = retrieved_at
    existing_evidence: object = []
    if existing_entry:
        first_seen_at = optional_text(existing_entry.get("first_seen_at")) or retrieved_at
        existing_evidence = existing_entry.get("evidence", [])
        items.remove(existing_entry)

    evidence = merge_evidence(existing_evidence, incoming_evidence)
    expires_at = optional_text(raw.get("expires_at")) or optional_text(existing_entry.get("expires_at"))
    review_at = optional_text(raw.get("review_at")) or optional_text(existing_entry.get("review_at"))
    if expires_at:
        parse_time(expires_at)
    if review_at:
        parse_time(review_at)
    classification = classify(evidence, expires_at, now)
    entry: Dict[str, object] = {
        "id": identifier,
        "symbol": symbol,
        "claim": claim,
        "direction_hint": optional_text(raw.get("direction_hint")) or optional_text(existing_entry.get("direction_hint")) or "unclear",
        "first_seen_at": first_seen_at,
        "last_checked_at": retrieved_at,
        "event_time": optional_text(raw.get("event_time")) or optional_text(existing_entry.get("event_time")),
        "review_at": review_at,
        "expires_at": expires_at,
        "status": classification["status"],
        "confidence": classification["confidence"],
        "core_eligible": classification["core_eligible"],
        "price_trigger": optional_text(raw.get("price_trigger")) or optional_text(existing_entry.get("price_trigger")),
        "invalidation": optional_text(raw.get("invalidation")) or optional_text(existing_entry.get("invalidation")),
        "impact_path": optional_text(raw.get("impact_path")) or optional_text(existing_entry.get("impact_path")),
        "counter_case": optional_text(raw.get("counter_case")) or optional_text(existing_entry.get("counter_case")),
        "evidence": evidence,
    }
    items.append(entry)
    items.sort(key=lambda item: str(item.get("last_checked_at", "")) if isinstance(item, dict) else "", reverse=True)
    state["updated_at"] = iso(now)
    atomic_write(path, state)
    return entry


def expire(path: Path, at: dt.datetime) -> Dict[str, object]:
    state = load_state(path)
    items = state["items"]
    expired_count = 0
    if not isinstance(items, list):
        raise ValueError("invalid state items")
    for item in items:
        if not isinstance(item, dict):
            continue
        expires_at = optional_text(item.get("expires_at"))
        if expires_at and parse_time(expires_at) <= at and item.get("status") not in {"rejected", "expired"}:
            item["status"] = "expired"
            item["confidence"] = "low"
            item["core_eligible"] = False
            expired_count += 1
    state["updated_at"] = iso(at)
    atomic_write(path, state)
    return {"expired_count": expired_count, "at": iso(at)}


def filtered_state(path: Path, statuses: Sequence[str]) -> Dict[str, object]:
    state = load_state(path)
    if not statuses:
        return state
    invalid = set(statuses) - STATUSES
    if invalid:
        raise ValueError("unsupported status: %s" % ",".join(sorted(invalid)))
    items = state["items"]
    if not isinstance(items, list):
        raise ValueError("invalid state items")
    return {
        "schema_version": state.get("schema_version", 1),
        "updated_at": state.get("updated_at", ""),
        "items": [
            item
            for item in items
            if isinstance(item, dict) and item.get("status") in statuses
        ],
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--state-file", help="Override the default .crypto rumor watch file")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    upsert_parser = commands.add_parser("upsert")
    upsert_parser.add_argument("--input", required=True)
    list_parser = commands.add_parser("list")
    list_parser.add_argument("--status", action="append", default=[])
    expire_parser = commands.add_parser("expire")
    expire_parser.add_argument("--at", help="ISO-8601 timestamp; defaults to now")
    return root


def main() -> int:
    args = parser().parse_args()
    path = Path(args.state_file).expanduser().resolve() if args.state_file else watch_file()
    if args.command == "init":
        state = load_state(path)
        atomic_write(path, state)
        result: Dict[str, object] = {"state_file": str(path), "initialized": True}
    elif args.command == "upsert":
        result = {"state_file": str(path), "item": upsert(path, Path(args.input))}
    elif args.command == "expire":
        at = parse_time(args.at) if args.at else utc_now()
        result = {"state_file": str(path), **expire(path, at)}
    else:
        result = {"state_file": str(path), **filtered_state(path, args.status)}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
