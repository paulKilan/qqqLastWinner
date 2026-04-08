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

app = Flask(__name__, template_folder="templates", static_folder="static")

# Cache signals so page loads are fast; refreshed on demand
_cache = None


@app.route("/")
def index():
    global _cache
    if _cache is None:
        _cache = get_all_signals(refresh_data=False)
    return render_template("index.html", data=_cache)


@app.route("/api/signals")
def api_signals():
    """JSON endpoint — returns current signals without refreshing data."""
    global _cache
    if _cache is None:
        _cache = get_all_signals(refresh_data=False)
    return jsonify(_cache)


@app.route("/api/refresh")
def api_refresh():
    """Fetch latest data from Yahoo Finance, recompute signals, return JSON."""
    global _cache
    _cache = get_all_signals(refresh_data=True)
    return jsonify(_cache)


if __name__ == "__main__":
    print("Starting dashboard at http://localhost:5000")
    print("Press Ctrl+C to stop.\n")
    # Pre-load on startup
    _cache = get_all_signals(refresh_data=False)
    app.run(debug=False, port=5000)
