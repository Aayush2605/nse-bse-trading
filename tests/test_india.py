"""India (NSE) port checks, on real data cut on 2026-11-01:

india/ICICIBANK-2026-10-30-5m.json  Yahoo v8 chart, ICICIBANK.NS, Fri Oct 30 2026, 75 five-minute bars
india/EQUITY_L.csv                  rows from NSE's EQUITY_L.csv (EQ and BE series)
"""

import datetime
import json
import os
import unittest

from _load import load, FIX

scan = load("trader-scanner", "scan")
entry = load("trader-entry", "entry")
exitp = load("trader-exit", "exit")
risk = load("trader-risk", "check")
tm = load("trader-timemachine", "timemachine")

IDIR = os.path.join(FIX, "india")
ICICI = os.path.join(IDIR, "ICICIBANK-2026-10-30-5m.json")
DT = datetime.datetime


class Clock(unittest.TestCase):
    def test_ist_has_no_daylight_saving(self):
        for mod in (scan, entry, exitp, risk, tm):
            self.assertEqual(mod.to_ist(DT(2026, 1, 5, 3, 45)), DT(2026, 1, 5, 9, 15))
            self.assertEqual(mod.to_ist(DT(2026, 7, 6, 3, 45)), DT(2026, 7, 6, 9, 15))
            self.assertEqual(mod.ist_to_utc(DT(2026, 10, 30, 15, 30)), DT(2026, 10, 30, 10, 0))

    def test_session_and_holidays(self):
        self.assertEqual(scan.session(datetime.date(2026, 10, 30)), (datetime.time(9, 15), datetime.time(15, 30)))
        self.assertIsNone(scan.session(datetime.date(2026, 11, 10)))       # Diwali Balipratipada
        self.assertIsNone(scan.session(datetime.date(2026, 10, 31)))       # Saturday
        self.assertIn("NSE holiday", scan.trading_day(datetime.date(2026, 11, 24))[1])

    def test_risk_window_defaults(self):
        self.assertEqual(risk.DEFAULTS["no_entries_before"], "09:30")
        self.assertEqual(risk.DEFAULTS["flat_by"], "15:15")


class Symbols(unittest.TestCase):
    def test_yahoo_suffix(self):
        self.assertEqual(scan.to_yahoo("reliance"), "RELIANCE.NS")
        self.assertEqual(entry.yahoo_symbol("TCS.BO"), "TCS.BO")
        self.assertEqual(scan.to_yahoo("^NSEI"), "^NSEI")
        self.assertIn("M%26M.NS", scan.spark_path(["M&M", "BAJAJ-AUTO"], "1d", "5m"))

    def test_nse_tickers_pass_the_checks(self):
        for t in ("RELIANCE", "M&M", "BAJAJ-AUTO", "20MICRONS", "ICICIBANK.NS", "TCS.BO"):
            self.assertTrue(risk.TICKER.match(t), t)

    def test_universe_keeps_eq_only(self):
        with open(os.path.join(IDIR, "EQUITY_L.csv"), encoding="utf-8") as fh:
            kept, counts = scan.build_universe(fh.read())
        syms = [s for s, _ in kept]
        self.assertIn("M&M", syms)
        self.assertIn("RELIANCE", syms)
        self.assertNotIn("3IINFOLTD", syms)                                 # BE series
        self.assertEqual(counts["keep"], 7)


class RealSession(unittest.TestCase):
    def test_orb_triggers_on_the_first_close_above_the_range(self):
        with open(ICICI) as fh:
            ch = entry.parse_chart(fh.read(), "ICICIBANK")
        res = entry.evaluate(ch, entry.parse_now("2026-10-30 09:40"))
        self.assertEqual(res["status"], "triggered")
        self.assertAlmostEqual(res["level"], 1390.9, places=2)
        self.assertAlmostEqual(res["trigger"]["price"], 1394.5, places=2)

    def test_time_machine_fills_a_null_bar(self):
        bars = [{"date": "2026-10-29", "slot": i, "start": "x", "o": 1, "h": 1, "l": 1, "c": 1.0 + i, "v": 1}
                for i in range(tm.SESSION_BARS) if i != 40]
        full, short = tm.full_sessions(tm.split_sessions(bars), "2026-10-30")
        self.assertEqual((len(full), short), (1, []))
        self.assertEqual(full[0][1][40]["c"], 40.0)                         # last close carried
        too_short = [b for b in bars if b["slot"] < 60]
        self.assertEqual(tm.full_sessions(tm.split_sessions(too_short), "2026-10-30")[0], [])


if __name__ == "__main__":
    unittest.main()
