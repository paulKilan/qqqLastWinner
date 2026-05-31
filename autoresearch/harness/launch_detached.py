"""
launch_detached.py — Spawn the harness loop as a detached Windows process.

The child process survives this script exiting AND the parent terminal
closing. Output goes to autoresearch/harness/harness.out.log.

Usage:
    python -m autoresearch.harness.launch_detached         # start
    python -m autoresearch.harness.launch_detached --stop  # request stop (creates STOP file)
    python -m autoresearch.harness.launch_detached --status

Stop is graceful — the loop checks for the STOP file each iteration and
exits cleanly. Use kill PID only if it's truly wedged.
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(HARNESS_DIR, "harness.pid")
OUT_LOG = os.path.join(HARNESS_DIR, "harness.out.log")
STOP_FILE = os.path.join(HARNESS_DIR, "STOP")
HEARTBEAT_FILE = os.path.join(HARNESS_DIR, "heartbeat.txt")
STATE_FILE = os.path.join(HARNESS_DIR, "state.json")


def _is_alive(pid: int) -> bool:
    try:
        if sys.platform == "win32":
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True
            )
            return str(pid) in r.stdout
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def start():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                old = int(f.read().strip())
            if _is_alive(old):
                print(f"Harness already running with PID {old}.")
                return
        except Exception:
            pass

    if os.path.exists(STOP_FILE):
        os.remove(STOP_FILE)

    log_fh = open(OUT_LOG, "a", buffering=1)
    log_fh.write(f"\n=== Launch {datetime.now().isoformat()} ===\n")

    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            [sys.executable, "-m", "autoresearch.harness.loop"],
            cwd=ROOT_DIR,
            stdout=log_fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )
    else:
        proc = subprocess.Popen(
            [sys.executable, "-m", "autoresearch.harness.loop"],
            cwd=ROOT_DIR,
            stdout=log_fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )

    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

    print(f"Harness launched as PID {proc.pid}")
    print(f"  state:     {STATE_FILE}")
    print(f"  heartbeat: {HEARTBEAT_FILE}")
    print(f"  stdout:    {OUT_LOG}")
    print(f"  log.jsonl: {os.path.join(HARNESS_DIR, 'log.jsonl')}")
    print(f"To stop:   python -m autoresearch.harness.launch_detached --stop")
    print(f"To status: python -m autoresearch.harness.launch_detached --status")


def stop():
    if not os.path.exists(PID_FILE):
        print("No PID file. Harness not tracked.")
        return
    with open(STOP_FILE, "w") as f:
        f.write(datetime.now().isoformat())
    print("STOP file created. Harness will exit on its next iteration boundary.")
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    print(f"Tracked PID: {pid} (alive: {_is_alive(pid)})")


def status():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        print(f"PID: {pid}  alive: {_is_alive(pid)}")
    else:
        print("No PID file.")
    if os.path.exists(HEARTBEAT_FILE):
        print(f"Heartbeat: {open(HEARTBEAT_FILE).read().strip()}")
    tested_path = os.path.join(HARNESS_DIR, "tested.hashes")
    if os.path.exists(tested_path):
        with open(tested_path) as f:
            n = sum(1 for _ in f)
        print(f"Tested combos: {n}")
    if os.path.exists(STATE_FILE):
        import json
        s = json.load(open(STATE_FILE))
        print(f"Iterations: {s.get('iterations')}  Promotions: {s.get('promotions')}")
        champs = s.get("champions") or []
        if champs:
            print(f"Champions: {len(champs)}")
            for i, c in enumerate(champs):
                m = c.get("metrics") or {}
                print(f"  #{i} {c.get('focus','?'):<10} score={m.get('score',0):>8.2f}  "
                      f"ret={m.get('mean_return_pct',0):>10.0f}%  sharpe={m.get('mean_sharpe',0):.2f}  "
                      f"outperf={m.get('mean_outperf',0):.2f}x  min_ratio={m.get('min_ratio',0):.3f}  {c.get('label','')}")
        else:
            m = s.get("metrics") or {}
            print(f"Label: {s.get('label')}")
            if m.get("ok") and "score" in m:
                print(f"Score: {m['score']:.4f}  Ret: {m.get('mean_return_pct',0):.1f}%  "
                      f"Sharpe: {m.get('mean_sharpe',0):.2f}  Outperf: {m.get('mean_outperf',0):.2f}x  "
                      f"DD: {m.get('mean_max_dd_pct',0):.1f}%")


def report(snapshot: str = None):
    """Pretty-print per-window stats for the current best, or a named snapshot."""
    import json
    if snapshot:
        path = os.path.join(HARNESS_DIR, "snapshots", f"{snapshot}.json")
        if not os.path.exists(path):
            print(f"Snapshot not found: {path}")
            return
    else:
        path = STATE_FILE
        if not os.path.exists(path):
            print("No state.json yet.")
            return

    s = json.load(open(path))
    m = s.get("metrics") or {}
    if not m.get("ok") or "score" not in m:
        print("State has no scored metrics (legacy or pre-baseline).")
        return

    print("=" * 110)
    print(f"  Label:       {s.get('label')}")
    print(f"  Iteration:   {s.get('iterations')}   Promotions: {s.get('promotions')}")
    print(f"  Score:       {m['score']:.4f}")
    print(f"  Mean return: {m['mean_return_pct']:.1f}%   Sharpe: {m['mean_sharpe']:.2f}   "
          f"Outperf: {m['mean_outperf']:.2f}x   DD: {m['mean_max_dd_pct']:.1f}%")
    print("=" * 110)
    print(f"  {'Window':<27} {'Strat%':>12} {'QQQ%':>12} {'Ratio':>8} "
          f"{'Tr/Yr':>7} {'Win%':>7} {'MaxDD%':>9} {'Sharpe':>7}")
    print("  " + "-" * 106)

    rets = m.get("rets", {}); qqq = m.get("qqq_rets", {}); rat = m.get("ratios", {})
    tyr = m.get("trades_yr", {}); wr = m.get("win_rate", {}); sh = m.get("sharpe", {}); dd = m.get("max_dd", {})

    for win in rets:
        print(f"  {win:<27} {rets[win]:>+11.1f}% {qqq.get(win, 0):>+11.1f}% "
              f"{rat.get(win, 0):>7.2f}x {tyr.get(win, 0):>6.1f} "
              f"{wr.get(win, 0):>6.1%} {dd.get(win, 0):>8.1f}% {sh.get(win, 0):>6.2f}")

    print("\n  Params (non-default only):")
    from autoresearch.harness.parametric_strategy import ITER31_DEFAULTS
    diffs = {k: v for k, v in s.get("params", {}).items() if ITER31_DEFAULTS.get(k) != v}
    if not diffs:
        print("    (identical to Iter31 defaults)")
    else:
        for k, v in sorted(diffs.items()):
            print(f"    {k:<24} {ITER31_DEFAULTS.get(k)!r:>10} -> {v!r}")


def list_snapshots():
    snap_dir = os.path.join(HARNESS_DIR, "snapshots")
    if not os.path.isdir(snap_dir):
        print("No snapshots dir.")
        return
    files = sorted(os.listdir(snap_dir))
    for f in files:
        if f.endswith(".json"):
            print(f"  {f[:-5]}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stop", action="store_true")
    p.add_argument("--status", action="store_true")
    p.add_argument("--report", nargs="?", const="", default=None,
                   help="Pretty-print stats for current best, or pass a snapshot label.")
    p.add_argument("--list-snapshots", action="store_true")
    args = p.parse_args()
    if args.stop:
        stop()
    elif args.status:
        status()
    elif args.list_snapshots:
        list_snapshots()
    elif args.report is not None:
        report(args.report or None)
    else:
        start()


if __name__ == "__main__":
    main()
