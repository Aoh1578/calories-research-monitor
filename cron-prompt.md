# Calories Research Monitor Cron Prompt

Load and follow the `calories-research-monitor` skill exactly. This job runs in `C:/Users/Home/Documents/Calories/research-monitor`.

Mission: perform an automated research-monitor run for the Calories book evidence ledger. The user is not a doctor, so be conservative, source-first, and citation-aware. Do not give medical advice. Do not ingest LOW relevance items. Social posts are discovery pointers only.

Execution requirements:

1. Determine today's date and use a 180-day lookback window.
2. Read `data/data.json` and `data/seen.json` before searching.
3. Use all three discovery channels every run:
   - Scholar/academic: PubMed, Europe PMC, Crossref, bioRxiv, medRxiv, journal pages, DOI pages.
   - Web: credible science/news/institution/lab pages.
   - Social: public X/Bluesky/web-indexed posts from watchlist researchers, or web search constrained to social URLs if native social tools are unavailable.
4. Daily run strategy: cover a rotating shard of mechanistic nodes based on day-of-year so the system stays inside cron limits, but always include at least one counterargument/null-result query and at least one watchlist/social query. On Mondays, attempt broad coverage across all nodes before summarizing.
5. For candidates, prefer primary mechanistic studies over reviews when both exist. Include null results and critiques when relevant.
6. Extract enough metadata to fill the required entry schema. Use empty strings/arrays if metadata is unavailable. Never fabricate DOI, PMID, journal, author, dates, sample size, funding, or citation strings.
7. Build a JSON array of candidate entries using the skill schema. Each entry must include `status: needs_human_review`.
8. Save candidates to `incoming/YYYY-MM-DD-candidates.json`. If no valid MEDIUM/HIGH candidates exist, save an empty JSON array.
9. Mandatory ingestion and deployment step, even when candidate list is empty:
   ```bash
   cd C:/Users/Home/Documents/Calories/research-monitor
   C:/Users/Home/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe scripts/ingest_entries.py incoming/YYYY-MM-DD-candidates.json
   C:/Users/Home/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe scripts/deploy_website.py
   ```
10. Read `runs/YYYY-MM-DD-summary.json` and `runs/deploy-last.json`.
11. Final notification rules:
   - If HIGH entries were added, report a compact summary with title, URL/DOI, evidence level, node tags, and why it matters to the book.
   - If deployment or ingestion failed, report the exact failed step and log path.
   - If only MEDIUM or zero entries were added and deployment succeeded, return one terse line: `Calories monitor ran successfully. No HIGH findings added.`

Success is not candidate preparation. Success is ingestion, backup, seen-file update, run log, static-site data update, and deployment.
