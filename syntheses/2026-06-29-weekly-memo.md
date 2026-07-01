# Calories Research Weekly Synthesis — 2026-06-29

## Scope
- Date range reviewed: 2026-06-23 through 2026-06-29 (last 7 days)
- Entries reviewed: 17 total entries in data.json; 0 new entries added in the last 7 days
- Data sources checked: data/data.json, runs/*-summary.json, runs/*-collector.log, backups/*-new_entries.json

**Critical note:** The daily collector failed on all 7 days (2026-06-23 through 2026-06-29) with DNS resolution errors (`getaddrinfo failed` for PubMed, Crossref, and Bluesky endpoints). No new literature was ingested this week. The last successful ingestion was 2026-06-19 (historical backfill for FOOD_MATRIX, 3 entries). A PROTEIN_LEVERAGE historical backfill attempted on 2026-06-26 also failed due to network issues.

## Executive takeaways
1. **Collector is offline** — Network/DNS failure has blocked all automated collection for 7+ days. This is an infrastructure issue, not a literature gap.
2. **Evidence base is static and thin** — All 17 entries remain in `needs_human_review` status with `overclaim_risk: MEDIUM`. Zero entries have been human-verified, mechanisms extracted, or chapter-mapped.
3. **Cluster coverage is lopsided** — FOOD_MATRIX (3 entries), ULTRA_PROCESSED (4 entries), ENERGY_BALANCE/GLYCEMIC_DYNAMICS/THERMIC_EFFECT/CIRCADIAN_TIMING have 1–2 entries each. PROTEIN_LEVERAGE, SATIETY_SIGNALS, REWARD_PALATABILITY, MICROBIOME, EXERCISE_COMPENSATION, WEIGHT_REGULATION, ENDOCRINE_ADIPOSE, LABELING_MEASUREMENT, INDIVIDUAL_VARIATION, EATING_RATE have either 0 or only auto-tagged entries without human review.

## Mechanism clusters

| Cluster | Entries | Key mechanisms suggested (from abstracts only) | Evidence quality |
|---------|---------|-----------------------------------------------|------------------|
| **Food matrix / Atwater accuracy** | 3 (2007, 2010, 2012) | Fiber and intact structure reduce metabolizable energy vs. Atwater prediction; almond ME ~32% lower than Atwater; cereal vs. fruit/veg fiber differ | RCT human (n=27, n=18); 1 comparative mammal review — **needs full-text verification** |
| **Ultra-processed foods & intake** | 4 (2019, 2020, 2022, 2026) | UPF → faster eating rate (~48 vs 31 kcal/min) → passive overconsumption; texture/energy density mediate; 2-week RCT shows sustained ER effect | 1 inpatient RCT (Hall 2019, n=20), 1 mechanistic crossover (Forde 2026, n≈?) — **strongest cluster but small samples** |
| **Eating rate & texture** | 3 (overlap with UPF) | Harder texture → slower ER → lower intake; post-meal satiety not fully compensated later | Crossover trials (n=50, n≈?) — **mechanistic human** |
| **Circadian thermogenesis** | 1 (2026) | Endogenous circadian peak in diet-induced thermogenesis in biological morning | Constant-routine RCT — **single study, needs replication** |
| **Glycemic individual variation** | 1 (2026) | Inter-individual glycemic differences scale with GI; argues against large person×food interactions | Mechanistic human — **single study, counters personalization hype** |
| **Low-carb / one-carbon metabolism** | 1 (2026) | LCHF alters one-carbon metabolites vs. processed carb diet (isocaloric) | RCT n=193 — **metabolic mechanism, not directly intake/weight** |

## Chapter-use candidates

| Chapter theme | Ready-to-use entries (after human review) | Gaps |
|---------------|-------------------------------------------|------|
| **Calorie measurement & Atwater limits** | 2007 Zou (fiber), 2012 Novotny (almonds) | No modern Atwater validation studies; no labeling tolerance data |
| **UPF & passive overconsumption** | Hall 2019 (inpatient RCT), Forde 2020/2022/2026 (texture/ER mediation) | No long-term free-living UPF trials; no dose-response; mechanism still debated (energy density vs. texture vs. hyper-palatability) |
| **Food form, texture, eating rate** | Teo 2022 (texture×processing), Forde 2026 (sustained ER effect) | No data on liquid vs. solid calories in UPF context; no chronic adaptation data |
| **Circadian meal timing & TEF** | Vujovic 2026 (constant routine) | Single study; no weight-change outcomes; no translation to real-world eating windows |
| **Glycemic response & personalization** | Della Corte 2026 (GI predicts inter-individual variation) | Counters strong personalization claims; needs integration with microbiome/genetics data |
| **Protein leverage** | **Zero entries** — collector failed on historical backfill | Major gap for book |

## Counterarguments and overclaim risks

1. **Energy balance remains the constraint** — Every "calories not equal" mechanism (matrix, UPF, protein, circadian) operates *within* energy balance. The dataset includes `CLAIM_COUNTERARGUMENT_ENERGY_BALANCE` but no entries explicitly test whether these mechanisms produce weight change *independent* of sustained intake differences. Risk: overstating mechanistic importance without behavioral persistence data.

2. **UPF mechanism attribution is unsettled** — Hall 2019 shows intake difference; Forde 2020/2022/2026 implicate eating rate/texture/energy density. But: (a) NOVA classification conflates processing with formulation; (b) no study diets differ in multiple dimensions; (c) 2-week Forde 2026 shows sustained ER effect but no weight endpoint. Risk: treating "UPF" as a unified causal exposure.

3. **Small samples, short durations** — Hall 2019: n=20, 2 weeks. Novotny 2012: n=18, 18 days. Teo 2022: n=50, single meals. Forde 2026: 2 weeks. Zou 2007: n=27. No long-term free-living RCTs. Risk: extrapolating acute mechanisms to chronic weight regulation.

4. **Publication bias toward positive mechanisms** — Collector queries target mechanism-positive terms. Null/negative studies (e.g., "UPF no different from matched controls when texture/energy density equated") may be missed. No systematic review coverage in dataset.

5. **Animal / comparative data misapplied** — Clauss 2010 (carnivore digestibility) tagged to FOOD_MATRIX and CLAIM_FIBER_MATRIX_ENERGY but is a cross-species review of captive wild mammals. Risk: inappropriate extrapolation to human fiber/matrix effects.

6. **Glycemic personalization overclaim** — Della Corte 2026 argues against large person×food interactions, but study design (GI scaling) may not capture all personalized nutrition claims. Risk: overcorrecting in either direction.

## Human-review priority

| Priority | Entry ID | Why |
|----------|----------|-----|
| **1** | Hall 2019 (20260604-historical-ultra-processed-diets-cause-excess-calorie-intake) | Anchor UPF chapter; only inpatient RCT; need full text for diet composition, compliance, metabolic measures |
| **2** | Novotny 2012 (20260619-historical-discrepancy-atwater-almonds) | Concrete Atwater error quantification; cited widely; need actual ME values, dose-response |
| **3** | Forde 2026 (20260604-eating-rate-has-sustained-effects) | 2-week sustained ER effect; directly tests mechanism mediation; need full text for magnitude, compliance |
| **4** | Zou 2007 (20260619-historical-accuracy-atwater-factors-fiber) | Fiber-specific Atwater error; human RCT; need fiber type×dose detail |
| **5** | Vujovic 2026 (20260604-constant-routine-circadian-thermogenesis) | Only circadian TEF entry; need magnitude (kcal/day), phase relationship, feasibility for meal-timing advice |
| **6** | Della Corte 2026 (20260604-individual-glycemic-responses-scale) | Counters personalization narrative; need effect sizes, GI thresholds, limitations |
| **7** | Teo 2022 (20260604-texture-based-differences-eating-rate) | Texture×processing factorial; need satiety compensation data |
| **8** | Forde 2020 (20260604-historical-ultra-processing-or-oral-processing) | Mechanism framing paper; need full argument structure |
| **9** | Bråtveit 2026 (20260604-marked-changes-one-carbon-metabolism) | Large RCT (n=193) but metabolic endpoints; relevance to calories book needs judgment |
| **10** | Clauss 2010 (20260619-historical-carnivorous-mammals) | Likely low relevance; verify or deprioritize |

## Missing evidence / research targets

1. **PROTEIN_LEVERAGE** — Zero entries. Need: Simpson & Raubenheimer foundational papers, human protein leverage RCTs, protein×UPF interaction studies.
2. **SATIETY_SIGNALS / REWARD_PALATABILITY** — Only auto-tagged via UPF entries. Need: gut hormone (GLP-1, PYY, CCK) response to UPF vs. whole foods; fMRI reward studies; dopamine dynamics.
3. **MICROBIOME** — Zero entries. Need: fiber fermentation → SCFA → energy harvest; UPF emulsifiers/microbiome; inter-individual microbiome variation in energy extraction.
4. **EXERCISE_COMPENSATION / CONSTRAINED_EXPENDITURE** — Zero entries. Need: Pontzer constrained energy model tests; exercise compensation RCTs; interaction with diet composition.
5. **WEIGHT_REGULATION / SET_POINT** — Zero entries. Need: set point vs. settling point human data; metabolic adaptation magnitude; weight loss maintenance biology.
6. **ENDOCRINE_ADIPOSE** — Zero entries. Need: leptin dynamics with weight change; leptin resistance mechanisms; adipose as endocrine organ in calorie regulation.
7. **LABELING_MEASUREMENT** — Only via Atwater entries. Need: FDA/EU labeling tolerances; restaurant/menu labeling accuracy; database vs. analytic values.
8. **INDIVIDUAL_VARIATION** — Only glycemic entry. Need: habitual diet×genetics×microbiome interaction studies; responder/non-responder phenotypes for UPF, protein, fiber.
9. **LONG-TERM FREE-LIVING DATA** — All RCTs are ≤2 weeks inpatient or single-meal. Need: 6–12 month pragmatic trials with mechanism measures.
10. **NEGATIVE/NULL STUDIES** — Collector bias toward positive mechanisms. Need: targeted search for "no difference" studies (e.g., UPF matched for texture/energy density).

## Source notes

- **data/data.json** — 17 entries, all `status: needs_human_review`, `overclaim_risk: MEDIUM`, `book_use` auto-assigned (mechanism/counterargument), `chapter_candidates: []` empty for all.
- **Collector logs (2026-06-23 to 2026-06-29)** — 100% query failure rate due to `getaddrinfo failed` (DNS/network). No candidates generated.
- **Historical backfills** — FOOD_MATRIX (2026-06-19) succeeded (3 entries). PROTEIN_LEVERAGE (2026-06-26) failed (network).
- **No entries from Crossref, Bluesky, or non-PubMed sources** in current dataset.
- **All entries lack**: full-text verification, extracted key findings, mechanism descriptions, quote_or_key_sentence, chapter_candidates, funding/conflict details, sample sizes, durations, populations — all fields empty or placeholder.
- **Date filtering ambiguity**: Since no new entries were added in the last 7 days, this synthesis covers the *entire* current dataset (17 entries), not just recent additions. Clearly marked above.