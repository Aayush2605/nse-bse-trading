---
name: nse-news
description: >-
  News Monitor. Tracks breaking news on every stock you watch and flags what
  moves it: Indian financial headlines per stock (Google News India:
  Moneycontrol, Economic Times, CNBC-TV18, Business Standard, Mint ...), the
  company's own NSE announcements (results, board meetings, dividends,
  deals, resignations, credit ratings) and how far each stock is from
  yesterday's close. Shows only what is new since the last check, newest
  first, in India time (IST), tags each item (earnings,
  analyst, deal, halt, regulatory, macro...) and never repeats one. Use when
  the user says "any news on RELIANCE", "why is this moving", "what's the news on
  my watchlist", "morning briefing", "pre-market news", "monitor the news",
  "did anything break", "check the announcements", or after /nse-scanner finds setups.
argument-hint: "[tickers]"
---

# nse-news

A chart can look perfect and still be about to gap on a results date, a
SEBI order or a block deal. Before a setup becomes a trade, this skill reads the two
feeds that carry those first, for every stock on the watchlist, and tells you
only what is new. It also prints how far each stock has moved today, so a
headline and a move sit side by side.

Tool in this folder (standard library Python, no keys):

```bash
python3 "${CLAUDE_SKILL_DIR}/news.py"                         # watchlist + plan + portfolio
python3 "${CLAUDE_SKILL_DIR}/news.py" --tickers RELIANCE ICICIBANK --hours 12
python3 "${CLAUDE_SKILL_DIR}/news.py" --no-filings --json
```

## What it reads and writes

| file / feed | what |
| --- | --- |
| `--tickers`, else `trader/watchlist.json` | the scanner's hits (nse-scanner) |
| `trader/plan.json` | the trade you are planning (nse-exit) |
| `trader/portfolio.json` | what you hold (nse-broker records fills there) |
| Google News RSS, India edition | `https://news.google.com/rss/search?q=RELIANCE+share&hl=en-IN&gl=IN&ceid=IN:en` |
| NSE corporate announcements | the company's own filings of the last 7 days (none for BSE-only stocks) |
| Yahoo Finance chart endpoint | the last price against yesterday's close (unofficial, can lag) |
| `trader/state/news.json` | what has been shown (kept 30 days) |

## The rules

- **Headlines are leads, not facts.** Before telling the user something
  happened, open the story or the filing and read it. Quote the source and
  link it. Never summarise a paywalled story you could not read: say so.
- **Filings beat headlines.** If an NSE announcement and a headline disagree,
  the announcement is what the company told the exchange.
- **Say what it touches.** Every item lists the tickers it touches and its
  tags: earnings, analyst, legal, deal, capital, people, risk, halt,
  regulatory, macro. Filings marked `!` are the ones that move stocks:
  financial results, board meeting outcomes, dividends, bonus or split,
  buybacks, acquisitions and mergers, resignations and appointments,
  insolvency or default, credit ratings, pledges.
- **MOVING** marks a stock 3 % or more from yesterday's close (`--move-pct`).
  A move with no headline is worth saying out loud too.
- **No predictions.** Report what was published and how far the price is from
  yesterday's close. Never say what the stock will do next.

## Steps

1. Run the check: `python3 "${CLAUDE_SKILL_DIR}/news.py"`. Exit code 1 means
   nothing new. `--all` shows items already seen, `--json` gives everything
   machine readable, `--dry-run` leaves the state alone.
2. Read the items that matter: every `!` filing, anything tagged earnings,
   halt, legal, regulatory or risk, and every MOVING ticker first.
3. Write a short brief, per ticker: what happened, the source and link, the
   move, and one line on why it matters to the setup (for example "results
   are this week: an overnight gap can jump past any stop").
4. If a story changes the picture, say so before `/nse-entry` and
   `/nse-exit`: a results date inside the trade, a SEBI order, a QIP or OFS.
   Never act on a headline alone.

During the session: `/loop 15m /nse-news`, or a scheduled task each
morning before the open.

## Example

Friday 2026-10-30, ICICIBANK broke its opening range at 9:35 AM. The check
shows the bank's NSE filing that morning (an ESOP allotment, 10:16), the
weekend's headlines (NDTV Profit on foreign ownership of HDFC Bank and ICICI
Bank, CNBC-TV18's Diwali picks) and `ICICIBANK 1,398.00 +0.82% vs yesterday's
close`. The brief: "No results or board meeting this week; nothing that should
gap the stock." When a ticker has no news, say so rather than padding the brief.

## What it never does

- Never invents or embellishes a story, a quote or a number.
- Never trades on news, and never tells the user to buy or sell because of a
  headline.
- Never hammers a server: one request per feed per ticker, a pause between
  calls.

## Safety

Education and tooling, not financial advice. This skill only reads and
reports. Nothing places an order except `/nse-broker`, after
`/nse-risk` passes and the user types an explicit yes for that order.
