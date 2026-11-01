#!/usr/bin/env python3
"""Quarterly results for nse-results. Standard library only.

Reads a company's quarterly results from its NSE filings (SEBI's Integrated
Filing, Financials) and sums up what changed: revenue, net profit and EPS for
the last quarters, with quarter-on-quarter and year-on-year growth.

    python3 results.py TCS                    # consolidated, last 5 quarters
    python3 results.py ICICIBANK --standalone
    python3 results.py INFY --quarters 8 --json
    python3 results.py TCS --offline DIR      # filings.json and <qe_Date>.xml from DIR

Sources:
  - the filings list: https://www.nseindia.com/api/integrated-filing-results?symbol=<SYM>&type=Integrated%20Filing-%20Financials
  - each quarter's XBRL (Ind AS taxonomy), linked from that list. The "OneD"
    context is the quarter itself. Revenue is RevenueFromOperations (banks:
    InterestEarned, then TotalIncome), profit is ProfitLossForPeriod, EPS is
    basic EPS from continuing operations.

Amounts print in rupees crore (1 crore = 10 million). Numbers are what the
company filed; read the filing before acting. Not financial advice.
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request

LIST_URL = ("https://www.nseindia.com/api/integrated-filing-results?symbol=%s"
            "&type=Integrated%%20Filing-%%20Financials")
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}  # what NSE's edge answers from a script
CRORE = 1e7
REVENUE_TAGS = ("RevenueFromOperations", "InterestEarned", "TotalIncome", "Income")
PROFIT_TAGS = ("ProfitLossForPeriod", "ProfitLossForThePeriod")
EPS_TAGS = ("BasicEarningsLossPerShareFromContinuingOperations", "BasicEarningsLossPerShare",
            "BasicEarningsPerShareAfterExtraordinaryItems")


class ResultsError(Exception):
    pass


def fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        raise ResultsError("could not read %s: %s" % (url, e))


def nse_symbol(sym):
    s = sym.upper()
    if s.endswith(".BO"):
        raise ResultsError("%s is BSE-only: this tool reads NSE filings" % sym)
    s = s[:-3] if s.endswith(".NS") else s
    return s[:-3] if s.endswith("-SM") else s


def pick_filings(rows, standalone=False, n=5):
    """One filing per quarter, newest first: consolidated unless asked (or there is none), latest revision."""
    want = "Standalone" if standalone else "Consolidated"
    by_q = {}
    for r in rows:
        try:
            q = datetime.datetime.strptime(r.get("qe_Date") or "", "%d-%b-%Y").date()
        except ValueError:
            continue
        if not str(r.get("xbrl", "")).endswith(".xml"):
            continue
        rank = (r.get("consolidated") == want, r.get("broadcast_Date") or "")
        if q not in by_q or rank > by_q[q][0]:
            by_q[q] = (rank, r)
    return [(q, by_q[q][1]) for q in sorted(by_q, reverse=True)[:n]]


def quarter_facts(xml):
    """XBRL text -> {"revenue", "profit", "eps"} for the quarter (the OneD context)."""
    def first(tags):
        for t in tags:
            m = re.search(r"<[\w-]+:%s\b[^>]*contextRef=\"OneD\"[^>]*>\s*([-\d.]+)\s*<" % t, xml)
            if m:
                return float(m.group(1))
        return None
    return {"revenue": first(REVENUE_TAGS), "profit": first(PROFIT_TAGS), "eps": first(EPS_TAGS)}


def label(q):
    """2026-09-30 -> 'Q2 FY27' (India's financial year starts in April)."""
    fy = q.year + 1 if q.month >= 4 else q.year
    return "Q%d FY%02d" % ({6: 1, 9: 2, 12: 3, 3: 4}.get(q.month, 0), fy % 100)


def growth(a, b):
    return None if a is None or not b else round((a / b - 1) * 100, 1)


def summarize(quarters):
    """[(date, facts, kind)] newest first -> rows with QoQ and YoY growth."""
    out = []
    for i, (q, f, kind) in enumerate(quarters):
        prev = quarters[i + 1][1] if i + 1 < len(quarters) else {}
        yago = next((g for d, g, _ in quarters if d.month == q.month and d.year == q.year - 1), {})
        out.append({"quarter": label(q), "end": q.isoformat(), "basis": kind,
                    "revenue_cr": None if f["revenue"] is None else round(f["revenue"] / CRORE, 2),
                    "profit_cr": None if f["profit"] is None else round(f["profit"] / CRORE, 2),
                    "eps": f["eps"],
                    "revenue_qoq": growth(f["revenue"], prev.get("revenue")),
                    "profit_qoq": growth(f["profit"], prev.get("profit")),
                    "revenue_yoy": growth(f["revenue"], yago.get("revenue")),
                    "profit_yoy": growth(f["profit"], yago.get("profit"))})
    return out


def fmt(v, pct=False):
    if v is None:
        return "-"
    return "%+.1f%%" % v if pct else "{:,.2f}".format(v)


def report(sym, rows):
    lines = ["%s quarterly results (%s, from its NSE filings), rupees crore:" % (sym, rows[0]["basis"].lower()),
             "  %-8s %14s %8s %8s %14s %8s %8s %8s" % ("quarter", "revenue", "QoQ", "YoY", "net profit", "QoQ",
                                                       "YoY", "EPS")]
    for r in rows:
        lines.append("  %-8s %14s %8s %8s %14s %8s %8s %8s" % (
            r["quarter"], fmt(r["revenue_cr"]), fmt(r["revenue_qoq"], 1), fmt(r["revenue_yoy"], 1),
            fmt(r["profit_cr"]), fmt(r["profit_qoq"], 1), fmt(r["profit_yoy"], 1), fmt(r["eps"])))
    r = rows[0]
    said = []
    for what, k in (("Revenue", "revenue"), ("Net profit", "profit")):
        if r[k + "_yoy"] is not None:
            said.append("%s %s year on year" % (what.lower() if said else what,
                                                 ("up %.1f%%" if r[k + "_yoy"] >= 0 else "down %.1f%%") % abs(r[k + "_yoy"])))
    if said:
        lines.append("What changed in %s: %s." % (r["quarter"], ", ".join(said)))
    lines.append("Numbers as filed; read the filing before acting. Not financial advice.")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Quarterly results from NSE filings (nse-results).")
    ap.add_argument("symbol")
    ap.add_argument("--quarters", type=int, default=5)
    ap.add_argument("--standalone", action="store_true", help="standalone instead of consolidated")
    ap.add_argument("--offline", metavar="DIR", help="filings.json and <YYYY-MM-DD>.xml files")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        sym = nse_symbol(a.symbol)
        if a.offline:
            with open(os.path.join(a.offline, "filings.json"), encoding="utf-8") as fh:
                doc = json.load(fh)
        else:
            doc = json.loads(fetch(LIST_URL % urllib.parse.quote(sym)))
        rows = doc.get("data", []) if isinstance(doc, dict) else doc
        picks = pick_filings(rows, a.standalone, a.quarters + 4)  # 4 more for year-on-year growth
        if not picks:
            raise ResultsError("no quarterly results filed on NSE for %s" % sym)
        quarters = []
        for q, r in picks:
            if a.offline:
                with open(os.path.join(a.offline, q.isoformat() + ".xml"), encoding="utf-8") as fh:
                    xml = fh.read()
            else:
                xml = fetch(r["xbrl"])
            quarters.append((q, quarter_facts(xml), r.get("consolidated") or "Standalone"))
        rows = summarize(quarters)[:a.quarters]
    except ResultsError as e:
        print("results.py: %s" % e, file=sys.stderr)
        return 1
    print(json.dumps({"symbol": sym, "quarters": rows}, indent=2) if a.json else report(sym, rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
