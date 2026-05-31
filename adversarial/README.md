# Adversarial Regime Hunter

GAN-style strategy stress-test. Each cycle:

1. **Breaker** finds a time window where the harness's *current best* underperforms QQQ buy-and-hold, tagged with vol/trend/dispersion/rate regime labels.
2. **Patcher** proposes a SPEC param adjustment targeting that regime, with one-sentence rationale per param.
3. **Validator** (deterministic Python) checks the patch on:
   - the failure window (must improve materially),
   - 3 same-regime windows (must hold up on average),
   - 3 different-regime windows (must not regress),
   - the harness EVAL_WINDOWS holdout (must not regress).
   
   Verdict: `generalizes` / `overfits` / `regresses-elsewhere` / `neutral`.

4. **Ledger** appends one JSONL row to `ledger.jsonl`. Generalizing patches save a candidate snapshot to `candidates/` for human review. **Patches never auto-apply to the harness.**

## Files

| File | Purpose |
|---|---|
| `regime_labeler.py` | Vol / trend / dispersion / rate-proxy tags from QQQ data. |
| `breaker.py` | Sliding-window scan; reads current best from `autoresearch/harness/state.json`. |
| `patcher.py` | Validates / clamps a proposed patch against `mutator.SPEC`. |
| `validator.py` | Runs the four-cohort generalization test with hard thresholds. |
| `ledger.py` | Append-only JSONL + candidate snapshot store. |
| `prompts/` | Per-role markdown prompts the routine consumes. |
| `routine.md` | The single-cycle Claude Routine prompt. |

## Run as Claude Routine

In Claude (the app), invoke `/schedule`. Paste `routine.md` as the routine prompt. Pick a cadence (suggested: every 4–8 hours when the harness is active; pause it if the harness is stopped).

Each fire = one cycle, ~3–8 minutes, one ledger row. Cost is bounded.

## Run manually (debugging)

```bash
# Print top-8 failure windows for current best
python -c "from adversarial.breaker import load_current_best_params, find_failures, to_jsonable; import json; print(json.dumps(to_jsonable(find_failures(load_current_best_params(), top_n=8)), indent=2))"

# Validate a patch on a specific window
python -c "
from adversarial.validator import validate, to_dict
from adversarial.breaker import load_current_best_params
from adversarial.regime_labeler import label_dict
import json
fw = ('2007-01-02', '2008-12-31')
regime = label_dict(*fw)
patch = {'subC_rsi2_thresh': 8}
print(json.dumps(to_dict(validate(fw, regime, patch, load_current_best_params())), indent=2))
"
```

## Why pre-registered cohorts (vs. backtest soup)

The Validator's four cohorts (failure / same-regime / other-regime / holdout) are fixed by `validator.py` at the time of each cycle. The Patcher does not see them when proposing the patch. This is what prevents the loop from quietly converging to "patches that look good in averages." If the patch only works on the failure window, `same-regime` will tell you. If it breaks something else, `other-regime` or `holdout` will tell you.
