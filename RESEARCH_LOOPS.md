# Research Loops

Two long-running, agent-driven research subprojects layered on top of the harness:

| Subproject | Purpose | Cadence | Cost per fire |
|---|---|---|---|
| [`adversarial/`](adversarial/README.md) | Find regimes that break the harness's current best, propose patches, validate generalization. | Every 4–8 hours when harness is active | ~3–8 min |
| [`hypothesis_search/`](hypothesis_search/README.md) | Read recent quant-finance papers; pre-register and test one hypothesis per paper; maintain ledger. | Weekly | ~12 min |

Both are designed to run as **Claude app Routines** (cron-scheduled remote agents).

## Register as Routines

In Claude (the desktop app), open `/schedule`. For each subproject:

1. **Title:** `Adversarial regime hunter` (or `Hypothesis search`).
2. **Working directory:** the repo root (`crazy-bhabha-598d42` worktree, or main once merged).
3. **Schedule:**
   - Adversarial: `0 */6 * * *` (every 6 hours). Pause when the harness is stopped — adversarial against an unchanging baseline produces redundant findings fast.
   - Hypothesis: `0 9 * * 1` (Mondays 9am). Weekly is plenty; the world doesn't produce 7 testable q-fin papers per day.
4. **Prompt:** paste the contents of the subproject's `routine.md` verbatim.

Each routine fire = exactly one cycle (Breaker→Patcher→Validator, or one batch of K=3 hypothesis tests). One ledger row appended. Process exits. The next fire is independent — there is no long-running daemon to babysit.

## Outputs you'll come back to

| Path | Read this when |
|---|---|
| `adversarial/ledger.jsonl` | Reviewing what regimes broke the strategy and which patches generalized. |
| `adversarial/candidates/` | Picking up a generalizing patch to merge into the harness manually. |
| `hypothesis_search/ledger.jsonl` | Auditing what papers we tested and why each was kept/discarded. |
| `hypothesis_search/promoted_features.md` | Short list of features that passed BH + sign-agreement; candidates for becoming a new ParametricStrategy sub. |

Both ledgers are append-only JSONL — safe to grep, awk, jq.

## What these loops deliberately do NOT do

- **Auto-edit `parametric_strategy.py` or `state.json`.** Promotion of a found patch or a kept feature is always a human decision. The loops produce evidence; you do the merge.
- **Re-fit on the holdout.** The hypothesis loop's pre-registration contract is sacred; the validator's four cohorts are fixed before the patcher proposes anything.
- **Compete with the harness.** The harness explores SPEC param space; the adversarial loop attacks regime gaps; the hypothesis loop proposes new SPEC entries. They're three layers stacked, not three loops doing the same thing.

## Stopping a routine

Use `/schedule` to pause/delete. The Python primitives have no daemon — there's nothing to kill outside the routine system itself. The harness loop is separate (`autoresearch.harness.launch_detached --stop`).
