# NSE BSE Trading skills

11 Claude skills for day trading Indian stocks on NSE and BSE: scan every listed stock, track news, time entries and exits, count Indian charges, and replay every outcome before you risk a rupee.

Free, MIT, no signup, no API key. The tools are plain Python that read free public data: NSE and BSE listing files, Yahoo Finance charts (`.NS` and `.BO`), NSE corporate announcements, results and insider disclosures, and Google News India.

One scans every listed stock (about 5,000 on NSE and BSE) for setups. Another tracks the news and the company's own NSE filings. One watches a setup bar by bar and tells you the moment to get in, and another sets your stop and your target before you do. The Time Machine replays the rest of the session 10,000 times from the stock's own recent bars, plus every past day the same setup fired, and tells you the honest odds. Position sizing counts brokerage, STT, exchange fees, SEBI fees, stamp duty and GST, and the risk check knows circuit limits, NSE's ASM/GSM lists and trade-for-trade stocks.

And no trade goes through until you say yes. Paper trading is the default and is simulated here: nothing reaches your broker until you turn it off yourself.

> Ported to Indian markets from Jake Schincariol's [day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) (MIT), which covers US markets.

## Install

Paste this into Claude:

```
https://github.com/Aayush2605/nse-bse-trading

install skill
```

Or as a plugin, in Claude Code:

```
/plugin marketplace add Aayush2605/nse-bse-trading
/plugin install nse-bse-trading@nse-bse-trading
```

Claude Code namespaces plugin skills, so installed as a plugin they show up as `/nse-bse-trading:nse-scanner` and so on. Copy the folders instead if you want plain `/nse-scanner`:

```
git clone https://github.com/Aayush2605/nse-bse-trading.git
cp -r nse-bse-trading/nse-* ~/.claude/skills/
```

The tools need Python 3.8 or newer. Nothing to pip install.

## The eleven

| command | job | what it does |
| --- | --- | --- |
| `/nse-scanner` | Chart Scanner | Scans every NSE and BSE stock for setups: opening-range breakouts, flags, oversold bounces. |
| `/nse-news` | News Monitor | Indian headlines and the company's own NSE announcements for every stock you watch. |
| `/nse-entry` | Entry Timer | Watches a setup bar by bar and tells you the moment to get in. |
| `/nse-exit` | Exit Planner | Sets your stop and your target before you enter, out by 3:15 PM. |
| `/nse-timemachine` | Time Machine | Replays every possible outcome of a trade: 10,000 simulated sessions plus every past time the setup fired. |
| `/nse-risk` | Risk Manager | Checks every trade against your limits, circuit limits, ASM/GSM and T2T, and stops anything over them. |
| `/nse-budget` | Budget Manager | Sizes every position to your budget and your max loss, after Indian charges. |
| `/nse-broker` | Order Executor | Paper trades here by default; Zerodha Kite when you go live, never without your yes. |
| `/nse-alerts` | Price Alerts | Rings when a price, a stop, the target or the 9:15 opening bell hits. |
| `/nse-results` | Results Analyst | Reads quarterly results from NSE filings and sums up what changed. |
| `/nse-insider` | Insider Tracker | Promoter and director trades (SEBI PIT) and the day's bulk and block deals. |

## How to use it

Everything lands in a `trader/` folder in your project, and each skill reads what the last one wrote:

```
scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker   (one trade)
alerts: stop, target, flat by 3:15 PM                                          (while it is open)
news / results / insider                                                       (on a schedule)
```

An example with real data: ICICI Bank, Friday 30 October 2026.

1. **`/nse-scanner`** at 10:15 AM: of ten large stocks, ICICIBANK, TCS and BAJAJ-AUTO had closed above their 15-minute opening range. ICICIBANK's range was 1383.40 to 1390.90.
2. **`/nse-news`**: an ESOP allotment filing on NSE, weekend headlines on foreign ownership; no results or board meeting that week.
3. **`/nse-entry`**: at 9:35 AM it said triggered: the 9:30 bar closed at 1394.50, above the range.
4. **`/nse-exit`**: stop at the range's midpoint, 1387.15, so 7.35 a share at risk; target one times that risk, 1401.85; flat by 3:15 PM either way.
5. **`/nse-timemachine`**: 10,000 replays from ICICIBANK's last 59 sessions gave target first 41 %, stop first 53 %. The same rule on those 59 real days fired 37 times: 13 targets, 21 stops. Its verdict: leans toward the stop. That is the point of looking first.
6. **`/nse-budget`** with Rs 50,000 and the default limits: 26 shares (Rs 36,257). Charges for the round trip about Rs 38: net loss at the stop Rs 229.52, net gain at the target Rs 152.45.
7. **`/nse-risk`**: max loss, daily loss, trades per day, reward to risk, the entry window, circuit limits, ASM/GSM, T2T. PASS or BLOCK, with the reason.
8. **`/nse-broker`**: shows the ticket. You type yes. In paper mode it fills here; `paper-check` closed it at the target at 11:50 AM.

