---
name: nse-broker
description: >-
  Order Executor. Sends approved orders to your broker, paper trading by
  default, never without your yes. Shows each order as a plain ticket (a
  bracket shows its stop-loss, take-profit and the max loss at the stop)
  plus the exact JSON for Zerodha Kite's place_order (an MIS entry, then an
  SL-M stop once it fills: Kite has no bracket orders), records your yes
  word for word. Paper trading is simulated locally: approved orders fill at
  the latest price and paper-check closes them at the stop, the target or the
  flat-by time, with profit after Indian charges. Live, Claude's own Allow
  once / Deny card asks again. Builds the flatten ticket and logs each
  trade's max loss for nse-risk. Covers connecting Zerodha's Kite MCP server
  and SEBI's static-IP rule for API orders. Use when the user says "place
  the order", "buy it", "execute", "send it to my broker", "close my
  position", "flatten", "get me out", "connect Zerodha", "connect Kite",
  "paper trade", or after /nse-risk passes.
argument-hint: "[order number]"
---

# nse-broker

The Order Executor is the only skill in this pack that can lead to a real
order, so it is the strictest. An order reaches the market only after three
separate gates, every time, for every order:

1. **nse-risk passed this exact order today** (matched by fingerprint).
2. **The user typed an explicit yes for this one order** in the chat.
3. **Live only: the user clicked Allow once** on Claude's own permission card,
   which appears because the order tool is set to "Needs approval".

In paper mode (`"paper": true`, the default) nothing ever reaches Zerodha:
`ticket.py paper` fills the approved order here instead.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/ticket.py" show                     # every ticket, READY or not
python3 "${CLAUDE_SKILL_DIR}/ticket.py" approve --index 1 --reply "yes"
python3 "${CLAUDE_SKILL_DIR}/ticket.py" paper --index 1                # paper: fill it here
python3 "${CLAUDE_SKILL_DIR}/ticket.py" paper-check                     # paper: stop / target / flat-by
python3 "${CLAUDE_SKILL_DIR}/ticket.py" result --index 1 --status placed --broker-id ID --filled-qty 26 --filled-price 1394.50
python3 "${CLAUDE_SKILL_DIR}/ticket.py" fill --symbol ICICIBANK --side sell --qty 26 --price 1401.85
python3 "${CLAUDE_SKILL_DIR}/ticket.py" flatten --symbol ICICIBANK --qty 26
python3 "${CLAUDE_SKILL_DIR}/ticket.py" log
```

`ticket.py` never talks to a broker. It renders tickets, checks that a reply
is a real yes for that order, builds the flatten ticket, and keeps the log in
`trader/state/broker.json`. `--now "2026-10-19 10:15"` pins the clock (India time (IST)).

## What it reads and writes

| file | what |
| --- | --- |
| `trader/orders.json` | the proposed orders (nse-budget writes it; `flatten` replaces it) |
| `trader/state/risk.json` | nse-risk's verdicts; only a PASS from today is READY |
| `trader/state/broker.json` | every yes, no, placed, failed and filled, with each entry's max loss |
| `trader/portfolio.json` | cash and shares, updated by `fill` and by `result --filled-qty` |
| `trader/plan.json` | the flat-by time for `flatten` |

## Paper trading (the default)

Indian brokers have no free paper accounts, so paper trading happens here.
After the user's yes:

1. `ticket.py paper --index N` fills the order at the latest 1-minute close
   on Yahoo (or `--price`), updates `trader/portfolio.json` and opens a paper
   trade with the plan's stop, target and flat-by time.
2. `ticket.py paper-check` (run it whenever the user asks how the trade is
   doing, or when nse-alerts rings) walks today's 1-minute bars since the
   fill: the stop, the target or the flat-by time closes it, and it prints
   the gross and the net profit after Indian charges. A bar that touches
   both the stop and the target counts as the stop.

## Live: Zerodha Kite (only when the user sets "paper": false)

Zerodha publishes an MCP server: github.com/zerodha/kite-mcp-server. Its
order tool is `place_order` with Kite's own fields (`variety`, `exchange`,
`tradingsymbol`, `transaction_type`, `quantity`, `product`, `order_type`,
`price`, `trigger_price`, `validity`), plus `cancel_order`, `get_orders` and
`get_positions`.

1. The hosted server (`npx mcp-remote https://mcp.kite.trade/mcp`, in
   `claude_desktop_config.example.json`) needs no API key; the user logs in
   to Kite in the browser. Zerodha says the hosted version leaves out
   destructive trading tools, so it may not offer `place_order`. For live
   orders the user self-hosts it with their own Kite Connect API key and
   secret (env vars in the Claude Desktop config, never in the chat).
