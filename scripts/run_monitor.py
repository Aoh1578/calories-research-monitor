#!/usr/bin/env python
"""Deterministic daily collector for Calories Research Monitor.

Designed for Hermes cron no_agent=True: stdout is the user notification.
- Prints nothing on successful empty/MEDIUM-only runs.
- Prints concise summary when HIGH entries are added.
- Prints explicit failure details on error via non-zero exit.

Sources used every run:
- Scholar: PubMed ESearch/EFetch.
- Web: Crossref works API.
- Social: public Bluesky search endpoint where reachable.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path("C:/Users/Home/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe")
TODAY = datetime.now(timezone.utc).date().isoformat()
LOOKBACK_DATE = (datetime.now(timezone.utc).date() - timedelta(days=180)).isoformat()
INCOMING = ROOT / "incoming" / f"{TODAY}-candidates.json"
RUN_LOG = ROOT / "runs" / f"{TODAY}-collector.log"
SUMMARY = ROOT / "runs" / f"{TODAY}-summary.json"

NODES = {
    "ULTRA_PROCESSED": ["ultra-processed", "ultraprocessed", "processed food", "nova"],
    "FOOD_MATRIX": ["food matrix", "food structure", "metabolizable energy", "atwater", "bioavailability"],
    "SATIETY_SIGNALS": ["satiety", "hunger", "ghrelin", "glp-1", "pyy", "gastric emptying"],
    "PROTEIN_LEVERAGE": ["protein leverage", "protein appetite", "protein satiety"],
    "THERMIC_EFFECT": ["thermic effect", "diet-induced thermogenesis", "thermogenesis"],
    "GLYCEMIC_DYNAMICS": ["glycemic", "glucose", "insulin", "postprandial"],
    "MICROBIOME": ["microbiome", "microbiota", "fermentation", "short-chain fatty acid"],
    "EATING_RATE": ["eating rate", "oral processing", "chewing", "texture"],
    "REWARD_PALATABILITY": ["palatability", "food reward", "hyperpalatable", "dopamine"],
    "CIRCADIAN_TIMING": ["meal timing", "circadian", "time-restricted", "late eating"],
    "INDIVIDUAL_VARIATION": ["personalized nutrition", "interindividual", "individual variability", "metabolic phenotype"],
    "LABELING_MEASUREMENT": ["calorie label", "nutrition label", "atwater", "bomb calorimetry"],
    "EXERCISE_COMPENSATION": ["exercise compensation", "constrained energy", "energy expenditure"],
    "WEIGHT_REGULATION": ["weight regulation", "set point", "settling point", "adaptive thermogenesis"],
    "ENDOCRINE_ADIPOSE": ["leptin", "adipose", "endocrine"],
    "ENERGY_BALANCE": ["energy balance", "energy expenditure", "energy intake", "calorie"],
}

CLAIMS = {
    "CLAIM_UPF_PASSIVE_OVEREATING": ["ultra-processed", "ad libitum", "energy intake", "passive over"],
    "CLAIM_SAME_CALORIES_DIFFERENT_EVENT": ["food matrix", "eating rate", "satiety", "postprandial", "protein", "fiber"],
    "CLAIM_FOOD_FORM_ALTERS_INTAKE": ["texture", "eating rate", "oral processing", "liquid", "solid", "satiety"],
    "CLAIM_PROTEIN_SATIETY_THERMIC": ["protein", "thermic", "satiety", "protein leverage"],
    "CLAIM_FIBER_MATRIX_ENERGY": ["fiber", "food matrix", "metabolizable energy", "microbiome"],
    "CLAIM_GLYCEMIC_VARIABILITY": ["glycemic", "glucose", "insulin", "personalized"],
    "CLAIM_ADAPTIVE_EXPENDITURE": ["adaptive thermogenesis", "constrained", "energy expenditure", "compensation"],
    "CLAIM_MEASUREMENT_LIMITS": ["atwater", "calorie label", "labeling", "metabolizable energy"],
    "CLAIM_COUNTERARGUMENT_ENERGY_BALANCE": ["energy balance", "isocaloric", "calorie restriction", "weight loss"],
    "CLAIM_CALORIE_USEFUL_INCOMPLETE": ["calorie", "energy intake", "metabolism"],
}

PUBMED_QUERIES = [
    # Keep queries narrow. Broad terms like protein/glucose/calorie flood PubMed with disease-management or animal-feed papers.
    '("ultra-processed food" OR "ultra processed food") AND ("energy intake" OR appetite OR "ad libitum" OR randomized)',
    '("food matrix" OR "metabolizable energy" OR Atwater) AND (calorie OR energy OR nutrition)',
    '("eating rate" OR "oral processing" OR "food texture") AND (satiety OR "energy intake")',
    '("diet-induced thermogenesis" OR "thermic effect of food") AND (meal OR diet OR calorie)',
    '("personalized nutrition" OR "glycemic response") AND (meal OR diet OR postprandial) AND variability',
    '("constrained energy expenditure" OR "adaptive thermogenesis" OR "exercise compensation") AND (diet OR obesity OR "energy balance")',
    '(isocaloric OR "energy balance") AND ("weight loss" OR obesity) AND (diet OR trial OR review)',
]

DIRECT_FOCUS_TERMS = [
    "ultra-processed", "ultra processed", "food matrix", "metabolizable energy", "atwater",
    "eating rate", "oral processing", "food texture", "satiety", "diet-induced thermogenesis",
    "thermic effect", "constrained energy expenditure", "adaptive thermogenesis", "exercise compensation",
    "personalized nutrition", "glycemic response", "isocaloric", "energy balance", "calorie label",
]

EXCLUDE_TERMS = [
    # Usually outside this book's mechanism scope unless explicitly tied to calorie metabolism in ordinary diets.
    "date palm leaves", "lamb", "ruminant", "cattle", "broiler", "piglet", "aquaculture", "single-cell protein",
    "insulin dosing", "type 1 diabetes management", "multiple sclerosis incidence", "cognitive impairment",
    "postoperative", "enteral nutrition", "general surgery", "protocol for", "pilot randomized controlled trial",
    "red pepper", "capsaicin", "bariatric surgery", "obesity medicines", "anti-obesity medication",
]

CROSSREF_QUERIES = [
    'ultra-processed food randomized energy intake nutrition',
    'food matrix metabolizable energy calorie Atwater nutrition',
    'eating rate texture satiety energy intake',
]

BSKY_QUERIES = [
    'ultra-processed food Kevin Hall',
    'constrained energy expenditure Pontzer',
    'personalized nutrition glycemic response',
]


def log(msg: str) -> None:
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {msg}\n")


def get_json(url: str, timeout: int = 20) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "CaloriesResearchMonitor/1.0 (book research)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def get_text(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "CaloriesResearchMonitor/1.0 (book research)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:70] or "untitled"


def classify(text: str) -> tuple[list[str], list[str], str, str, str]:
    low = text.lower()
    if any(term in low for term in EXCLUDE_TERMS):
        return [], [], "", "", ""
    if not any(term in low for term in DIRECT_FOCUS_TERMS):
        return [], [], "", "", ""
    nodes = [node for node, keys in NODES.items() if any(k in low for k in keys)]
    claims = [claim for claim, keys in CLAIMS.items() if any(k in low for k in keys)]
    if not nodes:
        nodes = ["ENERGY_BALANCE"] if "calorie" in low or "energy" in low else []
    if not claims and nodes:
        claims = ["CLAIM_CALORIE_USEFUL_INCOMPLETE"]

    high_terms = ["randomized", "controlled feeding", "metabolic ward", "trial", "systematic review", "meta-analysis", "isocaloric"]
    relevance = "HIGH" if nodes and any(t in low for t in high_terms) else "MEDIUM"
    if not nodes or not claims:
        relevance = "LOW"

    if "systematic review" in low:
        evidence = "REVIEW_SYSTEMATIC"
    elif "meta-analysis" in low or "meta analysis" in low:
        evidence = "META_ANALYSIS"
    elif "randomized" in low or "trial" in low:
        evidence = "RCT_HUMAN_FREE_LIVING"
    elif "cohort" in low:
        evidence = "PROSPECTIVE_COHORT"
    elif "review" in low:
        evidence = "REVIEW_NARRATIVE"
    else:
        evidence = "MECHANISTIC_HUMAN" if relevance != "LOW" else ""

    relation = "complicates" if any(t in low for t in ["isocaloric", "null", "no difference", "energy balance", "evidence against", "against person-specific"]) else "strengthens"
    book_use = "counterargument" if relation == "complicates" else "mechanism"
    return nodes, claims, relation, evidence, book_use if relevance != "LOW" else ""


def pubmed_ids(query: str, retmax: int = 4) -> list[str]:
    params = urllib.parse.urlencode({
        "db": "pubmed", "term": query, "retmode": "json", "retmax": retmax,
        "sort": "pub date", "mindate": LOOKBACK_DATE, "maxdate": TODAY, "datetype": "pdat",
    })
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}"
    data = get_json(url)
    return data.get("esearchresult", {}).get("idlist", [])


def parse_pubmed_article(article: ET.Element) -> dict[str, Any] | None:
    pmid = norm("".join(article.findtext(".//PMID") or ""))
    title = norm("".join(article.findtext(".//ArticleTitle") or ""))
    if not pmid or not title:
        return None
    abstract = norm(" ".join(t.text or "" for t in article.findall(".//AbstractText")))
    journal = norm(article.findtext(".//Journal/Title") or "")
    year = article.findtext(".//PubDate/Year") or article.findtext(".//ArticleDate/Year") or ""
    month = article.findtext(".//PubDate/Month") or article.findtext(".//ArticleDate/Month") or "01"
    day = article.findtext(".//PubDate/Day") or article.findtext(".//ArticleDate/Day") or "01"
    month_map = {m: str(i).zfill(2) for i, m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], 1)}
    month = month_map.get(month[:3], month.zfill(2) if month.isdigit() else "01")
    day = day.zfill(2) if day.isdigit() else "01"
    date_published = f"{year}-{month}-{day}" if year else ""
    if date_published and date_published > TODAY:
        return None
    authors = []
    for a in article.findall(".//Author")[:6]:
        last = a.findtext("LastName") or ""
        fore = a.findtext("ForeName") or ""
        name = norm(f"{fore} {last}")
        if name:
            authors.append(name)
    doi = ""
    for aid in article.findall(".//ArticleId"):
        if aid.attrib.get("IdType") == "doi" and aid.text:
            doi = norm(aid.text)
    # PubMed occasionally carries stale/cross-linked DOI metadata. If DOI embeds an old year
    # that conflicts with a new publication year, leave it blank for human review.
    embedded_years = [int(y) for y in re.findall(r"(?:19|20)\d{2}", doi)]
    if year.isdigit() and embedded_years and max(embedded_years) < int(year) - 3:
        doi = ""
    text = f"{title} {abstract} {journal}"
    nodes, claims, relation, evidence, book_use = classify(text)
    relevance = "HIGH" if evidence in {"RCT_HUMAN_FREE_LIVING", "REVIEW_SYSTEMATIC", "META_ANALYSIS"} and nodes else ("MEDIUM" if nodes else "LOW")
    if relevance == "LOW":
        return None
    return {
        "id": f"{TODAY.replace('-', '')}-{slugify(title)}",
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
        "study_type": evidence,
        "evidence_level": evidence,
        "population": "",
        "sample_size": "",
        "duration": "",
        "intervention_or_exposure": "",
        "primary_outcome": "",
        "cascade_nodes": nodes,
        "claim_tags": claims,
        "claim_relation": relation,
        "relevance": relevance,
        "summary": (abstract[:500] + "…") if len(abstract) > 500 else abstract,
        "key_findings": [],
        "mechanism": "",
        "limitations": ["Automatically collected from PubMed metadata/abstract; requires human review before manuscript use."],
        "funding": "",
        "conflicts": "",
        "quote_or_key_sentence": "",
        "book_use": book_use,
        "chapter_candidates": [],
        "overclaim_risk": "MEDIUM",
        "medical_caution": "Do not present as medical advice; verify full text and study design before use.",
        "generalizability": "Unknown until human review of full paper.",
        "status": "needs_human_review",
        "added_by_run": TODAY,
    }


def collect_pubmed() -> list[dict[str, Any]]:
    ids: list[str] = []
    for q in PUBMED_QUERIES:
        try:
            found = pubmed_ids(q)
            log(f"pubmed query={q!r} ids={found}")
            ids.extend(found)
            time.sleep(0.34)
        except Exception as e:
            log(f"pubmed query failed {q!r}: {e}")
    ids = list(dict.fromkeys(ids))[:20]
    if not ids:
        return []
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode({
        "db": "pubmed", "id": ",".join(ids), "retmode": "xml"
    })
    xml = get_text(url)
    root = ET.fromstring(xml)
    entries = []
    for article in root.findall(".//PubmedArticle"):
        parsed = parse_pubmed_article(article)
        if parsed:
            entries.append(parsed)
    return entries


def collect_crossref() -> list[dict[str, Any]]:
    # Discovery/log channel. Crossref metadata can be noisy, so only ingest if very direct and recent.
    out = []
    for q in CROSSREF_QUERIES:
        try:
            params = urllib.parse.urlencode({"query": q, "filter": f"from-pub-date:{LOOKBACK_DATE}", "sort": "published", "order": "desc", "rows": 3})
            data = get_json(f"https://api.crossref.org/works?{params}")
            items = data.get("message", {}).get("items", [])
            log(f"crossref query={q!r} count={len(items)}")
            for item in items:
                title = norm((item.get("title") or [""])[0])
                text = f"{title} {item.get('container-title', [''])[0] if item.get('container-title') else ''}"
                nodes, claims, relation, evidence, book_use = classify(text)
                if not nodes or not claims:
                    continue
                # Avoid flooding ledger from Crossref alone unless title is clearly load-bearing.
                if not any(term in title.lower() for term in ["ultra-processed", "food matrix", "eating rate", "glycemic", "energy expenditure"]):
                    continue
                doi = item.get("DOI", "")
                date_parts = ((item.get("published-print") or item.get("published-online") or item.get("created") or {}).get("date-parts") or [[]])[0]
                pubdate = "-".join(str(x).zfill(2) for x in date_parts[:3]) if date_parts else ""
                authors = [norm(f"{a.get('given','')} {a.get('family','')}") for a in (item.get("author") or [])[:6]]
                out.append({
                    "id": f"{TODAY.replace('-', '')}-{slugify(title)}", "date_found": TODAY, "date_published": pubdate,
                    "title": title, "source_type": "web", "url": item.get("URL", ""), "doi": doi, "pmid": "", "pmcid": "",
                    "journal": (item.get("container-title") or [""])[0], "authors": [a for a in authors if a], "year": str(date_parts[0]) if date_parts else "",
                    "citation_apa": "", "citation_vancouver": "", "study_type": evidence, "evidence_level": evidence,
                    "population": "", "sample_size": "", "duration": "", "intervention_or_exposure": "", "primary_outcome": "",
                    "cascade_nodes": nodes, "claim_tags": claims, "claim_relation": relation, "relevance": "MEDIUM",
                    "summary": "Crossref-discovered candidate; verify full paper before use.", "key_findings": [], "mechanism": "", "limitations": ["Metadata-only Crossref discovery."],
                    "funding": "", "conflicts": "", "quote_or_key_sentence": "", "book_use": book_use,
                    "chapter_candidates": [], "overclaim_risk": "MEDIUM", "medical_caution": "Not medical advice; verify primary source.",
                    "generalizability": "Unknown until human review.", "status": "needs_human_review", "added_by_run": TODAY,
                })
        except Exception as e:
            log(f"crossref query failed {q!r}: {e}")
    return out


def collect_bsky() -> list[dict[str, Any]]:
    # Discovery/log channel. Public endpoint may be rate-limited or require auth in future.
    for q in BSKY_QUERIES:
        try:
            params = urllib.parse.urlencode({"q": q, "limit": 5})
            data = get_json(f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?{params}", timeout=15)
            posts = data.get("posts", [])
            log(f"bsky query={q!r} count={len(posts)}")
        except Exception as e:
            log(f"bsky query failed {q!r}: {e}")
    return []


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    log("run " + " ".join(args))
    return subprocess.run(args, cwd=str(ROOT), text=True, capture_output=True, timeout=180)


def main() -> int:
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    INCOMING.parent.mkdir(parents=True, exist_ok=True)
    log("collector start")
    candidates = []
    candidates.extend(collect_pubmed())
    candidates.extend(collect_crossref())
    collect_bsky()

    # Cap per run to avoid flooding. Ingest script handles dedupe.
    seen_titles = set()
    unique = []
    for c in candidates:
        key = c.get("doi") or c.get("pmid") or c.get("title", "").lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        unique.append(c)
    unique.sort(key=lambda e: (e.get("relevance") != "HIGH", e.get("date_published") or ""))
    unique = unique[:8]

    INCOMING.write_text(json.dumps(unique, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"wrote candidates path={INCOMING} count={len(unique)}")

    ingest = run_cmd([str(PYTHON), "scripts/ingest_entries.py", str(INCOMING)])
    if ingest.returncode != 0:
        sys.stderr.write(f"ingest failed\nSTDOUT:\n{ingest.stdout}\nSTDERR:\n{ingest.stderr}\nlog={RUN_LOG}\n")
        return ingest.returncode

    deploy = run_cmd([str(PYTHON), "scripts/deploy_website.py"])
    if deploy.returncode != 0:
        sys.stderr.write(f"deploy failed\nSTDOUT:\n{deploy.stdout}\nSTDERR:\n{deploy.stderr}\nlog={RUN_LOG}\n")
        return deploy.returncode

    summary = json.loads(SUMMARY.read_text(encoding="utf-8")) if SUMMARY.exists() else {}
    log(f"summary={summary}")
    if int(summary.get("high_added_count", 0)) > 0:
        titles = summary.get("added_titles", [])
        print("HIGH Calories research findings added:\n" + "\n".join(f"- {t}" for t in titles) + "\n" + "https://aoh1578.github.io/calories-research-monitor/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
