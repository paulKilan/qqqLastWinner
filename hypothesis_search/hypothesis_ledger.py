"""
hypothesis_ledger.py — Persistent ledger of paper-derived hypotheses tested
against QQQ. Each row is a complete record: paper -> hypothesis -> prediction
-> test -> outcome -> kept/discarded with reasoning.

This *is* the moat. Six months in, querying the ledger answers questions like:
  - Which volatility-of-volatility features have we tested? (don't re-test)
  - Which papers' claims didn't replicate on QQQ? (institutional memory)
  - What's our holdout-period false-positive rate? (calibrate skepticism)

Schema (one JSONL row per hypothesis):
  ts                 : ISO timestamp
  paper_id           : SHA1 of the URL or arXiv ID
  paper_url          : source URL
  paper_title        : short
  paper_summary      : 1-3 sentence what the paper claims
  hypothesis         : "<feature X> predicts <outcome Y> with sign/magnitude"
  prediction         : "we expect Spearman rho > 0.05 on holdout, p < 0.05 / k"
  feature_spec       : dict — see feature_translator
  test               : dict — train/holdout split, k tested this batch, alpha
  outcome            : dict — train_rho, holdout_rho, p_value, bh_threshold
  status             : "kept" | "discarded" | "needs-more-data"
  reason             : human-readable why
"""
from __future__ import annotations

import os
import json
import hashlib
from datetime import datetime
from typing import Optional


HD = os.path.dirname(os.path.abspath(__file__))
LEDGER_FILE = os.path.join(HD, "ledger.jsonl")
SEEN_PAPERS_FILE = os.path.join(HD, "seen_papers.txt")
PROMOTED_FEATURES_FILE = os.path.join(HD, "promoted_features.md")


def paper_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def append(rec: dict):
    rec = {"ts": datetime.now().isoformat(timespec="seconds"), **rec}
    with open(LEDGER_FILE, "a") as f:
        f.write(json.dumps(rec) + "\n")
    if rec.get("paper_url"):
        mark_seen(rec["paper_url"])
    if rec.get("status") == "kept":
        _append_promoted(rec)


def load_all() -> list[dict]:
    if not os.path.exists(LEDGER_FILE):
        return []
    rows = []
    with open(LEDGER_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def seen_papers() -> set[str]:
    if not os.path.exists(SEEN_PAPERS_FILE):
        return set()
    with open(SEEN_PAPERS_FILE) as f:
        return {line.strip() for line in f if line.strip()}


def mark_seen(url: str):
    if url in seen_papers():
        return
    with open(SEEN_PAPERS_FILE, "a") as f:
        f.write(url + "\n")


def open_hypotheses(window_days: Optional[int] = None) -> list[dict]:
    rows = load_all()
    return [r for r in rows if r.get("status") == "kept"]


def _append_promoted(rec: dict):
    line = (f"- **{rec.get('paper_title','(untitled)')}** "
            f"({rec.get('paper_url','')}): "
            f"{rec.get('hypothesis','')}  "
            f"holdout_rho={rec.get('outcome',{}).get('holdout_rho','?')}, "
            f"p={rec.get('outcome',{}).get('p_value','?')}\n")
    with open(PROMOTED_FEATURES_FILE, "a") as f:
        f.write(line)


def stats() -> dict:
    rows = load_all()
    by_status = {}
    for r in rows:
        s = r.get("status", "unknown")
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "total": len(rows),
        "by_status": by_status,
        "papers_seen": len(seen_papers()),
    }
