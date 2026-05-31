# Hypothesis-driven Feature Search — single-cycle routine

You are running ONE batch of hypothesis tests. Each routine fire = pick K papers, extract → translate → test → record verdict. Append K rows to `hypothesis_search/ledger.jsonl` and exit.

`K` (batch size) defaults to **3**. Smaller K = lower BH penalty per hypothesis. Don't push K above 5 without good reason.

## Setup
Working dir: repo root. The ledger lives at `hypothesis_search/ledger.jsonl`, seen-papers at `hypothesis_search/seen_papers.txt`.

## Cycle steps

### 1. Find candidate papers (WebSearch)
Run a WebSearch with a query like one of:
- `arxiv q-fin recent forecasting return predictability`
- `SSRN equity volatility predictor 2025`
- `arxiv quantitative finance momentum reversal signal`

Vary the query each cycle; record which query you used in the ledger row. Pull the top 5–8 results, drop any URL already in `hypothesis_search/seen_papers.txt`. Skim abstracts; pick K candidates whose claims look extractable (see `prompts/extract.md`).

### 2. For each of K candidates: Extract hypothesis
Read `prompts/extract.md`. WebFetch the paper page, read abstract + relevant section, emit the strict JSON. If `skip: true`, mark seen and pick a replacement candidate from the search results (don't compromise on K).

### 3. For each kept hypothesis: Translate to feature_spec
Read `prompts/translate.md`. Emit the strict JSON. If `unsupported: true`, ledger-append a `spec-unsupported` row and move on.

### 4. Run the pre-registered test (deterministic Python)
```bash
python -c "
import json
from hypothesis_search.preregistered_test import test_one, apply_bh_correction, to_dict
specs = [
  (<feature_spec_1>, <horizon_1>, <expected_sign_1>),
  (<feature_spec_2>, <horizon_2>, <expected_sign_2>),
  (<feature_spec_3>, <horizon_3>, <expected_sign_3>),
]
results = [test_one(s, h, sg) for (s, h, sg) in specs]
results = apply_bh_correction(results)
print(json.dumps([to_dict(r) for r in results], indent=2))
"
```

### 5. For each result: Write verdict
Read `prompts/verdict.md`. Emit the strict JSON.

### 6. Append K rows to the ledger
```bash
python -c "
from hypothesis_search.hypothesis_ledger import append, paper_id
for row in <ROWS_LIST>:
    append(row)
"
```
Each row must include: `paper_id`, `paper_url`, `paper_title`, `paper_summary`, `hypothesis`, `prediction`, `feature_spec`, `test`, `outcome`, `status`, `reason`.

### 7. Stop
Print `hypothesis_ledger.stats()` and exit. **One batch per fire.**

## Constraints
- **Pre-registration is sacred.** TRAIN_END is fixed at `2018-12-31`. Do not change it mid-cycle.
- **No re-testing.** If a hypothesis appears in the ledger already (same `feature_spec` + `horizon` + `expected_sign`), do not retest. Record a `duplicate` skip.
- **No feature engineering after seeing holdout.** If the test result is bad, don't re-translate the hypothesis. Record discarded; move on.
- **Web access required** (WebSearch + WebFetch on arxiv/SSRN).
- Budget guideline: ≤ 12 minutes wall clock per cycle.
