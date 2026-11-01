#!/usr/bin/env python3
"""Insider trades and big deals for nse-insider. Standard library only.

Under SEBI's insider-trading rules (PIT), promoters, directors and key staff
must disclose their trades in their company's shares within days. NSE posts
those disclosures, and every bulk and block deal of the day. This tool reads
both, newest first.

    python3 insider.py --symbol RELIANCE            # one company's insider trades
    python3 insider.py                              # your watchlist + plan + portfolio, last 30 days
    python3 insider.py --deals                      # today's bulk and block deals, whole market
    python3 insider.py --symbol TCS --days 90 --market-only --json

Sources:
  - https://www.nseindia.com/api/corporates-pit?index=equities&symbol=<SYM>
  - https://www.nseindia.com/api/snapshot-capital-market-largedeal

--market-only keeps buys and sells made on the market (it drops gifts,
transfers, pledges and ESOP allotments, which say little about a view).
Disclosures are public information filed after the fact, not a tip.
Not financial advice.
"""

import argparse
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

PIT_URL = "https://www.nseindia.com/api/corporates-pit?index=equities&symbol=%s"
DEALS_URL = "https://www.nseindia.com/api/snapshot-capital-market-largedeal"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}  # what NSE's edge answers from a script


class InsiderError(Exception):
    pass


def get_json(url, offline=None, name=None):
    if offline:
        with open(os.path.join(offline, name), encoding="utf-8") as fh:
            return json.load(fh)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        raise InsiderError("could not read %s: %s" % (url, e))


def nse_symbol(sym):
    s = sym.upper()
    if s.endswith(".BO"):
        return None
    s = s[:-3] if s.endswith(".NS") else s
    return s[:-3] if s.endswith("-SM") else s


def _num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def parse_pit(doc, since=None, market_only=False):
    """corporates-pit JSON -> trades, newest first."""
    out = []
    for r in (doc or {}).get("data") or []:
        try:
            filed = datetime.datetime.strptime(r.get("date", ""), "%d-%b-%Y %H:%M")
        except ValueError:
            continue
        if since and filed.date() < since:
            continue
        mode = (r.get("acqMode") or "").strip()
        on_market = "market" in mode.lower() and "off" not in mode.lower()
        if market_only and not on_market:
            continue
        qty, val = _num(r.get("secAcq")), _num(r.get("secVal"))
        out.append({"symbol": r.get("symbol"), "company": r.get("company"), "filed": filed.isoformat(" "),
                    "person": (r.get("acqName") or "").strip(), "category": r.get("personCategory") or "",
                    "side": (r.get("tdpTransactionType") or "").strip() or "-", "qty": qty, "value": val,
                    "price": round(val / qty, 2) if qty else None, "mode": mode,
                    "from": r.get("acqfromDt"), "to": r.get("acqtoDt"),
                    "holding_after_pct": _num(r.get("afterAcqSharesPer")), "link": r.get("xbrl") or ""})
    out.sort(key=lambda t: t["filed"], reverse=True)
    return out


def parse_deals(doc, symbols=None):
    """largedeal snapshot -> (as_on, deals). symbols: keep only these (bare NSE symbols)."""
    deals = []
    for kind, key in (("bulk", "BULK_DEALS_DATA"), ("block", "BLOCK_DEALS_DATA")):
        for r in (doc or {}).get(key) or []:
            if symbols and str(r.get("symbol", "")).upper() not in symbols:
                continue
            qty, px = _num(r.get("qty")), _num(r.get("watp"))
            deals.append({"kind": kind, "symbol": r.get("symbol"), "company": r.get("name"),
                          "client": r.get("clientName"), "side": r.get("buySell"), "qty": qty, "price": px,
                          "value": round(qty * px, 2)})
    deals.sort(key=lambda d: -d["value"])
    return (doc or {}).get("as_on_date"), deals


def crore(v):
    return "Rs %s cr" % "{:,.2f}".format(v / 1e7)


