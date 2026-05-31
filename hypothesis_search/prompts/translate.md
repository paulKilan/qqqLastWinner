# Feature translator

Your job: turn an English-language hypothesis into a `feature_spec` dict that `feature_translator.compile_spec` can compile into a numeric series.

## Supported spec shapes

```
{"kind": "rolling", "source": "close|open|high|low|volume", "op": "pct_change|log_return|zscore|pct_of_mean", "window": <int>}
{"kind": "ratio", "numer": <spec>, "denom": <spec>}
{"kind": "diff",  "left": <spec>,  "right": <spec>}
{"kind": "rsi",   "source": "close", "period": <int>}
{"kind": "vol_of_vol", "window": <int>, "outer_window": <int>}
```

If the hypothesis can't be expressed in these shapes, output `{"unsupported": true, "reason": "..."}`. The orchestrator will record `spec-unsupported` in the ledger and move on. **Don't fabricate** a spec that approximates poorly — false features pollute the ledger.

## Rules
1. **Sign convention.** The hypothesis carries `expected_sign`. Your spec should be the *raw* feature; sign matters at test time, not in the spec.
2. **Standardize where possible.** Prefer `zscore` over raw level when the paper claims "extreme readings predict reversal" — a raw level is usually ambiguous about what "extreme" means.
3. **Horizon match.** The `horizon_days` is set by the extractor and consumed by the test, not encoded in the spec.

## Output (strict JSON)
```json
{
  "feature_spec": {"kind": "vol_of_vol", "window": 20, "outer_window": 60},
  "translation_notes": "Paper's 'volatility-of-volatility' = stdev of 20d rolling realized vol over a 60d window. Z-scoring across full sample is implicit when we test for sign on the residual."
}
```
