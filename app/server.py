#!/usr/bin/env python3
"""NSE BSE Trader: a local web app over the 11 skills. Standard library only.

    python3 app/server.py                 # opens http://127.0.0.1:8765 in your browser
    python3 app/server.py --port 9000 --folder ~/nse-trader --no-browser

It listens on your own computer only (127.0.0.1), runs the pack's own scripts
with checked inputs (never a shell, never free text), and keeps everything in
--folder/trader/ (default: ~/nse-trader). Paper trading: nothing is ever sent
to a broker from this app.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(APP)
SYMBOL = re.compile(r"^[A-Z0-9&][A-Z0-9&\-]{0,19}(\.(NS|BO))?$")
NOW = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
NIFTY50 = ("ADANIENT,ADANIPORTS,APOLLOHOSP,ASIANPAINT,AXISBANK,BAJAJ-AUTO,BAJFINANCE,BAJAJFINSV,BEL,BHARTIARTL,"
           "CIPLA,COALINDIA,DRREDDY,EICHERMOT,ETERNAL,GRASIM,HCLTECH,HDFCBANK,HDFCLIFE,HINDALCO,HINDUNILVR,"
           "ICICIBANK,INDIGO,INFY,ITC,JIOFIN,JSWSTEEL,KOTAKBANK,LT,M&M,MARUTI,MAXHEALTH,NESTLEIND,NTPC,ONGC,"
           "POWERGRID,RELIANCE,SBILIFE,SBIN,SHRIRAMFIN,SUNPHARMA,TATACONSUM,TMPV,TATASTEEL,TCS,TECHM,TITAN,"
           "TRENT,ULTRACEMCO,WIPRO")
TRADER_FILES = {"watchlist": "watchlist.json", "entry": "entry.json", "plan": "plan.json",
                "timemachine": "timemachine.json", "orders": "orders.json", "risk": "state/risk.json",
                "broker": "state/broker.json", "config": "config.json", "portfolio": "portfolio.json"}
LOCK = threading.Lock()  # one step at a time: the skills hand files to each other


class BadInput(Exception):
    pass


def script(skill, name):
    return os.path.join(ROOT, skill, name)


def symbol(v):
    s = str(v or "").strip().upper()
    if not SYMBOL.match(s):
        raise BadInput("that does not look like an NSE or BSE symbol: %r" % v)
    return s


def number(v, lo, hi, what):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise BadInput("%s must be a number" % what)
    if not lo <= x <= hi:
        raise BadInput("%s must be between %s and %s" % (what, lo, hi))
    return x


def clock(body):
    """["--now", "..."] for practice on a past session, else []."""
    v = str(body.get("now") or "").strip()
    if not v:
        return []
    if not NOW.match(v):
        raise BadInput("practice time must look like 2026-10-30 09:40")
    return ["--now", v]


def commands(step, body):
    """The scripts a step runs, in order: [[script, args...]]. Every value is checked here."""
    py = [sys.executable, "-I", "-X", "utf8"]  # utf8: Windows pipes would choke on the rupee sign
    now = clock(body)
    if step == "scan":
        cmd = py + [script("nse-scanner", "scan.py"), "daily" if body.get("mode") == "daily" else "orb"]
        if body.get("all"):
            return [py + [script("nse-scanner", "scan.py"), "universe"], cmd + now]
        syms = [symbol(s) for s in re.split(r"[,\s]+", str(body.get("symbols") or NIFTY50)) if s.strip()]
        if not syms or len(syms) > 300:
            raise BadInput("give 1 to 300 symbols, or tick 'all NSE and BSE stocks'")
        return [cmd + ["--symbols", ",".join(syms), "--min-price", "0"] + now]
    if step == "research":
        s = symbol(body.get("symbol"))
        return [py + [script("nse-news", "news.py"), "--tickers", s, "--hours", "72", "--all", "--dry-run", "--no-moves"],
                py + [script("nse-results", "results.py"), s, "--quarters", "4"],
                py + [script("nse-insider", "insider.py"), "--symbol", s, "--days", "90"]]
    if step == "plan":
        s = symbol(body.get("symbol"))
        r = {"1": "1R", "1.5": "1.5R", "2": "2R"}.get(str(body.get("target") or "1"), "1R")
        return [py + [script("nse-entry", "entry.py"), "check", s, "--write"] + now,
                py + [script("nse-exit", "exit.py"), "plan", "--from", "trader/entry.json", "--stop", "or-mid",
                      "--target", r, "--write"] + now,
                py + [script("nse-timemachine", "timemachine.py"), "run", "--write"]]
    if step == "size":
        budget = number(body.get("budget"), 1000, 1e9, "budget")
        return [py + [script("nse-budget", "size.py"), "--budget", "%.0f" % budget, "--write"] + now]
    if step == "check":
        cmds = []
        if body.get("refresh"):
            cmds.append(py + [script("nse-risk", "check.py"), "--refresh-rules"])
        return cmds + [py + [script("nse-risk", "check.py")] + now]
    if step == "ticket":
        return [py + [script("nse-broker", "ticket.py"), "show", "--index", "1"] + now]
    if step == "place":
        if body.get("confirm") != "yes":
            raise BadInput("placing needs your yes")
        return [py + [script("nse-broker", "ticket.py"), "approve", "--index", "1", "--reply", "yes"] + now,
                py + [script("nse-broker", "ticket.py"), "paper", "--index", "1"] + now]
    if step == "track":
        return [py + [script("nse-broker", "ticket.py"), "paper-check"] + now]
    raise BadInput("unknown step %r" % step)


def save_settings(folder, body):
    """Write the user's limits to trader/config.json, keeping anything else already there."""
    path = os.path.join(folder, "trader", "config.json")
    cfg = read_json(path) or {}
    for key, lo, hi in (("budget", 1000, 1e9), ("max_loss_per_trade_usd", 10, 1e7),
                        ("max_daily_loss_usd", 10, 1e7), ("max_trades_per_day", 1, 50)):
        if body.get(key) not in (None, ""):
            cfg[key] = number(body[key], lo, hi, key.replace("_usd", "").replace("_", " "))
    cfg["max_trades_per_day"] = int(cfg.get("max_trades_per_day", 3))
    cfg["paper"] = True  # this app never trades live
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    return cfg


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def snapshot(folder):
    """Every trader/ file the page draws from."""
    return {k: read_json(os.path.join(folder, "trader", f)) for k, f in TRADER_FILES.items()}


