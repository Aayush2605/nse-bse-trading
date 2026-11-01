"""Run a skill module on the NYSE clock, for the logic tests whose fixtures are real
US market data (TSLA, Oct 2026). The bar handling, opening ranges, simulation, sizing
and risk rules are the same in any market; only the clock, the calendar, the symbol
form and the default limits differ. test_india.py tests those Indian parts.
"""

import datetime

NYSE_HOLIDAYS = {
    "2026-01-01": "New Year's Day", "2026-01-19": "Martin Luther King, Jr. Day",
    "2026-02-16": "Washington's Birthday", "2026-04-03": "Good Friday", "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth National Independence Day", "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day", "2026-11-26": "Thanksgiving Day", "2026-12-25": "Christmas Day",
    "2027-01-01": "New Year's Day", "2027-01-18": "Martin Luther King, Jr. Day",
    "2027-02-15": "Washington's Birthday", "2027-03-26": "Good Friday", "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth National Independence Day (observed)",
    "2027-07-05": "Independence Day (observed)", "2027-09-06": "Labor Day",
    "2027-11-25": "Thanksgiving Day", "2027-12-24": "Christmas Day (observed)",
}
NYSE_EARLY_CLOSE = {"2026-11-27": "day after Thanksgiving", "2026-12-24": "Christmas Eve",
                    "2027-11-26": "day after Thanksgiving"}
US_LIMITS = {"budget": None, "max_order_usd": 4000, "min_order_usd": 5, "max_loss_per_trade_usd": 50,
             "max_daily_loss_usd": 150, "no_entries_before": "09:45", "no_entries_after": "15:30",
             "flat_by": "15:55", "broker": "alpaca", "brokerage_per_order": 0, "brokerage_pct": 0}


def _nth_sunday(year, month, n):
    d = datetime.date(year, month, 1)
    d += datetime.timedelta(days=(6 - d.weekday()) % 7)
    return d + datetime.timedelta(weeks=n - 1)


def ny_offset(utc):
    y = utc.year
    start = datetime.datetime.combine(_nth_sunday(y, 3, 2), datetime.time(7, 0))
    end = datetime.datetime.combine(_nth_sunday(y, 11, 1), datetime.time(6, 0))
    return -4 if start <= utc.replace(tzinfo=None) < end else -5


def ny_to_utc(local):
    for off in (-4, -5):
        utc = local - datetime.timedelta(hours=off)
        if ny_offset(utc) == off:
            return utc
    return local + datetime.timedelta(hours=5)


def us_symbol(sym):
    return sym.upper().replace(".", "-")


def us_clock(mod):
    """Patch one loaded skill module to the NYSE clock and US defaults. Returns it."""
    def put(name, value):
        if hasattr(mod, name):
            setattr(mod, name, value)
    put("ist_offset", ny_offset)
    put("ist_to_utc", ny_to_utc)
    put("NSE_HOLIDAYS", dict(NYSE_HOLIDAYS))
    put("NSE_EARLY_CLOSE", dict(NYSE_EARLY_CLOSE))
    put("OPEN", datetime.time(9, 30))
    put("CLOSE", datetime.time(16, 0))
    put("SESSION_BARS", 78)
    put("OPEN_MIN", 9 * 60 + 30)
    put("CLOSE_MIN", 16 * 60)
    put("_yq", us_symbol)
    put("MAX_GAPS", 0)                                   # US data has no null bars to fill
    put("india_reasons", lambda *a, **k: ([], []))       # NSE market rules: test_india.py
    put("charges", lambda qty, buy, sell, c=None: dict.fromkeys(
        ("brokerage", "stt", "exchange", "sebi", "stamp", "gst", "total"), 0.0))   # Indian charges: test_india.py
    if hasattr(mod, "DEFAULTS"):
        for k, v in US_LIMITS.items():
            if k in mod.DEFAULTS:
                mod.DEFAULTS[k] = v
    return mod