## The tools

All standard-library Python. The data tools read public endpoints and are polite about it.

```
python3 nse-scanner/scan.py universe                                   # ~5,000 NSE + BSE stocks
python3 nse-scanner/scan.py daily                                      # daily setups, whole universe
python3 nse-scanner/scan.py orb --at 10:15                             # opening-range breakouts so far
python3 nse-news/news.py --tickers ICICIBANK --hours 12                # headlines, NSE filings, today's move
python3 nse-entry/entry.py check ICICIBANK --setup orb                 # waiting / triggered / expired
python3 nse-exit/exit.py plan --stop or-mid --target 1R --write        # -> trader/plan.json
python3 nse-timemachine/timemachine.py run --write                     # 10,000 replays + the history
python3 nse-budget/size.py --write                                     # -> trader/orders.json, with charges
python3 nse-risk/check.py --refresh-rules                              # NSE bands, ASM/GSM, once a day
python3 nse-risk/check.py                                              # PASS / BLOCK per order
python3 nse-broker/ticket.py show                                      # the tickets, READY or not
python3 nse-broker/ticket.py paper --index 1                           # paper fill
python3 nse-broker/ticket.py paper-check                               # stop / target / flat by
python3 nse-alerts/alerts.py add --from-plan                           # stop, target, flat by
python3 nse-results/results.py TCS                                     # quarters, growth, EPS
python3 nse-insider/insider.py --symbol RELIANCE                       # insider trades
```

```
python3 -m unittest discover -s tests -v
```

The tests run offline. `tests/test_india.py` checks the Indian parts on real NSE and BSE data: the IST clock and NSE holidays, the symbol forms, the universe, the charges, circuit limits and surveillance, Kite orders and paper fills, and the news, results and insider sources. The other test files check the market-independent logic (bars, opening ranges, the simulation, sizing, risk rules) on the original pack's real US data, run on a New York clock by `tests/_us_clock.py`.

## Fine print

**Not financial advice.** This is software that reads public data and does arithmetic. It does not know your situation and it cannot see the future. SEBI's own study found that most individual intraday traders in equity cash lose money. You can lose money. Decide for yourself, and talk to a SEBI-registered adviser if you need advice.

**No trade goes through until you say yes.** Only `/nse-broker` can lead to an order, and only after `/nse-risk` passes that exact order and you type yes for it in the chat. Live, set the Kite order tools to "Needs approval" in Claude, never "Always allow", so Claude's own "Allow once / Deny" card is a second check.

**Paper first.** `"paper": true` is the default in `config.example.json`, and paper orders are filled here, never sent to Zerodha.

**SEBI's retail algo rules.** Since 1 April 2026, orders placed through a broker's API must come from a static IP you registered with your broker, and carry the exchange's algo ID. Scanning, alerts and paper trading need none of that; live orders do.

**Intraday (MIS) only, equity only.** Brokers square off MIS positions themselves around 3:15 to 3:20 PM and charge for it, so the pack is flat by 3:15. Trade-for-trade (T2T) stocks cannot be traded intraday and are blocked. A stock locked at its lower circuit has no buyers, so a stop there may never fill. No F&O, delivery, margin or short selling.

**The Time Machine is a simulation, not a prediction.** It is built from the stock's own last 60 days of 5-minute bars. Results, a SEBI order or a block deal can do things those days never did.

**The data is free and unofficial.** Yahoo Finance's chart endpoint and NSE's website APIs are not official APIs: they can lag, change or refuse you. Yahoo's NSE bars miss a bar or two most days. Check anything that matters against your broker before you act on it.

**Charges change.** The rates in `nse-budget/size.py` are Zerodha's intraday equity rates as of November 2026. Check them after each Union Budget.

**Insider disclosures are public, not a tip.** They are filed after the trade under SEBI's PIT rules.

**Taxes.** Intraday equity gains are speculative business income in India, taxed at your slab rate. Nothing here is tax advice.

## Files

```
nse-scanner/     SKILL.md, scan.py
nse-news/        SKILL.md, news.py
nse-entry/       SKILL.md, entry.py
nse-exit/        SKILL.md, exit.py
nse-timemachine/ SKILL.md, timemachine.py
nse-risk/        SKILL.md, check.py
nse-budget/      SKILL.md, size.py, config.example.json, targets.example.json
nse-broker/      SKILL.md, ticket.py, claude_desktop_config.example.json
nse-alerts/      SKILL.md, alerts.py, alerts.example.json
nse-results/     SKILL.md, results.py
nse-insider/     SKILL.md, insider.py
tests/           unittest suite + offline fixtures
```

MIT. Ported to NSE and BSE by [Aayush Mehta](https://github.com/Aayush2605), from the original by [Jake Schincariol](https://opusjake.ai).
