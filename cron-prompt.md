# Calories Research Monitor Cron Prompt

Load and follow the `calories-research-monitor` skill exactly. Workdir: `C:/Users/Home/Documents/Calories/research-monitor`.

HARD RUNTIME RULE: Hermes cron runs have a short hard budget. Do not do deep extraction loops. Complete ingestion and deploy even when candidate count is zero. Preparation without ingest+deploy is failure.

Mission: run one bounded daily research-monitor pass for the Calories book.

Steps:
1. Read `data/data.json` and `data/seen.json` if available. Do not try to read directories as files.
2. Use all three discovery channels with small bounded searches:
   - Scholar: 3 web_search calls constrained to PubMed/preprint/journal domains.
   - Web: 2 web_search calls for credible institutional/journal/news pages.
   - Social: 2 web_search calls constrained to `site:x.com` or `site:bsky.app` for watchlist names/topics.
   Include at least one counterargument/null-result query.
3. Do not use `web_extract` on more than 2 URLs total. Prefer PubMed/DOI/journal metadata. If extraction is slow or blocked, skip it and log the limitation.
4. Build only safely-supported HIGH/MEDIUM candidate entries. Do not invent DOI, PMID, authors, sample size, citation strings, or dates. Use empty strings/arrays when unknown. Exclude LOW.
5. Write candidates, even an empty array, to `incoming/YYYY-MM-DD-candidates.json`.
6. Always run:
   `C:/Users/Home/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe scripts/ingest_entries.py incoming/YYYY-MM-DD-candidates.json`
   `C:/Users/Home/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe scripts/deploy_website.py`
7. Read `runs/YYYY-MM-DD-summary.json` and verify `docs/data.json` exists.
8. Notify only if HIGH entries were added. If no HIGH entries and deployment succeeded, final response may be one compact status line.

Failure reporting: if ingestion or deploy fails, report the exact command, exit output, and relevant run/log path.
