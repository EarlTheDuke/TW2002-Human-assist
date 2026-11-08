# Claude seat session 2: later-game play (2026-11-08)

Same rules as the pilot: Claude plays seat P1 from the cockpit only, logs what it
wanted, where it looked, and what got in the way; fixes go in as they are found.

Game: lobby `3e9cd19e`, 1 seat + 3 bots, 500 sectors, v3.11, 1-hour days, 5 days,
1,000,000 starting credits. Server restarted with the pilot fixes (manual StarDock
sector, stand-down rule).

Goals: outfit fast; trade with haggling; TransWarp with fuel; build a citadel; fight a
bot; meet Ferrengi; comms and computer reports.

## Session 2 result

Worked end to end from the cockpit: StarDock (manual fix confirmed), shipyard + 7-item
outfit, Port Report, one-click trades, haggling, TransWarp with a fighter lock, Grimy
traces, claiming an orphaned planet, holo scans, Fed Comm, corporation create + menu,
offensive fighters and mines. The turn-saving fix held live through 15+ minutes idle.

**Fixed this session**
1. Haggle counters were dropped: the cockpit looked for "counter 22", the engine says
   "port countered at 22". The form now stays open with the counter price and quantity.
2. After Send, the comms box kept text and focus, so command keys typed into it.
3. Empty hail list now says "Nobody in this sector to hail"; "no TransWarp lock" explained.
4. **Bots never outfitted under v3.11** — the heuristic checked `sector == 1` for
   StarDock. Now uses the drawn sector and banks before shopping. In the pinned 4242
   match the bot's net worth went 84,310 → 162,532. Both v3.11 pins re-pinned on purpose.

**Blocked / for Ben**
1. **Citadels are unreachable under v3.11 for every planet class.** Level 1 needs
   1,000,000+ colonists (M: 1,000k, O: 1,400k) while Terra supplies 30,000 + 750/day and a
   planet grows ~5%/day. Looks like a units mismatch (Terra in people, the citadel table in
   handbook thousands). Ben's open "class M ratios / units" decision.
   *Evidence (docs/reference/tw2002/cabal_strategy_site/planets.html):* the citadel table
   gives Class M L1 "Colo 1000", Oceanic "1400" — planet units, the cockpit's "Colonists
   (1000s)", where one hold of colonists is one unit. So L1 was ~1,000 holds: about 20
   Terra runs in a 50-hold ship, normal mid-game play. Here Terra's measured "30,000" and
   "+750/day" are stored as *people* (`TERRA_LIVE_START`, 1,000 per hold) — 30 holds in
   total, ever. **Recommendation:** read Terra's 30,000 and +750 as units (thousands of
   people), i.e. 30,000,000 people and +750,000/day. That one change makes every citadel
   reachable at the original pace without touching the citadel table. Not changed here
   (fidelity call, Ben's open decision).
2. Fighting a bot means luck: bots move every round, a Grimy trace is stale on arrival.
   Traps (offensive fighters on a hub) are the realistic route; waiting for a hit.

**Small, open**
- Port names reuse the bot names ("Port Orion-52" vs trader "Orion").
- TransWarp form shows ore but not the turn cost (3 vs 21 by warps).
- Fed Comm result line drops my own name from the message and doubles punctuation.
- Ports can't be attacked here, and the Attack button gives no hint why beyond "no target".
- Corporations use tickers; the original numbered them.

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
| 22 | Find Ferrengi | Manual → Ferrengi | Partly | Manual says they leave new traders alone for 5 days, not where they roam. Still dev wording ("The string 1 does not"). |
| 23 | Explore far | Course plotter + Express ×4, holo scan at each stop | Yes | Express is the right tool: 6–9 hops a call, arrival line clear. 5 planets and ports found; Orion spotted next door at 485. |
| 24 | Catch Orion | Warp next door, holo-scan, follow | No | Bots move every round; three times the target was one lane ahead. **Name clash:** ports are named after the bots ("Port Orion-52" vs trader "Orion 30 fighters") — even my scan reader confused them; a person will too. |
| 25 | Set a trap instead | F → 300 offensive + H → 5 armid at hub 485 (7 lanes) | Yes | Forms clear; sector line shows both. Waiting to see an engagement report. |
| 26 | Did the trap work? | Result line, G (Deployed Fighters), C → L Rankings | Partly | "Your mines hit Vega in sector 485 for 60 damage." Rankings then show **Vega in an escape pod** — the 2 mines' overflow took its 30 fighters and the ship was destroyed. **Nothing told me I killed it.** Root cause (engine): `_destroy_ship(..., reason="mines")` passes no killer, so the mine owner gets no kill summary, no kill credit, and the death record has no killer. Recommend passing the mine owner as killer (rule change, flag-gated → Ben). |
| 27 | — | G Deployed Fighters | — | **Bug (fixed):** showed "5 armid mines" at 485 after 2 went off; the screen rebuilt totals from deploy/recall events only. Now subtracts detonations and takes the engine's "fighters stay" count after a fight. |
| 28 | — | Offensive fighters | — | Did not fire: the mines killed Vega first (entry order NavHaz → limpet → armid → quasar → fighters, per the v26 notes). Correct. |
| 29 | Corporation | T → CORP CREATE (ticker, name) → corp menu | Yes | Created "Claude Test Corp [CLD]". Corp menu clear: Invite/Join dim for a one-man corp, Memo, Deposit credits, Set password, Transfer C.E.O., Make ship corporate, alliances. |
| 4 | — | Enter on the reopened counter form | Partly | Once, Enter did nothing; clicking CONFIRM worked. Handler looks right (last input submits); likely the form redrew under the keypress. Watch. |