def run_step(folder, step, body):
    out = []
    with LOCK:
        for cmd in commands(step, body):
            try:
                p = subprocess.run(cmd, cwd=folder, capture_output=True, text=True, timeout=900,
                                   encoding="utf-8", errors="replace")
                code, text = p.returncode, (p.stdout + ("\n" + p.stderr if p.stderr.strip() else "")).strip()
            except subprocess.TimeoutExpired:
                code, text = -1, "This took longer than 15 minutes and was stopped."
            out.append({"tool": os.path.basename(next(c for c in cmd if c.endswith(".py"))), "code": code, "text": text})
    return {"step": step, "runs": out, "files": snapshot(folder)}


def make_handler(folder):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, body, kind="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                with open(os.path.join(APP, "index.html"), "rb") as fh:
                    return self.send(200, fh.read(), "text/html; charset=utf-8")
            if self.path == "/api/state":
                return self.send(200, {"files": snapshot(folder), "folder": folder,
                                       "now": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
            self.send(404, {"error": "not found"})

        def do_POST(self):
            # another website in your browser cannot drive this app: same-origin JSON only
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json" or \
                    self.headers.get("Origin") not in (None, "http://%s" % self.headers.get("Host")):
                return self.send(403, {"error": "refused"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0) or 0) or b"{}")
                if not isinstance(body, dict):
                    raise BadInput("expected a JSON object")
                step = self.path.rsplit("/", 1)[-1]
                if step == "settings":
                    return self.send(200, {"config": save_settings(folder, body), "files": snapshot(folder)})
                return self.send(200, run_step(folder, step, body))
            except BadInput as e:
                return self.send(400, {"error": str(e)})
            except ValueError:
                return self.send(400, {"error": "that request was not valid JSON"})
    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description="NSE BSE Trader: the 11 skills behind buttons, on your computer.")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--folder", default=os.path.join(os.path.expanduser("~"), "nse-trader"),
                    help="where trader/ lives (default ~/nse-trader)")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args(argv)
    folder = os.path.abspath(os.path.expanduser(a.folder))
    os.makedirs(os.path.join(folder, "trader"), exist_ok=True)
    if not os.path.exists(os.path.join(folder, "trader", "config.json")):
        save_settings(folder, {"budget": 50000})
    server = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(folder))
    url = "http://127.0.0.1:%d" % a.port
    print("NSE BSE Trader is running at %s (your files: %s). Close this window to stop it." % (url, folder))
    if not a.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
