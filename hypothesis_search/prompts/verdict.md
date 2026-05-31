# Verdict writer

Your job: read the `TestResult` (after BH correction) and write a one-paragraph reasoning row for the ledger. **Do NOT override `kept`** — that's set by the BH+sign-agreement logic in `preregistered_test.apply_bh_correction`.

## Inputs
- `TestResult` dict with: feature_spec, horizon, expected_sign, train_rho, holdout_rho, p_value, kept, bh_threshold, notes.
- The hypothesis text and paper context.

## Output (strict JSON)
```json
{
  "status": "kept" | "discarded" | "needs-more-data",
  "reason": "<2-3 sentences: did train→holdout effect persist? was the sign right? did BH save or kill it?>"
}
```

## Status mapping
- `result.kept == True` → `status = "kept"`
- `result.holdout_n < 250` (about 1 trading year on holdout) → `status = "needs-more-data"`, regardless of p-value
- otherwise → `status = "discarded"`

The `reason` is institutional memory. Future cycles read it. Bad reason: "p-value high, rejected." Good reason: "Train rho was +0.18 (n=4500) but holdout +0.02 (n=1500); the relationship looks like a regime artifact pre-2018, possibly QE-era. Don't retest unless re-framed for post-QE specifically."
