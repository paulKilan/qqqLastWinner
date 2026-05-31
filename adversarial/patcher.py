"""
patcher.py — Apply a SPEC param patch to current best, evaluate locally.

The Patcher's *reasoning* (which params to change, by how much, why) is done
by the Claude routine via prompts/patcher.md. This module just provides the
mechanical surface: validate a proposed patch against SPEC bounds, apply it,
backtest a list of windows.
"""
from __future__ import annotations

import os
import sys
import copy
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from autoresearch.harness.mutator import SPEC, clamp
from adversarial.breaker import _evaluate, write_active_params


def validate_and_clamp_patch(patch: dict) -> dict:
    """Reject keys outside SPEC; clamp values to bounds. Returns cleaned patch."""
    cleaned = {}
    for k, v in patch.items():
        if k not in SPEC:
            continue
        cleaned[k] = clamp(k, v)
    return cleaned


def apply_patch(base: dict, patch: dict) -> dict:
    out = copy.deepcopy(base)
    out.update(validate_and_clamp_patch(patch))
    # Hard floors (mirrors mutator.mutate)
    out["vote_long"] = max(4, min(6, int(out.get("vote_long", 5))))
    out["vote_short"] = max(1, min(3, int(out.get("vote_short", 2))))
    return out


def evaluate_on_windows(params: dict, windows: list[tuple[str, str]]) -> list[dict]:
    write_active_params(params)
    out = []
    for s, e in windows:
        r = _evaluate(s, e)
        out.append(r)
    return out


def diff_summary(base: dict, patched: dict) -> dict:
    return {k: {"before": base.get(k), "after": patched[k]}
            for k in patched if base.get(k) != patched[k]}
