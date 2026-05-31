# Hypothesis-driven Feature Search

Replaces blind grid search with paper-derived, pre-registered hypothesis testing. Each cycle:

1. **Search** arxiv q-fin / SSRN via Claude WebSearch.
2. **Extract** ONE testable hypothesis per paper (`prompts/extract.md`).
3. **Translate** it into a `feature_spec` dict (`prompts/translate.md`).
4. **Test** on a fixed train/holdout split with a permutation p-value.
5. **Correct** for multiple comparisons via Benjamini-Hochberg across the batch.
6. **Verdict** — `kept` / `discarded` / `needs-more-data` — written to the ledger with a one-paragraph reason.

The ledger (`ledger.jsonl`) IS the moat. Six months of negative results compound into institutional memory: don't re-test a hypothesis that's already been killed; do read the reason for *why* it was killed before designing a similar one.

## Pre-registration contract

Hard rules (enforced by `preregistered_test.py`):
- Train/holdout split fixed at **2018-12-31**.
- The Translator emits the spec BEFORE seeing holdout data. Spec doesn't change after a bad test.
- Test statistic: Spearman rho on holdout. Permutation p-value (n=1000).
- Sign agreement: holdout sign must match `expected_sign` from the hypothesis.
- BH threshold per batch: `alpha=0.05 * rank/k`, where `k` is the batch size.

A hypothesis is `kept` only if BH-significant AND sign matches both train and holdout. Anything else is `discarded` (or `needs-more-data` if holdout n < 250).

## Files

| File | Purpose |
|---|---|
| `hypothesis_ledger.py` | JSONL append + seen-papers + promoted-features list. |
| `feature_translator.py` | Compile a `feature_spec` dict to a numeric series. |
| `preregistered_test.py` | Train/holdout test, permutation p, BH correction. |
| `prompts/extract.md` | LLM prompt for paper → hypothesis. |
| `prompts/translate.md` | LLM prompt for hypothesis → feature_spec. |
| `prompts/verdict.md` | LLM prompt for test_result → ledger reason. |
| `routine.md` | Single-batch Claude Routine prompt. |

## Run as Claude Routine

In Claude (the app), invoke `/schedule`. Paste `routine.md` as the routine prompt. Suggested cadence: weekly. Each fire tests K=3 hypotheses (≈12 minutes).

## Run manually

```bash
# Test a hand-rolled spec
python -c "
import json
from hypothesis_search.preregistered_test import test_one, apply_bh_correction, to_dict
specs = [
    ({'kind':'rolling','source':'close','op':'zscore','window':60}, 21, -1),
    ({'kind':'vol_of_vol','window':20,'outer_window':60}, 5, -1),
    ({'kind':'rsi','source':'close','period':2}, 5, +1),
]
res = [test_one(s, h, sg) for (s, h, sg) in specs]
res = apply_bh_correction(res)
print(json.dumps([to_dict(r) for r in res], indent=2))
"

# Stats over the ledger
python -c "from hypothesis_search.hypothesis_ledger import stats; print(stats())"
```

## Promoted features

Anything `status == "kept"` also appends a one-line entry to `promoted_features.md`. That file is the human-curated short list. Adding promoted features into `ParametricStrategy` (e.g., as a new Sub-L) is a *manual* decision — the loop never edits `parametric_strategy.py` directly.
