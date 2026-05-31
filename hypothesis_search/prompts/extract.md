# Hypothesis extractor

Your job: from a recent quant-finance paper (arxiv q-fin or SSRN), extract ONE testable hypothesis that can be evaluated against QQQ daily OHLCV.

## Inputs
- Paper URL, abstract, and (if accessible via WebFetch) the relevant section.
- The seen-papers list at `hypothesis_search/seen_papers.txt` — skip anything already there.
- The ledger at `hypothesis_search/ledger.jsonl` — read the last ~50 rows. Skip hypotheses that are duplicates or close cousins of previously-tested ones.

## Selection rules
1. **The paper must claim a *predictive* relationship**, not just a correlation or a stylized fact. ("X predicts Y at horizon h" — good. "X and Y co-move" — bad.)
2. **The variable on the LHS must be derivable from QQQ OHLCV** (or a transform — e.g., realized vol, returns, range, RSI). If the paper requires data we don't have (cross-sectional dispersion across S&P names, CDS spreads, etc.), reject and try a different paper.
3. **The horizon must be daily-grid feasible** (1–63 trading days). If the paper is monthly-only and there's no obvious daily analogue, reject.
4. **Single hypothesis per paper.** Don't bundle multiple claims; pick the strongest one.

## Output (strict JSON)
```json
{
  "paper_url": "https://arxiv.org/abs/...",
  "paper_title": "...",
  "paper_summary": "1-3 sentences on what the paper claims.",
  "hypothesis": "<feature description in plain English> predicts <forward return horizon> with sign <+1 | -1>",
  "expected_sign": 1,
  "horizon_days": 21,
  "rationale": "<why we expect this to translate to QQQ specifically>"
}
```

If the paper does not yield a viable hypothesis (rejected by rules above), output:
```json
{"paper_url": "...", "skip": true, "reason": "<one sentence>"}
```