def watch_symbols(watchlist, plan, portfolio):
    syms = []

    def load(p):
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}
    for h in load(watchlist).get("hits", []):
        syms.append(h.get("symbol") or "")
    syms.append(load(plan).get("symbol") or "")
    for p in load(portfolio).get("positions", []):
        syms.append(p.get("ticker") or p.get("symbol") or "")
    out = []
    for s in syms:
        n = nse_symbol(s) if s else None
        if n and n not in out:
            out.append(n)
    return out


def report_trades(trades, title):
    lines = [title]
    if not trades:
        lines.append("  none")
    for t in trades:
        lines.append("  %s  %-10s %-4s %s shares at ~%s (%s), %s  %s (%s), %s"
                     % (t["filed"][:10], t["symbol"], t["side"].upper()[:4], "{:,.0f}".format(t["qty"]),
                        "%.2f" % t["price"] if t["price"] else "-", crore(t["value"]), t["mode"] or "-",
                        t["person"], t["category"] or "-", "holds %.2f%% after" % t["holding_after_pct"]))
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="Insider trades (SEBI PIT) and bulk/block deals (nse-insider).")
    ap.add_argument("--symbol", nargs="*", help="NSE symbols (default: watchlist + plan + portfolio)")
    ap.add_argument("--days", type=int, default=30, help="disclosures filed in the last N days")
    ap.add_argument("--market-only", action="store_true", help="only market buys and sells")
    ap.add_argument("--deals", action="store_true", help="today's bulk and block deals (whole market, or --symbol)")
    ap.add_argument("--watchlist", default="trader/watchlist.json")
    ap.add_argument("--plan", default="trader/plan.json")
    ap.add_argument("--portfolio", default="trader/portfolio.json")
    ap.add_argument("--offline", metavar="DIR", help="pit-<SYM>.json and deals.json from DIR")
    ap.add_argument("--now", help="YYYY-MM-DD, for reproducible runs")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    today = datetime.date.fromisoformat(a.now) if a.now else datetime.date.today()
    since = today - datetime.timedelta(days=a.days)
    try:
        if a.symbol:
            syms = [nse_symbol(s) for s in a.symbol]
            syms = [s for s in syms if s]
        else:
            syms = watch_symbols(a.watchlist, a.plan, a.portfolio)
        if a.deals:
            as_on, deals = parse_deals(get_json(DEALS_URL, a.offline, "deals.json"), set(syms) if a.symbol else None)
            if a.json:
                print(json.dumps({"as_on": as_on, "deals": deals}, indent=2))
                return 0
            print("Bulk and block deals on NSE, %s (largest first):" % as_on)
            for d in deals[:40] or []:
                print("  %-5s %-12s %-4s %s at %.2f = %s  %s" % (d["kind"], d["symbol"], d["side"],
                                                                   "{:,.0f}".format(d["qty"]), d["price"],
                                                                   crore(d["value"]), d["client"]))
            if not deals:
                print("  none")
            print("A bulk deal is over 0.5% of a company's shares in a day; a block deal is one big trade "
                  "in the block window. Not financial advice.")
            return 0
        if not syms:
            raise InsiderError("no symbols: pass --symbol, or run /nse-scanner first (trader/watchlist.json)")
        all_trades = {}
        for s in syms:
            doc = get_json(PIT_URL % urllib.parse.quote(s), a.offline, "pit-%s.json" % s)
            all_trades[s] = parse_pit(doc, since, a.market_only)
    except InsiderError as e:
        print("insider.py: %s" % e, file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps(all_trades, indent=2))
        return 0
    for s in syms:
        print("\n".join(report_trades(all_trades[s], "%s: insider trades filed since %s%s" % (
            s, since.isoformat(), " (market buys and sells only)" if a.market_only else ""))))
    print("Disclosures are filed after the trade (SEBI PIT): public information, not a tip. Not financial advice.")
    return 0 if any(all_trades.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
