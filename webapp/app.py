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

from flask import Flask, render_template, jsonify
from webapp.signals import get_all_signals
from webapp.simulation import get_simulation_data

app = Flask(__name__, template_folder="templates", static_folder="static")

_signal_cache = None
_sim_cache    = None


@app.route("/")
def index():
    global _signal_cache
    if _signal_cache is None:
        _signal_cache = get_all_signals(refresh_data=False)
    return render_template("index.html", data=_signal_cache)


@app.route("/simulation")
def simulation():
    return render_template("simulation.html")


@app.route("/api/signals")
def api_signals():
    global _signal_cache
    if _signal_cache is None:
        _signal_cache = get_all_signals(refresh_data=False)
    return jsonify(_signal_cache)


@app.route("/api/refresh")
def api_refresh():
    global _signal_cache, _sim_cache
    _signal_cache = get_all_signals(refresh_data=True)
    _sim_cache    = None   # invalidate so simulation re-runs with fresh data
    return jsonify(_signal_cache)


@app.route("/api/simulation")
def api_simulation():
    """Return equity curve data for all tickers (2013-2024). Cached after first call."""
    global _sim_cache
    if _sim_cache is None:
        _sim_cache = get_simulation_data()
    return jsonify(_sim_cache)


if __name__ == "__main__":
    print("Starting dashboard at http://localhost:5000")
    print("Press Ctrl+C to stop.\n")
    _signal_cache = get_all_signals(refresh_data=False)
    app.run(debug=False, port=5000)
