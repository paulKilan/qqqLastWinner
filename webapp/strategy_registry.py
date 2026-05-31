"""
webapp/strategy_registry.py — Enumerate all available strategies the user can
pick from in the Signals / Simulation UI.

A "strategy" here is a backtest-runnable spec:
  - source: "iter31" | "champion" | "adversarial_candidate"
  - id: stable string for URLs/caching
  - label: human-readable
  - description: short paragraph
  - params: dict ready to feed to ParametricStrategy (None for Iter31 which has its own class)

Two strategy classes power everything:
  - ExperimentalStrategy   (Iter31, fixed 6-sub)
  - ParametricStrategy     (12-sub, params-driven via HARNESS_PARAMS_FILE env)

For ParametricStrategy-based options, we write the params to a per-strategy
temp file and set HARNESS_PARAMS_FILE before instantiation. A module lock
guards the env-var swap across threads.
"""
from __future__ import annotations

import os
import json
import hashlib
import threading
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(ROOT, "autoresearch", "harness", "state.json")
SNAPSHOTS_DIR = os.path.join(ROOT, "autoresearch", "harness", "snapshots")
CANDIDATES_DIR = os.path.join(ROOT, "adversarial", "candidates")
TMP_PARAMS_DIR = os.path.join(ROOT, "webapp", ".strategy_params_cache")
os.makedirs(TMP_PARAMS_DIR, exist_ok=True)

_env_lock = threading.Lock()


def _short_id(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:8]


def list_strategies() -> list[dict]:
    """Return all selectable strategies. Always includes Iter31 as the first entry."""
    out: list[dict] = []

    out.append({
        "id": "iter31",
        "source": "iter31",
        "label": "Iter31 (default 6-sub)",
        "description": "The original hand-tuned 6-sub ensemble. The hardcoded baseline against which everything else is measured.",
        "params": None,
    })

    # Champions from current harness state
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                s = json.load(f)
            for i, c in enumerate(s.get("champions") or []):
                focus = c.get("focus", "?")
                metrics = c.get("metrics") or {}
                label = c.get("label", f"champion-{i}")
                if focus == "min_ratio":
                    headline = f"min_ratio={metrics.get('min_ratio', 0):.3f}"
                elif focus == "sharpe":
                    headline = f"sharpe={metrics.get('mean_sharpe', 0):.2f}"
                elif focus == "outperf":
                    headline = f"outperf={metrics.get('mean_outperf', 0):.2f}x"
                else:
                    headline = f"score={metrics.get('score', 0):.1f}"
                arch = c.get("arch_constraint") or {}
                arch_str = ""
                for k, v in arch.items():
                    if k.startswith("enable_") and v == 1:
                        arch_str += f", Sub-{k[-1]} pinned"
                out.append({
                    "id": f"champ-{i}-{focus}",
                    "source": "champion",
                    "label": f"Champion #{i} · {focus} ({headline}{arch_str})",
                    "description": (
                        f"Harness champion #{i} optimizing '{focus}'. "
                        f"Composite score {metrics.get('score', 0):.2f}, "
                        f"mean return {metrics.get('mean_return_pct', 0):.0f}%, "
                        f"Sharpe {metrics.get('mean_sharpe', 0):.2f}, "
                        f"outperf {metrics.get('mean_outperf', 0):.2f}x, "
                        f"min ratio {metrics.get('min_ratio', 0):.3f}." +
                        (f" Architecture pinned: {arch_str.lstrip(', ')}." if arch_str else "")
                    ),
                    "params": c["params"],
                    "label_internal": label,
                    "metrics": {k: metrics.get(k) for k in
                                ("score", "mean_return_pct", "mean_sharpe", "mean_outperf",
                                 "mean_max_dd_pct", "min_ratio")},
                })
        except Exception:
            pass

    # Historical promotions — the legacy single-best harness run kept these
    # as prom1_*.json through promN_*.json in snapshots/. Useful for comparing
    # the search trajectory. We keep the LATEST timestamp per prom# (dedups
    # earlier runs that recreated prom1 etc).
    if os.path.isdir(SNAPSHOTS_DIR):
        prom_latest: dict[int, tuple[str, dict]] = {}
        for fn in sorted(os.listdir(SNAPSHOTS_DIR)):
            if not fn.startswith("prom") or not fn.endswith(".json"):
                continue
            try:
                n = int(fn.split("_")[0][4:])
            except ValueError:
                continue
            path = os.path.join(SNAPSHOTS_DIR, fn)
            try:
                with open(path, encoding="utf-8") as f:
                    snap = json.load(f)
            except Exception:
                continue
            if n not in prom_latest or fn > prom_latest[n][0]:
                prom_latest[n] = (fn, snap)
        for n in sorted(prom_latest):
            fn, snap = prom_latest[n]
            params = snap.get("params")
            metrics = snap.get("metrics") or {}
            if not params:
                continue
            out.append({
                "id": f"hist-prom-{n}",
                "source": "historical_promotion",
                "label": f"History · prom{n} (score={metrics.get('score', 0):.1f})",
                "description": (
                    f"Historical promotion #{n} from the legacy single-best harness run. "
                    f"Composite score {metrics.get('score', 0):.2f}, "
                    f"mean return {metrics.get('mean_return_pct', 0):.0f}%, "
                    f"Sharpe {metrics.get('mean_sharpe', 0):.2f}, "
                    f"outperf {metrics.get('mean_outperf', 0):.2f}x. "
                    f"Snapshot file: {fn}"
                ),
                "params": params,
                "metrics": {k: metrics.get(k) for k in
                            ("score", "mean_return_pct", "mean_sharpe", "mean_outperf",
                             "mean_max_dd_pct", "min_ratio")},
                "source_file": fn,
            })

    # Adversarial candidates
    if os.path.isdir(CANDIDATES_DIR):
        for fn in sorted(os.listdir(CANDIDATES_DIR)):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(CANDIDATES_DIR, fn)
            try:
                with open(path, encoding="utf-8") as f:
                    cand = json.load(f)
            except Exception:
                continue
            params = cand.get("patched_params") or cand.get("params")
            if not params:
                continue
            window = cand.get("failure_window", "?")
            verdict = cand.get("verdict", "?")
            out.append({
                "id": f"adv-{_short_id(fn)}",
                "source": "adversarial_candidate",
                "label": f"Adversarial · {fn.replace('.json','')[:40]} ({verdict})",
                "description": (
                    f"Adversarial patch targeting failure window {window}. "
                    f"Verdict: {verdict}. " +
                    (cand.get("summary") or "")[:200]
                ),
                "params": params,
                "source_file": fn,
            })

    return out


