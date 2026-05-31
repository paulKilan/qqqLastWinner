"""
tested_set.py — Persistent set of already-evaluated parameter combinations.

Each candidate is reduced to a canonical 16-char hash over the SPEC keys.
Hashes are appended to `tested.hashes` (one per line) and loaded into an
in-memory set on startup so duplicates are rejected without re-evaluating.

Total parameter space: ~1.9e52, so literal "all combos tested" is unreachable.
The practical exhaustion signal is *collision saturation*: when N consecutive
random draws all hit already-tested combos, the sampler has saturated its
reachable subspace (k <= max_k draws around defaults).
"""

import os
import json
import hashlib
from autoresearch.harness.mutator import SPEC


HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
TESTED_FILE = os.path.join(HARNESS_DIR, "tested.hashes")


def canonical_key(params: dict) -> str:
    items = [(k, params.get(k)) for k in sorted(SPEC.keys())]
    payload = json.dumps(items, sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()[:16]


def total_combo_space() -> int:
    n = 1
    for lo, hi, step in SPEC.values():
        if step >= 1:
            count = int((hi - lo) // step) + 1
        else:
            count = int(round((hi - lo) / step)) + 1
        n *= count
    return n


class TestedSet:
    def __init__(self, path: str = TESTED_FILE):
        self.path = path
        self.seen = set()
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    h = line.strip()
                    if h:
                        self.seen.add(h)

    def has(self, params: dict) -> bool:
        return canonical_key(params) in self.seen

    def add(self, params: dict) -> bool:
        h = canonical_key(params)
        if h in self.seen:
            return False
        self.seen.add(h)
        with open(self.path, "a") as f:
            f.write(h + "\n")
        return True

    def __len__(self):
        return len(self.seen)
