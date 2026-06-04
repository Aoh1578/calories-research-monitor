#!/usr/bin/env python
"""Ingest candidate research entries into the Calories Research Monitor.

Usage:
  python scripts/ingest_entries.py incoming/2026-06-04-candidates.json

The input may be either a JSON array of entries or an object with an `entries` array.
This script owns deterministic integrity work: schema normalization, dedupe,
backup, run logs, and copying canonical data to docs/data.json.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "data.json"
SEEN_PATH = ROOT / "data" / "seen.json"
DOCS_DATA_PATH = ROOT / "docs" / "data.json"
BACKUPS_DIR = ROOT / "backups"
RUNS_DIR = ROOT / "runs"

SOURCE_TYPES = {"scholar", "web", "social"}
RELEVANCE = {"HIGH", "MEDIUM"}
CLAIM_RELATIONS = {"strengthens", "weakens", "complicates", "background"}
BOOK_USES = {"scene", "mechanism", "stat", "counterargument", "caution", "background"}
OVERCLAIM = {"LOW", "MEDIUM", "HIGH"}
EVIDENCE_LEVELS = {
    "RCT_HUMAN_METABOLIC_WARD",
    "RCT_HUMAN_FREE_LIVING",
    "CONTROLLED_FEEDING_TRIAL",
    "PROSPECTIVE_COHORT",
    "CROSS_SECTIONAL",
    "MECHANISTIC_HUMAN",
    "ANIMAL_MODEL",
    "CELL_MODEL",
    "REVIEW_SYSTEMATIC",
    "REVIEW_NARRATIVE",
    "META_ANALYSIS",
    "EDITORIAL_COMMENTARY",
    "PREPRINT",
    "PUBLIC_DATASET",
    "SOCIAL_POINTER",
    "WEB_NEWS_POINTER",
}

DEFAULT_ENTRY: dict[str, Any] = {
    "id": "",
    "date_found": "",
    "date_published": "",
    "title": "",
    "source_type": "web",
    "url": "",
    "doi": "",
    "pmid": "",
    "pmcid": "",
    "journal": "",
    "authors": [],
    "year": "",
    "citation_apa": "",
    "citation_vancouver": "",
    "study_type": "",
    "evidence_level": "",
    "population": "",
    "sample_size": "",
    "duration": "",
    "intervention_or_exposure": "",
    "primary_outcome": "",
    "cascade_nodes": [],
    "claim_tags": [],
    "claim_relation": "background",
    "relevance": "MEDIUM",
    "summary": "",
    "key_findings": [],
    "mechanism": "",
    "limitations": [],
    "funding": "",
    "conflicts": "",
    "quote_or_key_sentence": "",
    "book_use": "background",
    "chapter_candidates": [],
    "overclaim_risk": "HIGH",
    "medical_caution": "",
    "generalizability": "",
    "status": "needs_human_review",
    "added_by_run": "",
}

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "mc_cid", "mc_eid"
}


def today() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_doi(raw: str) -> str:
    value = (raw or "").strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi:\s*", "", value)
    return value.strip()


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in TRACKING_PARAMS]
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") if parts.path != "/" else parts.path
    return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(query), ""))


def normalize_title(raw: str) -> str:
    raw = (raw or "").lower()
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def slugify(text: str, max_len: int = 48) -> str:
    text = normalize_title(text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:max_len].strip("-") or "untitled"


def ensure_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def clean_entry(raw: dict[str, Any], today_str: str, data: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    notes: list[str] = []
    entry = dict(DEFAULT_ENTRY)
    entry.update(raw or {})

    entry["title"] = str(entry.get("title") or "").strip()
    if not entry["title"]:
        return None, ["missing title"]

    entry["source_type"] = str(entry.get("source_type") or "web").lower()
    if entry["source_type"] not in SOURCE_TYPES:
        notes.append(f"source_type normalized from {entry['source_type']} to web")
        entry["source_type"] = "web"

    entry["relevance"] = str(entry.get("relevance") or "MEDIUM").upper()
    if entry["relevance"] not in RELEVANCE:
        return None, [f"excluded invalid or LOW relevance: {entry['relevance']}"]

    entry["doi"] = normalize_doi(str(entry.get("doi") or ""))
    entry["url"] = normalize_url(str(entry.get("url") or ""))
    entry["pmid"] = str(entry.get("pmid") or "").strip()
    entry["pmcid"] = str(entry.get("pmcid") or "").strip()
    entry["authors"] = [str(x).strip() for x in ensure_list(entry.get("authors")) if str(x).strip()]
    entry["cascade_nodes"] = [str(x).strip() for x in ensure_list(entry.get("cascade_nodes")) if str(x).strip()]
    entry["claim_tags"] = [str(x).strip() for x in ensure_list(entry.get("claim_tags")) if str(x).strip()]
    entry["key_findings"] = [str(x).strip() for x in ensure_list(entry.get("key_findings")) if str(x).strip()]
    entry["limitations"] = [str(x).strip() for x in ensure_list(entry.get("limitations")) if str(x).strip()]
    entry["chapter_candidates"] = [str(x).strip() for x in ensure_list(entry.get("chapter_candidates")) if str(x).strip()]

    known_nodes = {n["id"] for n in data.get("nodes", [])}
    unknown_nodes = [n for n in entry["cascade_nodes"] if n not in known_nodes]
    if unknown_nodes:
        notes.append(f"unknown node tags preserved: {', '.join(unknown_nodes)}")

    known_claims = {c["id"] for c in data.get("claims", [])}
    unknown_claims = [c for c in entry["claim_tags"] if c not in known_claims]
    if unknown_claims:
        notes.append(f"unknown claim tags preserved: {', '.join(unknown_claims)}")

    entry["claim_relation"] = str(entry.get("claim_relation") or "background").lower()
    if entry["claim_relation"] not in CLAIM_RELATIONS:
        notes.append("invalid claim_relation normalized to background")
        entry["claim_relation"] = "background"

    entry["book_use"] = str(entry.get("book_use") or "background").lower()
    if entry["book_use"] not in BOOK_USES:
        notes.append("invalid book_use normalized to background")
        entry["book_use"] = "background"

    entry["overclaim_risk"] = str(entry.get("overclaim_risk") or "HIGH").upper()
    if entry["overclaim_risk"] not in OVERCLAIM:
        entry["overclaim_risk"] = "HIGH"

    entry["evidence_level"] = str(entry.get("evidence_level") or "").upper()
    if entry["source_type"] == "social" and not entry["evidence_level"]:
        entry["evidence_level"] = "SOCIAL_POINTER"
    if entry["source_type"] == "web" and not entry["evidence_level"]:
        entry["evidence_level"] = "WEB_NEWS_POINTER"
    if entry["evidence_level"] and entry["evidence_level"] not in EVIDENCE_LEVELS:
        notes.append(f"nonstandard evidence_level preserved: {entry['evidence_level']}")

    entry["date_found"] = str(entry.get("date_found") or today_str)
    entry["added_by_run"] = str(entry.get("added_by_run") or today_str)
    if not entry.get("id"):
        entry["id"] = f"{today_str.replace('-', '')}-{slugify(entry['title'])}"
    entry["status"] = str(entry.get("status") or "needs_human_review")

    # Leave citation fields blank when incomplete. No fabrication.
    return entry, notes


def is_duplicate(entry: dict[str, Any], data: dict[str, Any], seen: dict[str, Any]) -> tuple[bool, str]:
    doi = normalize_doi(entry.get("doi", ""))
    pmid = str(entry.get("pmid") or "").strip()
    url = normalize_url(entry.get("url", ""))
    title = normalize_title(entry.get("title", ""))

    seen_dois = {normalize_doi(x) for x in seen.get("doi", []) if x}
    seen_pmids = {str(x).strip() for x in seen.get("pmid", []) if x}
    seen_urls = {normalize_url(x) for x in seen.get("url", []) if x}
    seen_titles = [normalize_title(x) for x in seen.get("titles", []) if x]

    for existing in data.get("entries", []):
        if doi and doi == normalize_doi(existing.get("doi", "")):
            return True, "duplicate doi in data"
        if pmid and pmid == str(existing.get("pmid") or "").strip():
            return True, "duplicate pmid in data"
        if url and url == normalize_url(existing.get("url", "")):
            return True, "duplicate url in data"
        ex_title = normalize_title(existing.get("title", ""))
        if title and ex_title and SequenceMatcher(None, title, ex_title).ratio() >= 0.90:
            return True, "fuzzy duplicate title in data"

    if doi and doi in seen_dois:
        return True, "duplicate doi in seen"
    if pmid and pmid in seen_pmids:
        return True, "duplicate pmid in seen"
    if url and url in seen_urls:
        return True, "duplicate url in seen"
    for st in seen_titles:
        if title and st and SequenceMatcher(None, title, st).ratio() >= 0.90:
            return True, "fuzzy duplicate title in seen"
    return False, ""


def update_seen(seen: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    for key in ["doi", "pmid", "url", "titles"]:
        seen.setdefault(key, [])
    for e in entries:
        if e.get("doi") and e["doi"] not in seen["doi"]:
            seen["doi"].append(e["doi"])
        if e.get("pmid") and e["pmid"] not in seen["pmid"]:
            seen["pmid"].append(e["pmid"])
        if e.get("url") and e["url"] not in seen["url"]:
            seen["url"].append(e["url"])
        if e.get("title") and e["title"] not in seen["titles"]:
            seen["titles"].append(e["title"])
    seen["updated_at"] = now_iso()
    return seen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidates", type=Path, help="JSON array or object with entries[]")
    args = parser.parse_args()

    today_str = today()
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    data = load_json(DATA_PATH, {"entries": [], "nodes": [], "claims": []})
    seen = load_json(SEEN_PATH, {"doi": [], "pmid": [], "url": [], "titles": []})
    payload = load_json(args.candidates, [])
    candidates = payload.get("entries", []) if isinstance(payload, dict) else payload
    if not isinstance(candidates, list):
        raise SystemExit("Candidate input must be a JSON array or object with entries[]")

    added: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    notes_by_title: dict[str, list[str]] = {}

    for raw in candidates:
        if not isinstance(raw, dict):
            rejected.append({"title": "<non-object>", "reason": "candidate is not an object"})
            continue
        entry, notes = clean_entry(raw, today_str, data)
        title = raw.get("title", "<missing title>")
        if notes:
            notes_by_title[str(title)] = notes
        if entry is None:
            rejected.append({"title": str(title), "reason": "; ".join(notes)})
            continue
        dup, reason = is_duplicate(entry, data, seen)
        if dup:
            rejected.append({"title": entry["title"], "reason": reason})
            continue
        added.append(entry)

    # Prepend new entries, latest first by date_found then publication date.
    data.setdefault("entries", [])
    data["entries"] = added + data["entries"]
    data["last_updated"] = today_str
    data["generated_at"] = now_iso()
    data.setdefault("project", "Calories Research Monitor")
    seen = update_seen(seen, added)

    write_json(DATA_PATH, data)
    write_json(SEEN_PATH, seen)
    write_json(DOCS_DATA_PATH, data)

    backup_path = BACKUPS_DIR / f"{today_str}-new_entries.json"
    write_json(backup_path, {"date": today_str, "entries": added})

    summary = {
        "date": today_str,
        "candidate_count": len(candidates),
        "added_count": len(added),
        "high_added_count": sum(1 for e in added if e.get("relevance") == "HIGH"),
        "medium_added_count": sum(1 for e in added if e.get("relevance") == "MEDIUM"),
        "rejected_count": len(rejected),
        "added_titles": [e["title"] for e in added],
        "rejected": rejected,
        "backup_path": str(backup_path),
        "data_path": str(DATA_PATH),
        "docs_data_path": str(DOCS_DATA_PATH),
        "notes": notes_by_title,
    }
    summary_path = RUNS_DIR / f"{today_str}-summary.json"
    write_json(summary_path, summary)

    log_lines = [
        f"Calories Research Monitor run {today_str}",
        f"Candidates: {len(candidates)}",
        f"Added: {len(added)}",
        f"Rejected: {len(rejected)}",
        f"High added: {summary['high_added_count']}",
        f"Backup: {backup_path}",
        "",
    ]
    for e in added:
        log_lines.append(f"ADDED [{e['relevance']}] {e['title']} | {e.get('url','')}")
    for r in rejected:
        log_lines.append(f"REJECTED {r['title']} | {r['reason']}")
    (RUNS_DIR / f"{today_str}.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