def find_strategy(strategy_id: Optional[str]) -> dict:
    """Look up a strategy spec by id. Defaults to Iter31 if missing/unknown."""
    if not strategy_id:
        return list_strategies()[0]
    for s in list_strategies():
        if s["id"] == strategy_id:
            return s
    return list_strategies()[0]


def write_params_for(strategy: dict) -> Optional[str]:
    """For a ParametricStrategy-based spec, write its params to a temp file and
    return the absolute path. Returns None for Iter31 (which doesn't read this).
    """
    if strategy["source"] == "iter31":
        return None
    path = os.path.join(TMP_PARAMS_DIR, f"{strategy['id']}.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(strategy["params"], f, indent=2)
    os.replace(tmp, path)
    return path


def instantiate_strategy(strategy: dict, ticker: str = "QQQ"):
    """Return a strategy instance ready for run_backtest / evaluate_window.

    For Iter31: instantiates ExperimentalStrategy.
    For champions / adversarial candidates: writes params to a temp file,
    sets HARNESS_PARAMS_FILE under a lock, instantiates ParametricStrategy.
    """
    if strategy["source"] == "iter31":
        from autoresearch.experimental_strategy import ExperimentalStrategy
        return ExperimentalStrategy()

    params_file = write_params_for(strategy)
    with _env_lock:
        prev = os.environ.get("HARNESS_PARAMS_FILE")
        os.environ["HARNESS_PARAMS_FILE"] = params_file
        try:
            import sys
            # Force re-import so module re-reads the env var
            if "autoresearch.harness.parametric_strategy" in sys.modules:
                del sys.modules["autoresearch.harness.parametric_strategy"]
            from autoresearch.harness.parametric_strategy import ParametricStrategy
            inst = ParametricStrategy()
        finally:
            if prev is not None:
                os.environ["HARNESS_PARAMS_FILE"] = prev
            else:
                os.environ.pop("HARNESS_PARAMS_FILE", None)
    return inst


def strategy_for_display(strategy_id: Optional[str]) -> dict:
    """Lightweight dict for the dropdown + header banner — no params payload."""
    s = find_strategy(strategy_id)
    return {
        "id": s["id"],
        "source": s["source"],
        "label": s["label"],
        "description": s["description"],
        "n_subs": 6 if s["source"] == "iter31" else 12,
        "metrics": s.get("metrics"),
    }
