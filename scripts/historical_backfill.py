#!/usr/bin/env python
"""Historical backfill collector for the Calories Research Monitor.

Runs one mechanistic node at a time. It is deliberately conservative:
- PubMed metadata/abstract discovery only;
- no medical advice;
- capped additions;
- all entries stay needs_human_review.

Usage:
  python scripts/historical_backfill.py --dry-run
  python scripts/historical_backfill.py --node ULTRA_PROCESSED --max-additions 3
  python scripts/historical_backfill.py
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path("C:/Users/Home/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe")
TODAY = datetime.now(timezone.utc).date().isoformat()
STATE_PATH = ROOT / "backfill" / "state.json"
INCOMING_DIR = ROOT / "incoming"
RUNS_DIR = ROOT / "runs"

CLAIMS = {
    "ULTRA_PROCESSED": ["CLAIM_UPF_PASSIVE_OVEREATING", "CLAIM_SAME_CALORIES_DIFFERENT_EVENT"],
    "FOOD_MATRIX": ["CLAIM_FIBER_MATRIX_ENERGY", "CLAIM_SAME_CALORIES_DIFFERENT_EVENT", "CLAIM_MEASUREMENT_LIMITS"],
    "PROTEIN_LEVERAGE": ["CLAIM_PROTEIN_SATIETY_THERMIC", "CLAIM_SAME_CALORIES_DIFFERENT_EVENT"],
    "EATING_RATE": ["CLAIM_FOOD_FORM_ALTERS_INTAKE", "CLAIM_UPF_PASSIVE_OVEREATING"],
    "GLYCEMIC_DYNAMICS": ["CLAIM_GLYCEMIC_VARIABILITY", "CLAIM_SAME_CALORIES_DIFFERENT_EVENT"],
    "EXERCISE_COMPENSATION": ["CLAIM_ADAPTIVE_EXPENDITURE", "CLAIM_COUNTERARGUMENT_ENERGY_BALANCE"],
    "LABELING_MEASUREMENT": ["CLAIM_MEASUREMENT_LIMITS", "CLAIM_CALORIE_USEFUL_INCOMPLETE"],
    "ENERGY_BALANCE": ["CLAIM_COUNTERARGUMENT_ENERGY_BALANCE", "CLAIM_CALORIE_USEFUL_INCOMPLETE"],
    "MICROBIOME": ["CLAIM_FIBER_MATRIX_ENERGY", "CLAIM_SAME_CALORIES_DIFFERENT_EVENT"],
    "SATIETY_SIGNALS": ["CLAIM_SAME_CALORIES_DIFFERENT_EVENT", "CLAIM_FOOD_FORM_ALTERS_INTAKE"],
    "REWARD_PALATABILITY": ["CLAIM_UPF_PASSIVE_OVEREATING", "CLAIM_FOOD_FORM_ALTERS_INTAKE"],
    "CIRCADIAN_TIMING": ["CLAIM_GLYCEMIC_VARIABILITY", "CLAIM_SAME_CALORIES_DIFFERENT_EVENT"],
    "INDIVIDUAL_VARIATION": ["CLAIM_GLYCEMIC_VARIABILITY", "CLAIM_CALORIE_USEFUL_INCOMPLETE"],
    "WEIGHT_REGULATION": ["CLAIM_ADAPTIVE_EXPENDITURE", "CLAIM_COUNTERARGUMENT_ENERGY_BALANCE"],
    "ENDOCRINE_ADIPOSE": ["CLAIM_ADAPTIVE_EXPENDITURE", "CLAIM_CALORIE_USEFUL_INCOMPLETE"],
    "THERMIC_EFFECT": ["CLAIM_PROTEIN_SATIETY_THERMIC", "CLAIM_SAME_CALORIES_DIFFERENT_EVENT"],
}

QUERY_SETS = {
    "ULTRA_PROCESSED": [
        '"ultra-processed foods" "ad libitum" "energy intake"',
        '"ultra-processed" "metabolic ward" "Hall"',
        '"NOVA" "ultra-processed foods" "review"',
    ],
    "FOOD_MATRIX": [
        '"food matrix" "metabolizable energy"',
        '"Atwater factors" "metabolizable energy"',
        'almonds "metabolizable energy" calories',
    ],
    "PROTEIN_LEVERAGE": [
        '"protein leverage" appetite humans',
        '"protein leverage hypothesis" obesity',
        'protein satiety "energy intake" review',
    ],
    "EATING_RATE": [
        '"eating rate" "energy intake"',
        '"oral processing" satiety "energy intake"',
        '"food texture" "eating rate" satiety',
    ],
    "GLYCEMIC_DYNAMICS": [
        '"personalized nutrition" "glycemic responses"',
        '"postprandial glucose" "interindividual variability"',
        '"continuous glucose monitoring" diet "glycemic response"',
    ],
    "EXERCISE_COMPENSATION": [
        '"constrained total energy expenditure"',
        '"exercise compensation" "energy expenditure" obesity',
        '"adaptive thermogenesis" "weight loss"',
    ],
    "LABELING_MEASUREMENT": [
        '"calorie labeling" accuracy restaurant',
        '"nutrition label" calorie accuracy',
        '"bomb calorimetry" "Atwater" food energy',
    ],
    "ENERGY_BALANCE": [
        'isocaloric diet trial weight loss energy balance',
        '"energy balance" obesity calories review',
        '"carbohydrate-insulin model" energy balance trial',
    ],
    "MICROBIOME": [
        'gut microbiota "energy harvest" obesity',
        'short-chain fatty acids fermentation energy balance',
        'dietary fiber microbiome satiety energy intake',
    ],
    "SATIETY_SIGNALS": [
        'GLP-1 PYY ghrelin satiety meal energy intake',
        'gastric emptying satiety energy intake',
        'appetite hormones diet composition energy intake',
    ],
    "REWARD_PALATABILITY": [
        'hyperpalatable foods energy intake',
        'food reward palatability energy intake obesity',
        'dopamine food reward eating behavior review',
    ],
    "CIRCADIAN_TIMING": [
        'late eating circadian metabolism glucose',
        'meal timing energy intake weight loss trial',
        'time restricted eating energy intake trial',
    ],
    "INDIVIDUAL_VARIATION": [
        'interindividual variability diet weight loss trial',
        'metabolic phenotype diet response nutrition',
        'personalized nutrition variability response diet',
    ],
    "WEIGHT_REGULATION": [
        'body weight regulation set point settling point review',
        'adaptive thermogenesis weight loss maintenance',
        'metabolic adaptation weight loss humans',
    ],
    "ENDOCRINE_ADIPOSE": [
        'leptin adipose feedback body weight regulation',
        'leptin resistance obesity energy balance review',
        'adipose endocrine appetite energy expenditure',
    ],
    "THERMIC_EFFECT": [
        'thermic effect of food protein carbohydrate fat',
        'diet induced thermogenesis protein energy expenditure',
        'protein thermogenesis satiety energy intake review',
    ],
}

HIGH_HINTS = ["randomized", "controlled", "metabolic ward", "trial", "systematic review", "meta-analysis", "review"]
COUNTER_HINTS = ["isocaloric", "no difference", "energy balance", "carbohydrate-insulin", "compensation", "adaptive"]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:70] or "untitled"


def get_json(url: str, timeout: int = 25) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "CaloriesResearchBackfill/1.0 (book research)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def get_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "CaloriesResearchBackfill/1.0 (book research)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def pubmed_ids(query: str, floor: str, retmax: int) -> list[str]:
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax,
        "sort": "relevance",
        "mindate": floor,
        "maxdate": TODAY,
        "datetype": "pdat",
    })
    data = get_json(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}")
    return data.get("esearchresult", {}).get("idlist", [])


def evidence_level(text: str) -> str:
    low = text.lower()
    if "meta-analysis" in low or "meta analysis" in low:
        return "META_ANALYSIS"
    if "systematic review" in low:
        return "REVIEW_SYSTEMATIC"
    if "metabolic ward" in low:
        return "RCT_HUMAN_METABOLIC_WARD"
    if "randomized" in low or "trial" in low:
        return "RCT_HUMAN_FREE_LIVING"
    if "cohort" in low:
        return "PROSPECTIVE_COHORT"
    if "review" in low:
        return "REVIEW_NARRATIVE"
    return "MECHANISTIC_HUMAN"


def parse_articles(xml: str, node: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml)
    out = []
    for article in root.findall(".//PubmedArticle"):
        pmid = norm(article.findtext(".//PMID") or "")
        title = norm("".join(article.findtext(".//ArticleTitle") or ""))
        if not pmid or not title:
            continue
        abstract = norm(" ".join(t.text or "" for t in article.findall(".//AbstractText")))
        journal = norm(article.findtext(".//Journal/Title") or "")
        year = article.findtext(".//PubDate/Year") or article.findtext(".//ArticleDate/Year") or ""
        month = article.findtext(".//PubDate/Month") or article.findtext(".//ArticleDate/Month") or "01"
        day = article.findtext(".//PubDate/Day") or article.findtext(".//ArticleDate/Day") or "01"
        month_map = {m: str(i).zfill(2) for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
        month = month_map.get(month[:3], month.zfill(2) if month.isdigit() else "01")
        day = day.zfill(2) if day.isdigit() else "01"
        date_published = f"{year}-{month}-{day}" if year else ""
        authors = []
        for a in article.findall(".//Author")[:8]:
            name = norm(f"{a.findtext('ForeName') or ''} {a.findtext('LastName') or ''}")
            if name:
                authors.append(name)
        doi = ""
        for aid in article.findall(".//ArticleId"):
            if aid.attrib.get("IdType") == "doi" and aid.text:
                doi = norm(aid.text)
        text = f"{title} {abstract} {journal}"
        ev = evidence_level(text)
        low = text.lower()
        relation = "complicates" if any(h in low for h in COUNTER_HINTS) else "strengthens"
        book_use = "counterargument" if relation == "complicates" else ("stat" if ev in {"META_ANALYSIS", "REVIEW_SYSTEMATIC"} else "mechanism")
        relevance = "HIGH" if any(h in low for h in HIGH_HINTS) else "MEDIUM"
        out.append({
            "id": f"{TODAY.replace('-', '')}-historical-{slugify(title)}",
            "date_found": TODAY,
            "date_published": date_published,
            "title": title,
            "source_type": "scholar",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "doi": doi,
            "pmid": pmid,
            "pmcid": "",
            "journal": journal,
            "authors": authors,
            "year": year,
            "citation_apa": "",
            "citation_vancouver": "",
            "study_type": ev,
            "evidence_level": ev,
            "population": "",
            "sample_size": "",
            "duration": "",
            "intervention_or_exposure": "",
            "primary_outcome": "",
            "cascade_nodes": [node],
            "claim_tags": CLAIMS.get(node, ["CLAIM_CALORIE_USEFUL_INCOMPLETE"]),
            "claim_relation": relation,
            "relevance": relevance,
            "summary": (abstract[:700] + "…") if len(abstract) > 700 else abstract,
            "key_findings": [],
            "mechanism": "",
            "limitations": [
                "Historical backfill from PubMed metadata/abstract; verify full text before manuscript use.",
                "Automatically tagged; mechanism and chapter use need human review."
            ],
            "funding": "",
            "conflicts": "",
            "quote_or_key_sentence": "",
            "book_use": book_use,
            "chapter_candidates": [],
            "overclaim_risk": "MEDIUM" if ev in {"RCT_HUMAN_METABOLIC_WARD", "RCT_HUMAN_FREE_LIVING", "REVIEW_SYSTEMATIC", "META_ANALYSIS"} else "HIGH",
            "medical_caution": "Do not present as medical advice; verify study design, population, and outcomes before use.",
            "generalizability": "Unknown until human review of full paper.",
            "status": "needs_human_review",
            "added_by_run": TODAY,
            "discovery_lane": "historical_backfill",
        })
    return out


def collect_node(node: str, floor: str, max_additions: int) -> tuple[list[dict[str, Any]], list[str]]:
    ids: list[str] = []
    log: list[str] = []
    for query in QUERY_SETS[node]:
        try:
            found = pubmed_ids(query, floor, retmax=8)
            log.append(f"query={query!r} ids={found}")
            ids.extend(found)
            time.sleep(0.34)
        except Exception as exc:
            log.append(f"query failed {query!r}: {exc}")
    ids = list(dict.fromkeys(ids))[:24]
    if not ids:
        return [], log
    xml = get_text("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}))
    entries = parse_articles(xml, node)
    rank = {"RCT_HUMAN_METABOLIC_WARD": 0, "RCT_HUMAN_FREE_LIVING": 1, "REVIEW_SYSTEMATIC": 2, "META_ANALYSIS": 3, "MECHANISTIC_HUMAN": 4, "REVIEW_NARRATIVE": 5}
    entries.sort(key=lambda e: (rank.get(e.get("evidence_level", ""), 9), e.get("year") or "9999"))
    return entries[:max_additions], log


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(ROOT), text=True, capture_output=True, timeout=240)


def selected_node(state: dict[str, Any], forced: str | None) -> tuple[str, int]:
    nodes = state.get("nodes") or list(QUERY_SETS)
    if forced:
        if forced not in QUERY_SETS:
            raise SystemExit(f"Unknown node: {forced}")
        return forced, nodes.index(forced) if forced in nodes else -1
    idx = int(state.get("current_index", 0)) % len(nodes)
    return nodes[idx], idx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--node")
    parser.add_argument("--max-additions", type=int)
    parser.add_argument("--date-floor")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    state = load_json(STATE_PATH, {"current_index": 0, "nodes": list(QUERY_SETS), "history": [], "max_additions_per_run": 3, "date_floor": "1990-01-01"})
    node, idx = selected_node(state, args.node)
    max_additions = args.max_additions or int(state.get("max_additions_per_run", 3))
    floor = args.date_floor or state.get("date_floor", "1990-01-01")
    entries, query_log = collect_node(node, floor, max_additions)

    incoming = INCOMING_DIR / f"{TODAY}-historical-{node}-candidates.json"
    write_json(incoming, entries)
    summary = {
        "date": TODAY,
        "node": node,
        "date_floor": floor,
        "candidate_count": len(entries),
        "candidate_titles": [e["title"] for e in entries],
        "incoming": str(incoming),
        "dry_run": bool(args.dry_run),
        "query_log": query_log,
    }

    if args.dry_run:
        write_json(RUNS_DIR / f"{TODAY}-historical-{node}-dry-run-summary.json", summary)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    ingest = run_cmd([str(PYTHON), "scripts/ingest_entries.py", str(incoming)])
    summary["ingest_returncode"] = ingest.returncode
    summary["ingest_stdout"] = ingest.stdout[-4000:]
    summary["ingest_stderr"] = ingest.stderr[-4000:]
    if ingest.returncode != 0:
        write_json(RUNS_DIR / f"{TODAY}-historical-{node}-summary.json", summary)
        print(json.dumps(summary, indent=2, ensure_ascii=False), file=sys.stderr)
        return ingest.returncode

    deploy = run_cmd([str(PYTHON), "scripts/deploy_website.py"])
    summary["deploy_returncode"] = deploy.returncode
    summary["deploy_stdout"] = deploy.stdout[-4000:]
    summary["deploy_stderr"] = deploy.stderr[-4000:]
    if deploy.returncode != 0:
        write_json(RUNS_DIR / f"{TODAY}-historical-{node}-summary.json", summary)
        print(json.dumps(summary, indent=2, ensure_ascii=False), file=sys.stderr)
        return deploy.returncode

    if not args.node and idx >= 0:
        state["current_index"] = (idx + 1) % len(state.get("nodes", []))
    state.setdefault("history", []).append({"date": TODAY, "node": node, "candidate_count": len(entries), "incoming": str(incoming)})
    state["history"] = state["history"][-100:]
    write_json(STATE_PATH, state)
    summary["state_next_index"] = state.get("current_index")
    write_json(RUNS_DIR / f"{TODAY}-historical-{node}-summary.json", summary)

    if entries:
        print("Historical backfill added candidates for " + node + ":\n" + "\n".join(f"- {e['title']}" for e in entries) + "\nhttps://aoh1578.github.io/calories-research-monitor/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