2. **SEBI's retail algo rules (since April 1, 2026):** API orders must come
   from a static IP the user registered with their broker. A home connection
   with a changing IP gets its API orders rejected. That is the user's setup
   to do with Zerodha, not something this skill can work around.
3. Set the tool permissions: `place_order`, `modify_order`, `cancel_order`,
   `place_gtt_order`, `modify_gtt_order`, `delete_gtt_order`: **Needs
   approval**, never Always allow. Read-only tools (`get_positions`,
   `get_orders`, `get_holdings`, `get_margins`, `get_quotes`): Always allow is fine.
4. Check it: ask for the margins (read only) and confirm the account.

**No bracket orders on Kite.** Each entry becomes up to two calls, both MIS
(intraday) and printed by the ticket: the entry now, then the SL-M stop
**after the entry fills**. The target is not sent: nse-alerts rings at the
target, then a flatten ticket. Before any sell that closes the trade, cancel
the open SL-M stop (`get_orders`, then `cancel_order`), or both would fill
and leave the user short. If Kite rejects SL-M, use `SL` with `price` a
little under the trigger. Brokers square off MIS positions themselves around
3:15 to 3:20 PM and charge for it: be flat by `flat_by` (15:15).

## Steps: the entry

1. `ticket.py show`. Only READY tickets go to the user. A ticket that is NOT
   READY or BLOCKED goes back to `/nse-risk`.
2. Show ONE ticket and ask: "Place this order? Reply yes or no." One order
   per question. Never offer "yes to all".
3. Run `ticket.py approve --index N --reply "<the user's reply, word for word>"`.
   If it prints "Not recorded", the reply was not an explicit yes for this
   order. Ask again. Never turn a reply into a yes yourself.
4. Paper: `ticket.py paper --index N`. Live: only after "Recorded your yes",
   call `place_order` with exactly the first JSON the ticket printed; once it
   fills, the SL-M stop JSON (its own yes is the same order's: say so). Then
   `ticket.py result --index N --status placed --broker-id <id> --filled-qty Q
   --filled-price P`, or `--status denied` / `failed` with `--note`.

## Steps: while it is open, and out by the close

- nse-alerts watches the stop, the target and the flat-by time
  (`alerts.py add --from-plan`). Paper: `ticket.py paper-check` closes it.
- Live, by the target or `flat_by` (15:15 IST):
  1. `get_positions` (read only) for the quantity held.
  2. `ticket.py flatten --symbol ICICIBANK --qty 26` writes a market sell.
  3. `/nse-risk` (a sell that only closes a position is never blocked by the
     daily limits or the entry window), `ticket.py show`, the user's yes.
  4. Cancel the open SL-M stop, then `place_order` with the ticket, then `result`.

## What it never does

- Never places an order without all three gates, and never two orders on one yes.
- Never places orders from a scheduled or background task: nobody is there to say yes.
- Never asks for, reads, stores or repeats API keys or passwords.
- Never switches `"paper"` to false. The user does that themselves.
- Never places F&O, CNC (delivery) or MTF orders: this pack day trades equity on MIS only.
- Never promises a fill price: a market order and a stop fill at whatever the market gives.

## Safety

- Education and tooling, not financial advice. A PASS is a rules check, not a recommendation.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except nse-broker, and only when all three hold: nse-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on Claude's own card (live) because the order tool is set to "Needs approval"
  (Customize > Connectors > tool permissions). Never set an order tool to "Always allow".
- No options, margin, short selling or leverage unless the config allows it and the user confirms.
- Broker keys live in environment variables or the Claude Desktop config, never in the chat.
