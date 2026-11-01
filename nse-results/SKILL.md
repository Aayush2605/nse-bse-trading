---
name: nse-results
description: >-
  Results Analyst. Reads a company's quarterly results straight from its NSE
  filings (SEBI's Integrated Filing, the XBRL the company filed) and sums up
  what changed: revenue, net profit and EPS for the last quarters, each
  quarter on quarter and against the same quarter a year earlier, in rupees
  crore, consolidated by default. Use when the user says "how were TCS's
  results", "analyze the results", "what changed this quarter", "is revenue
  growing", "Q2 numbers for ICICI", "check the quarterly results", or before
  trading a stock around its results date.
argument-hint: "[NSE symbol]"
---

# nse-results

Results move Indian stocks more than anything else on the calendar, and the
press release puts the best number first. This skill reads the numbers the
company actually filed with NSE, lines them up quarter by quarter, and says
plainly what changed. For a day trader it answers: did the business grow,
and is a results day coming (check `/nse-news` for the board meeting date:
a day trade is out before the close, so it is not exposed to results that
come out after hours).

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/results.py" TCS                    # consolidated, last 5 quarters
python3 "${CLAUDE_SKILL_DIR}/results.py" ICICIBANK --standalone
python3 "${CLAUDE_SKILL_DIR}/results.py" INFY --quarters 8 --json
```

## How it reads the numbers

| field | XBRL tag (Ind AS), "OneD" context = the quarter |
| --- | --- |
| revenue | `RevenueFromOperations`; banks: `InterestEarned`, then `TotalIncome` |
| net profit | `ProfitLossForPeriod` |
| EPS | basic EPS from continuing operations |

Quarters are labelled by India's financial year (April to March): the
quarter ending 30 Sep 2026 is Q2 FY27. Consolidated (the group) is the
default because that is what the market prices; `--standalone` for the
listed company alone. NSE has these filings in XBRL since SEBI's Integrated
Filing began (2025), so year-on-year growth needs five quarters on file.

## What to tell the user

Lead with the latest quarter: revenue and net profit, year on year first
(it removes seasonality), then quarter on quarter. Name anything odd: a
profit jump much bigger than revenue (a one-off gain?), falling EPS with
rising profit (more shares?). Then the link to the filing if they want to
read it. Never call results "good" or "bad" as a trade signal.

## Limits

- Numbers as filed. A restated or revised filing replaces the earlier one.
- BSE-only stocks are not covered (it reads NSE filings).
- Education and tooling, not financial advice.

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
