# Adversarial Regime Hunter — single-cycle routine

You are running ONE cycle of the adversarial regime hunter. Each routine fire = one Breaker→Patcher→Validator pass. Append exactly one row to `adversarial/ledger.jsonl` and exit.

## Setup
Working dir: repository root containing `adversarial/`, `autoresearch/`, `strategy/`.
The harness runs separately. Do NOT modify `autoresearch/harness/state.json` — adversarial patches are advisory.

## Cycle steps

### 1. Find failure windows
Run:
```bash
python -c "
import json
from adversarial.breaker import load_current_best_params, find_failures, to_jsonable
from adversarial.ledger import attempted_failure_windows
p = load_current_best_params()
exclude = attempted_failure_windows()
fs = find_failures(p, top_n=8, window_years=1.0, step_months=6, exclude=exclude)
print(json.dumps(to_jsonable(fs), indent=2))
"
```

### 2. Breaker — pick ONE failure window
Read `adversarial/prompts/breaker.md`. Apply its rules to the JSON output above. Emit the strict JSON (`failure_window`, `regime_summary`, `underperf_pct`, `hypothesis`).

If all returned windows are uninteresting (e.g., QQQ also negative, or all regimes already heavily attacked), append a `{event: "no-target"}` row to the ledger and exit.

### 3. Patcher — propose a SPEC patch
Read `adversarial/prompts/patcher.md`. Read the SPEC bounds in `autoresearch/harness/mutator.py`. Read current best params from `autoresearch/harness/state.json`. Emit the strict JSON (`patch`, `rationale`).

### 4. Validate (deterministic — Python does the math)
```bash
python -c "
import json
from adversarial.validator import validate, to_dict
from adversarial.breaker import load_current_best_params
fw = ('<START>', '<END>')              # from Breaker
regime = <REGIME_DICT_FROM_BREAKER>     # from Breaker output (dict)
patch = <PATCH_DICT>                   # from Patcher output
res = validate(fw, regime, patch, baseline_params=load_current_best_params())
print(json.dumps(to_dict(res), indent=2))
"
```

### 5. Validator — write the human-readable verdict
Read `adversarial/prompts/validator.md`. Consume the JSON above. Emit the strict JSON (`verdict`, `summary`, `merge_recommendation`).

### 6. Ledger append
```bash
python -c "
import json
from adversarial.ledger import append, save_candidate
append({
  'failure_window': '<START> to <END>',
  'regime': <REGIME_DICT>,
  'breaker_hypothesis': '<...>',
  'patch': <PATCH_DICT>,
  'patcher_rationale': [...],
  'validation': <VALIDATION_DICT>,
  'verdict': '<verdict>',
  'summary': '<...>',
  'merge_recommendation': '<review|discard>',
})
"
```

If `merge_recommendation == "review"`, also save the candidate snapshot:
```python
from adversarial.ledger import save_candidate
save_candidate('<window-tag>_<verdict>', {'params': <patched_params_dict>, 'baseline_window_diff': ...})
```

### 7. Stop
Print a one-line summary and exit. **Do not chain into another cycle.** If the user wants more cycles, they will fire the routine again.

## Constraints
- **Never modify the harness state file.** Adversarial findings are read-only relative to the harness.
- **One cycle per fire.** Routines are billed; bounded work prevents runaway cost.
- **No web access required.** Everything runs against local CSVs.
- Budget guideline: ≤ 8 minutes wall clock per cycle.
