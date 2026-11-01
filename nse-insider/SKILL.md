---
name: nse-insider
description: >-
  Insider Tracker. Reads the insider-trade disclosures promoters, directors
  and key staff must file under SEBI's insider-trading rules (PIT), as NSE
  posts them, plus every bulk and block deal of the day across the market.
  Shows who traded, buy or sell, how many shares, the value in rupees crore,
  how (market, off-market, pledge, ESOP) and what they hold after. Use when
  the user says "are promoters buying", "insider trades in RELIANCE", "who
  is selling", "bulk deals today", "block deals", "did any big investor buy",
  or to check the stocks on the watchlist before a trade.
argument-hint: "[NSE symbols]"
---

# nse-insider

When the people running a company buy its shares on the market with their
own money, that is worth knowing; when a big fund dumps a block, so is that.
This skill reads both from NSE.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/insider.py" --symbol RELIANCE              # one company, last 30 days
python3 "${CLAUDE_SKILL_DIR}/insider.py"                                # watchlist + plan + portfolio
python3 "${CLAUDE_SKILL_DIR}/insider.py" --symbol TCS --days 365 --market-only
python3 "${CLAUDE_SKILL_DIR}/insider.py" --deals                        # today's bulk and block deals
```

## Reading it

- **Mode matters.** "Market Purchase" or "Market Sale" is a real view.
  Off-market transfers, gifts, inheritance, pledges and ESOP allotments say
  little. `--market-only` keeps just the market trades.
- **Who:** Promoter and Promoter Group, Director, KMP (key managerial
  person), Immediate relative, Designated person.
- **A bulk deal** is a trade over 0.5% of a company's shares in a day; a
  **block deal** is one large trade in the exchange's block window. Both list
  the client's name.
- Disclosures come days after the trade (within two trading days to the
  company, then to the exchange). By the time you read them, the price may
  have moved.

## Safety

- These are public disclosures filed after the fact, not inside information
  and not a tip.
- BSE-only stocks are not covered (it reads NSE's disclosures).
- Education and tooling, not financial advice.
