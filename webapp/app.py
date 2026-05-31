"""
webapp/app.py — Flask web server for the Iter31 trading signal dashboard.

Run from project root:
  python webapp/app.py

Then open: http://localhost:5000
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from flask import Flask, render_template, jsonify, request
from webapp.signals import get_all_signals
from webapp.simulation import get_simulation_data
from webapp.research import get_research_data
from webapp.strategy_registry import list_strategies, strategy_for_display

app = Flask(__name__, template_folder="templates", static_folder="static")

# Per-strategy caches keyed by strategy_id.
_signal_cache: dict = {}
_sim_cache: dict = {}


def _strategy_id_from_request() -> str:
    return request.args.get("strategy", "iter31") if request else "iter31"


SOURCE_GROUP_TITLES = {
    "iter31": "Baseline",
    "champion": "Live Champions (multi-island)",
    "adversarial_candidate": "Adversarial Candidates",
    "historical_promotion": "Historical Promotions",
}


def _grouped_strategies():
    """Return [(group_title, [strategy_dicts])] preserving the order of first appearance."""
    groups: dict = {}
    order: list = []
    for s in list_strategies():
        title = SOURCE_GROUP_TITLES.get(s["source"], s["source"])
        if title not in groups:
            groups[title] = []
            order.append(title)
        groups[title].append({"id": s["id"], "label": s["label"], "source": s["source"]})
    return [(t, groups[t]) for t in order]


@app.route("/")
def index():
    sid = _strategy_id_from_request()
    if sid not in _signal_cache:
        _signal_cache[sid] = get_all_signals(refresh_data=False, strategy_id=sid)
    return render_template("index.html",
                           data=_signal_cache[sid],
                           strategy_groups=_grouped_strategies(),
                           selected_strategy=sid)


@app.route("/simulation")
def simulation():
    sid = _strategy_id_from_request()
    return render_template("simulation.html",
                           strategy_groups=_grouped_strategies(),
                           selected_strategy=sid,
                           selected_strategy_meta=strategy_for_display(sid))


@app.route("/research")
def research():
    return render_template("research.html", data=get_research_data())


@app.route("/api/strategies")
def api_strategies():
    return jsonify([
        {"id": s["id"], "label": s["label"], "source": s["source"],
         "description": s["description"], "metrics": s.get("metrics")}
        for s in list_strategies()
    ])


@app.route("/api/signals")
def api_signals():
    sid = _strategy_id_from_request()
    if sid not in _signal_cache:
        _signal_cache[sid] = get_all_signals(refresh_data=False, strategy_id=sid)
    return jsonify(_signal_cache[sid])


@app.route("/api/refresh")
def api_refresh():
    sid = _strategy_id_from_request()
    # OHLCV files are shared across all strategies, so a data refresh
    # invalidates every cached strategy — not just the one the user is
    # currently viewing. Otherwise a refresh on /research (typically sid=iter31)
    # leaves /simulation showing stale data for champion_N strategies.
    fresh = get_all_signals(refresh_data=True, strategy_id=sid)
    _signal_cache.clear()
    _signal_cache[sid] = fresh
    _sim_cache.clear()
    return jsonify(fresh)


@app.route("/api/simulation")
def api_simulation():
    """Return equity curve data for QQQ under chosen strategy. Cached per strategy."""
    sid = _strategy_id_from_request()
    if sid not in _sim_cache:
        _sim_cache[sid] = get_simulation_data(strategy_id=sid)
    return jsonify(_sim_cache[sid])


@app.route("/api/research")
def api_research():
    """Always fresh — never cached. Reads from harness state files on every request."""
    return jsonify(get_research_data())


if __name__ == "__main__":
    print("Starting dashboard at http://localhost:5000")
    print("Press Ctrl+C to stop.\n")
    _signal_cache["iter31"] = get_all_signals(refresh_data=False, strategy_id="iter31")
    app.run(debug=False, port=5000)
