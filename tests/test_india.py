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
size = load("trader-budget", "size")

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

    def test_universe_is_every_nse_and_bse_stock_once(self):
        texts = []
        for f in ("EQUITY_L.csv", "SME_EQUITY_L.csv", "bse.csv"):
            with open(os.path.join(IDIR, f), encoding="utf-8") as fh:
                texts.append(fh.read())
        kept, counts = scan.build_universe(*texts)
        tag = {s: t for s, _, t in kept}
        self.assertEqual(tag["RELIANCE"], "NSE EQ")                         # on both: kept once, NSE symbol
        self.assertNotIn("RELIANCE.BO", tag)
        self.assertEqual(tag["3IINFOLTD"], "NSE BE T2T")                    # listed, but delivery only
        self.assertEqual(tag["RAVITA-SM.NS"], "NSE ST T2T")                 # NSE SME, Yahoo's form
        self.assertEqual(tag["ABB.BO"], "BSE A")                            # BSE-only in this cut
        self.assertEqual(tag["BHAGGAS.BO"], "BSE XT T2T")
        self.assertNotIn("LIQUIDETF.BO", tag)                               # funds are not stocks
        self.assertNotIn("NIF100BEES.BO", tag)
        self.assertEqual(counts["keep"], 15)


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


class Charges(unittest.TestCase):
    PLAN = {"symbol": "ICICIBANK", "entry": 1394.50, "stop": 1387.15, "target": 1401.85}

    def test_round_trip_by_hand(self):
        # 100 x 1000 -> 1010: brokerage 20+20, STT 25.25, exchange 6.17, SEBI 0.20, stamp 3.00, GST 8.35
        self.assertEqual(size.charges(100, 1000, 1010)["total"], 82.97)
        self.assertEqual(size.charges(1, 100, 101)["brokerage"], 0.06)       # 0.03% beats Rs 20

    def test_max_loss_counts_the_charges(self):
        s = size.size_trade(self.PLAN, {"max_order_usd": 10 ** 7, "max_position_pct": 100, "cash_buffer_pct": 0},
                            budget=10 ** 6)
        self.assertLess(s["qty"], 68)                                         # 500 / 7.35 = 68 before charges
        self.assertLessEqual(s["net_loss"], 500)
        self.assertGreater(size.size_trade(dict(self.PLAN), {}, budget=10 ** 6)["net_profit"], 0)

    def test_charges_that_eat_the_profit_refuse(self):
        tiny = dict(self.PLAN, stop=1394.00, target=1394.60)
        s = size.size_trade(tiny, {"max_order_usd": 3000, "min_order_usd": 0}, budget=50000)
        self.assertIn("charges", s["refusal"])


class MarketRules(unittest.TestCase):
    RULES = {"prev_close_date": "2026-10-30", "stocks": {
        "ABAN": {"series": "BE", "band_pct": 2.0, "t2t": True, "prev_close": 14.38},
        "21STCENMGM": {"series": "EQ", "band_pct": 5.0, "surveillance": "LTASM - Stage I", "prev_close": 40.0},
        "ABANSENT": {"series": "EQ", "band_pct": 5.0, "prev_close": 26.79},
        "ICICIBANK": {"series": "EQ", "band_pct": None, "prev_close": 1390.0},
        "AXIOMGAS-SM.NS": {"series": "SM", "band_pct": 5.0, "t2t": True}}}

    def why(self, sym, ref, stop, **cfg):
        c = dict(risk.DEFAULTS, **cfg)
        return risk.india_reasons(sym, ref, stop, self.RULES, c, "2026-11-02")

    def test_t2t_surveillance_and_circuits_block(self):
        self.assertTrue(self.why("ABAN.NS", 14.38, 14.0)[0][0].startswith("t2t:"))
        self.assertTrue(self.why("AXIOMGAS-SM.NS", 50, 49)[0][0].startswith("t2t:"))
        self.assertTrue(self.why("21STCENMGM", 40, 39)[0][0].startswith("surveillance:"))
        self.assertEqual(self.why("21STCENMGM", 40, 39, allow_surveillance=True)[0], [])
        self.assertTrue(self.why("ABANSENT", 28.00, 27.5)[0][0].startswith("circuit: entry"))   # upper 28.13
        self.assertTrue(self.why("ABANSENT", 26.79, 25.40)[0][0].startswith("circuit: stop"))   # lower 25.45
        self.assertEqual(self.why("ABANSENT", 26.79, 26.0)[0], [])

    def test_fno_stocks_and_missing_rules_only_warn(self):
        r, w = self.why("ICICIBANK.NS", 1394.5, 1387.15)
        self.assertEqual(r, [])
        self.assertIn("no fixed price band", w[0])
        r, w = risk.india_reasons("RELIANCE", 1, 0.9, None, risk.DEFAULTS, "2026-11-02")
        self.assertEqual(r, [])
        self.assertIn("--refresh-rules", w[0])

    def test_stale_rules_warn(self):
        rules = dict(self.RULES, prev_close_date="2026-10-28")
        w = risk.india_reasons("ABANSENT", 26.79, 26.0, rules, risk.DEFAULTS, "2026-11-02")[1]
        self.assertIn("refresh", w[0])


if __name__ == "__main__":
    unittest.main()
