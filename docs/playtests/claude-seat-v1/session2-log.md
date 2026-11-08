# Claude seat session 2: later-game play (2026-11-08)

Same rules as the pilot: Claude plays seat P1 from the cockpit only, logs what it
wanted, where it looked, and what got in the way; fixes go in as they are found.

Game: lobby `3e9cd19e`, 1 seat + 3 bots, 500 sectors, v3.11, 1-hour days, 5 days,
1,000,000 starting credits. Server restarted with the pilot fixes (manual StarDock
sector, stand-down rule).

Goals: outfit fast; trade with haggling; TransWarp with fuel; build a citadel; fight a
bot; meet Ferrengi; comms and computer reports.

| # | Wanted | Looked at | Found? | Friction / note |
| --- | --- | --- | --- | --- |
| 1 | Build a citadel at home | Landed, B | Yes (blocked) | Form is clear (costs, have, short, days). **Unreachable:** level 1 on class M needs 1,000,000 colonists; home has 191,000; Terra's pool is 30,000 +750/day; the planet grows ~5%/day → ~34 days. The dialog's "about 41 more Terra trips" is impossible (Terra empties after 1). Code multiplies the S1 "1,000 thousand" into people on purpose (class M fidelity). Ties to Ben's open "class M ratios" decision — not changed. |
| 2 | Haggle a buy | P → offer 20 (list 23) | Partly | **Bug (fixed):** the cockpit reopens the form on a counter by matching "counter 22", but the engine says "port countered at 22", so the form just closed and the counter was lost. Now reopens with qty and the counter price ("We'll sell them for 440 credits (22 each). Your offer?") — CONFIRM takes it. Also the no-cockpit-block fallback now prefills the counter. Haggle won at 22. |
| 3 | Lowball after a counter | offer 21 after counter 22 | Yes | "trade failed: the port lost patience" — ends the haggle, as the original. |
| 5 | Find StarDock | Manual | Yes | Fix confirmed live: "StarDock is sector 448 in this game". 8 hops / 24 turns. |
| 6 | Outfit again (scripted the same clicks) | Shipyards + buy gear ×7 | Yes | All 8 purchases clean. Trading the Cruiser for a 12-hold Gunstar dropped 8 of my 20 organics; the confirm dialog does warn ("the rest is lost…"). |
| 7 | Find a fuel ore seller | Computer → R Port Report | Yes | Clear: class, stock %, my last-seen prices with day. Found 118 (SSB) sells fuel at 19, home 354 buys at 44. |
| 8 | Buy fuel | Port table BUY 50 | Yes | One click at list price, no haggle. Good fast path. |
| 9 | TransWarp | HERE → TransWarp | Partly | Refused "no TransWarp lock in range" — engine shorthand. **Fixed:** now says a jump needs your own fighters posted in the target sector, within range; leave fighters first (F). |
| 10 | Make a lock | F → leave 100 at 118 | Yes | Button label tracks the qty ("Deploy 100 defensive"). Nice. |
| 11 | TransWarp home→118 | TransWarp form | Yes | Form lists locked sectors and "Fuel cost 21 ore". Missing: the turn cost (it was 3 vs 21 by warps — the whole point). Jump worked: 7 hops, 21 ore, 3 turns. |
| 12 | Find a bot to fight | Computer → L Trader Rankings | Partly | Rankings list name/rank/hull but not where. **All three bots are still in the starting Merchant Cruiser** — the heuristic bots never spend the 1,000,000 cr, so they are no later-game opponent. |
| 13 | Trace a bot | StarDock → Ask Grimy, trader trace 3,000 cr | Yes | Faithful and clear ("Grimy names sector 367"). But bots move every turn: by arrival (3–6 hops) they were gone, twice. Chasing costs ~20 turns a try. |
| 14 | Claim a found planet | Land (modal explains: landing does not claim) → Claim planet | Yes | Clear. "Class O (Oceanic)" shows the new type name. |
| 15 | Citadel on the Oceanic planet | B | Yes (blocked) | Level 1 needs 1,400 (thousand) = 1,400,000 colonists. **Every class is out of reach**, not only M: Terra supplies people (30,000 +750/day) while the citadel table is in handbook thousands. Looks like a units mismatch; Ben's open "class M ratios / units" call. |
| 16 | Attack the port | HERE → Attack | No | "Attack: no target in this sector" — ports are not targets under these rules. OK, but the button sits there dim with no hint that ports can't be attacked. |
| 17 | Hail a bot | COMMS → Hail | Partly | Hail reaches traders in this sector only (faithful). The Trader list was simply **empty**. Fixed: shows "Nobody in this sector to hail". |
| 18 | Fed Comm broadcast | COMMS → Fed Comm → Send | Yes | Sent and shown in the comms feed. **Bug (fixed):** after Send the text stayed in the box *with focus*, so my next command keys (C, D) typed "cd" into the message. Now a sent message clears and focus returns to the command line; a refused send keeps the text. Small: the result line drops my own name from the message text ("Guest 1: here…") and doubles punctuation ("?.") |
| 19 | — | Header | — | Nice: an "auto-WAIT 84s" countdown shows how long until the server waits for me. |
| 20 | — | Idle ~15 min while tests ran | — | **Stand-down fix confirmed live:** 5+ "[Guest 1] external bot timed out (120s) — auto-WAIT" in a row, no "ends the day early", turns kept regenerating (180 → 217/250). |
| 21 | — | Why the bots never upgrade (code read) | — | **Bug:** the heuristic bot outfits and fits a scanner only when `sector id == 1` — the legacy StarDock. Under v3.11 sector 1 is Terra and StarDock moves, so bots never buy fighters or scanners. Same root cause as the manual. Fixed to use the bot's own `_observed_dock()` (legacy unchanged: it returns 1 there). |
| 4 | — | Enter on the reopened counter form | Partly | Once, Enter did nothing; clicking CONFIRM worked. Handler looks right (last input submits); likely the form redrew under the keypress. Watch. |
