---
name: nse-entry
description: >-
  Entry Timer. Watches a setup bar by bar and tells you the moment to get in.
  Reads free Yahoo 1-minute or 5-minute bars, builds the opening range (the
  first 15 minutes by default) and calls the entry on the first completed bar
  that CLOSES above the range high, or above a level you give it (like a
  20-day high from the scanner), with an optional volume check. Says waiting
  and how far, triggered with the time and the price, expired, or not open
  yet, and writes trader/entry.json for /nse-exit. Long side only. It never
  places an order. Use when the user says "tell me when to get in", "watch
  ICICIBANK", "has it broken out", "did it break the opening range", "entry
  signal", "time my entry", "check my watchlist", or after /nse-scanner
  and /nse-news, before /nse-exit.
argument-hint: "[TICKER] [--setup orb|level] [--interval 5m|1m]"
---

# nse-entry

The Entry Timer turns a setup into one moment: the bar that confirms it. It
reads bars, 1-minute or 5-minute, and waits for each one to finish. A price
that pokes above the high in the middle of a bar is not an entry. A bar that
CLOSES above it is. Then it says the time and the price, writes them down for
the Exit Planner, and stops. It never buys anything. Day trading loses most
people money, and a clean signal does not change that.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/entry.py" check ICICIBANK             # 15-minute opening range, 5-minute bars
python3 "${CLAUDE_SKILL_DIR}/entry.py" check ICICIBANK --write     # also save trader/entry.json
python3 "${CLAUDE_SKILL_DIR}/entry.py" check ICICIBANK --setup level --level 1400
python3 "${CLAUDE_SKILL_DIR}/entry.py" check ICICIBANK --interval 1m --min-volume-x 1.5
python3 "${CLAUDE_SKILL_DIR}/entry.py" watch ICICIBANK --until 14:45 # one line per closed bar, stops on the trigger
python3 "${CLAUDE_SKILL_DIR}/entry.py" watchlist                   # every hit in trader/watchlist.json
```

Other flags: `--or-minutes N` (default 15), `--json`, `--offline FILE` (a
saved Yahoo chart JSON, `.json` or `.json.gz`, or a folder of
`<TICKER>.json`), `--now "2026-10-30 09:35"` (India time (IST)) to replay a day.
`watch` with `--now` or `--offline` runs on a simulated clock and replays the
day bar by bar without waiting.

## What it reads and writes

| file | what |
| --- | --- |
| `trader/watchlist.json` | the scanner's hits (`hits[].symbol`), for `watchlist` |
| `trader/config.json` | `no_entries_before` (09:45) and `no_entries_after` (15:30), India time (IST). Optional |
| Yahoo chart API | today's bars, `range=1d&interval=5m` (or `1m`): free, unofficial, can lag |
| `trader/entry.json` | with `check --write`, or when `watch` triggers: symbol, setup, status, time, bar, price, level, opening range |

## The rule

- **Opening range (orb).** The high and low of the first 15 minutes: the
  9:30, 9:35 and 9:40 five-minute bars, or fifteen 1-minute bars. The level
  to beat is the range high.
- **Level.** A price you give, like a 20-day high from `/nse-scanner`.
- **The trigger** is the first completed bar after the range that CLOSES
  above the level. A wick above is not a trigger. A close exactly at the
  level is not above it.
- **The time** is that bar's close time (the 9:30 bar closes at 9:35 AM).
  The price is its close, to the cent.
- **Only closed bars count.** A bar is closed when the clock passes its start
  plus 5 (or 1) minutes and Yahoo has caught up to that moment (it waits a
  minute at most). Yahoo's live tick, like 10:49:45, is never a bar.
- **Volume, if you want it.** `--min-volume-x 1.5` also needs the trigger
  bar's volume at 1.5 times the range bars' average. The 9:30 bar holds the
  opening auction, so 1.0 is already strict.
- **Time limits.** No entries before 9:45 or after 15:30 (config). On a 1:00
  p.m. early close the cutoff moves up with the close, to 12:30.
- **What it says.** Waiting (and how far the last close is from the level),
  triggered, expired, or no data. Before 9:30: not open yet. Before 9:45: the
  range is still forming. Weekends and NSE holidays: the market is closed.

## Steps

1. Get the symbol from the user, or run `entry.py watchlist` after
   `/nse-scanner`. Check `/nse-news` for it first.
2. Run `entry.py check SYMBOL`. Tell the user the status in one line:
   waiting and how far, triggered at what time and price, or expired.
3. To wait for it, Claude can run `entry.py watch SYMBOL --until 15:30` in
   the background, or `entry.py check SYMBOL --write` on a `/loop` every 5
   minutes. `watch` wakes just after each bar closes, prints one line per
   bar, and exits 0 on the trigger (it writes `trader/entry.json`) or 1 when
   the setup expires. Keep the computer awake while it watches: a sleeping
   laptop pauses it, and it catches up, late, when it wakes.
4. When it triggers, say the time and the price, and that nothing was placed.
   If the trigger is more than a bar old, say that too: a late entry is a
   different trade.
5. Hand off to `/nse-exit` to set the stop and the target BEFORE anything
   is bought.

## Example

ICICIBANK, Friday 2026-10-30, 5-minute bars. The opening range (9:15 to 9:30)
is 1383.40 to 1390.90. At 9:33 the 9:30 bar is still open, so it waits:

```
WAITING  last close ₹1389.80 (9:25 bar), ₹1.10 under the range high ₹1390.90 (-0.08%).
The 9:30 bar is still forming (₹1394.50 so far, closes 9:35 AM); it does not count until it closes.
```

At 9:35 the bar has closed:

```
ICICIBANK.NS  Fri 2026-10-30 09:35 IST  opening-range breakout (15-minute range) on 5-minute bars (Yahoo, free, can lag)
Opening range 9:15-9:30: high ₹1390.90, low ₹1383.40 (3 of 3 bars).
TRIGGERED 9:35 AM at ₹1394.50: the 9:30 bar (bar 3) closed above the range high ₹1390.90 (+0.26%).
This is the moment to get in, if you take the trade. Nothing was placed.
Next: set the stop and target BEFORE you buy: /nse-exit (exit.py plan --from trader/entry.json).
```

With `--min-volume-x 1` it still triggers on the same bar: the 9:30 bar
traded 1.25x the opening range's volume.

## Rules

- Bar by bar, on free Yahoo 1-minute or 5-minute bars. They are unofficial
  and can lag. Say so when a minute matters.
- A signal is information, not an order, and not a promise. Nothing here
  promises winning trades or money.
- Long side only. v2 plans longs only. If the user wants a short, say that.
- One trigger per setup per day: the first close above. Later closes do not
  reset it.
- Never call an entry early because a bar looks like it will close above.

## What it never does

It never places an order, never sizes a position, never sets the stop (that
is `/nse-exit`), never moves the level after the fact, and never counts a
bar that has not closed. It never runs `/nse-broker` from a background
watch: nobody is there to say yes.

## Safety

- Education and tooling, not financial advice. A PASS is a rules check, not a recommendation.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except nse-broker, and only when all three hold: nse-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on Claude's own card (live; paper fills are simulated here) because the
  order tool is set to "Needs approval"
  (Customize > Connectors > tool permissions). Never set an order tool to "Always allow".
- No options, margin, short selling or leverage unless the config allows it and the user confirms.
- Broker keys live in environment variables or the Claude Desktop config, never in the chat.
