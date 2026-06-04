# Historical Backfill Plan

Purpose: build the book's durable evidence spine without polluting the daily monitor.

The daily collector answers: what changed recently?
The historical backfill answers: what has mattered for years?

## Operating rules

- Keep daily recent monitoring at a 180-day lookback.
- Run historical backfill separately, one mechanistic node per run.
- Prefer foundational human trials, controlled feeding studies, metabolic ward studies, major reviews, measurement papers, and important counterarguments/nulls.
- Cap each run tightly. Better three load-bearing entries than thirty noisy ones.
- Every entry remains `needs_human_review` until read by a human.
- Do not ingest social posts as historical evidence. Use them only to discover primary sources.
- Do not present automatically collected abstracts as manuscript-ready claims.

## Backfill waves

1. `ULTRA_PROCESSED`: NOVA, Hall metabolic ward trial, passive overconsumption, critiques.
2. `FOOD_MATRIX`: Atwater factors, metabolizable energy, nuts/almonds, intact vs processed structure.
3. `PROTEIN_LEVERAGE`: Simpson/Raubenheimer, protein appetite, satiety, thermic cost.
4. `EATING_RATE`: eating rate, oral processing, texture, beverages vs solids.
5. `GLYCEMIC_DYNAMICS`: personalized glycemic response, PREDICT, CGM variability, limits.
6. `EXERCISE_COMPENSATION`: Pontzer, constrained expenditure, adaptive thermogenesis, compensation.
7. `LABELING_MEASUREMENT`: labeling tolerances, restaurant label error, bomb calorimetry limits.
8. `ENERGY_BALANCE`: isocaloric trials, energy balance defenses, counterarguments.
9. `MICROBIOME`: fermentation, SCFAs, energy harvest, fiber.
10. `SATIETY_SIGNALS`: ghrelin, GLP-1, PYY, gastric emptying, appetite biology.
11. `REWARD_PALATABILITY`: hyperpalatable foods, reward, choice architecture, limits.
12. `CIRCADIAN_TIMING`: meal timing, late eating, time-restricted eating.
13. `INDIVIDUAL_VARIATION`: metabolic phenotypes, inter-individual variability.
14. `WEIGHT_REGULATION`: set point, settling point, adaptive response.
15. `ENDOCRINE_ADIPOSE`: leptin and adipose feedback.
16. `THERMIC_EFFECT`: diet-induced thermogenesis, protein cost.

## Cadence

- Weekly backfill: Friday 10:00 AM local time.
- One node per run, rotating through `backfill/state.json`.
- Max 3 additions per run.
- After deployment, the Monday synthesis memo can interpret the new historical entries for the book.

## Success condition

A successful backfill run:

1. Selects the next node from `backfill/state.json`.
2. Searches historical PubMed/Crossref-style metadata, preferably 1990-present unless the node needs older classics.
3. Writes candidates to `incoming/YYYY-MM-DD-historical-NODE-candidates.json`.
4. Runs `scripts/ingest_entries.py`.
5. Runs `scripts/deploy_website.py`.
6. Writes `runs/YYYY-MM-DD-historical-NODE-summary.json`.
7. Updates `backfill/state.json` to the next node only after successful ingest/deploy.

## Book-use standard

Historical backfill should privilege entries that can do one of these jobs:

- establish a mechanism;
- give the chapter a concrete experiment;
- supply a number worth remembering;
- complicate an over-neat claim;
- defend the fair counterargument that energy balance still matters.
