# Claude seat pilot: live play log (2026-11-08)

Claude plays seat P1 in the browser pane from the cockpit only (page text + the
in-game manual). No engine reads, no code, while playing. "Outside knowledge" marks a
move that leaned on something the screen did not show.

Game: lobby `ca182e91`, 1 seat + 3 bots, 500 sectors, v3.11, 1-hour days, 3 days,
1,000,000 starting credits. Day-1 goal: outfit the ship at StarDock.

## Pilot result (about 40 minutes, 22 game turns)

Covered: the manual, course plotting and Express, the shipyard and catalog, the gear
shop, the bank, Terra colonists, a Genesis torpedo, landing, placing colonists, leaving
fighters and laying mines. Everything worked end to end; the friction is in what the
screens say, not in what the buttons do.

**Fixed during the pilot**
1. The manual sent players to the wrong StarDock (said sector 1; v3.11 draws it per
   game). Now names this game's sector. Likely why the kimi seat never found StarDock.
2. The ship panel read colonists as holds ("Holds 30,000/50"); the same miscount fed
   the trade "no empty holds" check and the shop's empty-holds note.
3. The planet panel now names the type: "Class U (Gaseous)", like the original. A
   Gaseous planet makes nothing, and nothing said so before I put 30,000 colonists on it.

**Open, ranked**
1. **The 120 s idle rule hits browser seats too.** While I read code for ~2 minutes the
   log said "[Guest 1] external bot timed out (120s) — auto-WAIT". Four in a row ends
   the day and throws away saved turns (kimi run, finding 1). Confirmed: after an
   11-minute pause my seat had 10/250 turns ("249 turns skipped"). A human who steps
   away for 8 minutes loses the day. Needs Ben's call (rule change).
2. **The manual reads like a dev audit**: switch names, "Live GameA prints…", "one
   day's reading, another day was not measured". Players need rules, not provenance.
3. ~~Raw field names on forms~~ — fixed (4th live fix): labels and snake_case choices now read as words.
4. **Shop flow**: the gear form closes after each purchase and sits below the fold;
   7 items = 7 reopen-scroll-pick cycles. No total for fighters/shields once a qty is typed.
5. **Hover-only reasons**: TransWarp did nothing; "not enough fuel ore" was only a
   tooltip. The shop sold the drive without saying it burns fuel ore.
6. **Net worth drops a third when you arm** (1,023,650 → 691,942, rank to 4th). Check
   against the original; at least explain it on screen.
7. Small: Terra's load form text is a mangled template; landing on your own empty planet
   asks to confirm; "Net worth −23,987" in the buy dialog means the change.

Each row: what I wanted, where I looked, found or not, friction.

| # | Wanted | Looked at | Found? | Friction / note |
| --- | --- | --- | --- | --- |
| 1 | Learn where StarDock is and what it sells | Manual (Getting started, Ports and StarDock, StarDock services, Hardware) | Partly | **Wrong:** manual says "StarDock is sector 1" in 4+ places. Sector 1 is Terra; StarDock here is 226. Also reads like a dev audit: switch names (GRIMY_TIP_MODE), "Live GameA prints…", "one day's reading, another day was not measured", "cabal editor sample". Class 9 row says SSS and then a paragraph explains StarDock is "shown as Class 9" but "stored id stays 8": confusing. |
| 2 | Lift off home planet | Q key | Yes | Fine. 1 turn. Result line "ok — lifted off. Turns spent 1." is clear. |
| 3 | Plot a course to StarDock | C then F, typed 1 | Yes | Course card is good: hops, turns, Engage vs Express. (Typed 1 because the manual said so.) |
| 4 | Fly it | Express non-stop | Yes | Arrived in 5 hops / 15 turns. HERE panel at Terra offers "Plot course to StarDock (sector 226)" — that's where I learned the truth. |
| 5 | Fly to StarDock | HERE "Plot course to StarDock" + Express | Yes | 6 hops / 18 turns. All 3 bots parked there. Express button re-rendered under me once (page refreshes every turn) — a click target that moves. |
| 6 | Pick a better hull | Shipyards form | Partly | Form shows one hull at a time; the raw field name `ship_class` and `trade_in` are printed as labels. "Merchant Cruiser: 2,137 cr" means *net after trade-in* but reads like the hull's price. |
| 7 | Compare hulls | Computer → C Ship Catalog | Yes | Good table, one line per hull. (I first logged a 2-vs-3 turns-per-warp contradiction here; that was me misreading a screenshot. The catalog says 3, matching the yard. Retracted.) |
| 8 | Buy Havoc Gunstar | CONFIRM → "Want to buy it?" Yes/No | Yes | Confirmation is clear (trade-in, net cost, what stays behind). "Net worth −23,987 cr" means the *change* in net worth; reads like the total. |
| 9 | Buy 38 holds | StarDock: buy gear → Holds, qty | Yes | Excellent quote: price per hold, how many, total (29,336), the rising price list. |
| 10 | Buy 2,500 fighters | buy gear → Fighters | Partly | Hint says "203 cr each, up to 4,585" but no total once a qty is typed (holds show one). 507,500 cr is a big number to confirm blind. |
| 11 | Buy shields, Genesis, holo scanner, TransWarp, 5 mines | buy gear, one item per opening | Yes | **Friction:** the form closes after every purchase; each item = reopen "buy gear", scroll the HERE panel down to the form, pick, type, confirm. A shopping list of 7 items took 7 round trips. The form sits at the bottom of a scrolled panel, below the fold at 800x600. |
| 12 | Check the ship | I (Ship Info) | Yes | Clear. 3 turns per warp, matching the catalog and the yard. |
| 13 | — | Header | — | **Net worth fell 1,023,650 → 691,942 and rank to 4th of 4** after buying fighters/shields. A player reads that as "arming is punished". Check whether the original values gear this way; at least say why on screen. |
| 14 | Bank surplus | StarDock → Bank | Yes | Clean: balance, room (500,000 cap), Deposit/Withdraw, amount prefilled with all credits. Raw label `side` again. |
| 15 | TransWarp to Terra | HERE → TransWarp | No | Button does nothing visible; the reason ("not enough fuel ore") is only a hover tooltip. The shop sold me the drive without saying it burns fuel ore from the holds, and StarDock doesn't sell fuel. |
| 16 | Load colonists | Terra HERE → Load colonists | Yes | Prefilled 30 holds = whole pool. Text "Terra holds Colonists (1000s) 30 (30,000 people) of Colonists (1000s) 100 (100,000 people)" is a mangled template. |
| 17 | — | Ship panel | — | **Bug (fixed live):** "Holds 30,000/50": colonists counted as people, not holds (1,000 per hold). Same miscount fed the trade "no empty holds" check and the shop's "You only have N empty holds". Now uses the server's `cargo_free`. |
| 18 | Make a planet | U (Genesis) outside FedSpace, named it | Yes | Smooth: name field prefilled, one confirm, clear result. +25 experience. |
| 19 | Land + place colonists | L (confirm modal) → N | Partly | Landing asks to confirm even on my own empty planet. Colonist form prints raw `planet_id`, `fuel_ore`. **Gap:** nothing says a Class U planet produces nothing — I put 30,000 colonists on fuel ore and got "0 per day". The original names the type ("Gaseous"). Fixed live: panel now reads "Class U (Gaseous)". |
| 20 | — | Manual triage | — | **Fixed:** the manual printed the legacy constant (sector 1) for StarDock; v3.11 draws StarDock's sector per game. Per-game manual now says "StarDock is sector 226 in this game"; the lobby manual says it's random and where to find the course. Terra lines say sector 1 (it never moves). |
| 21 | — | Log | — | **"[Guest 1] external bot timed out (120s) — auto-WAIT"** while I spent ~2 minutes reading code. The lobby seat is on the external-seat deadline, so the stand-down rule (4 auto-WAITs = day forfeited) applies to people too. |
| 22 | Guard the planet | F → leave 1,000, defensive | Yes | Clear form (in sector / on board / cap). Sector line then shows "Fighters: 1,000 defensive yours". |
| 23 | Lay mines | H → armid, qty 5 | Yes | Clear. Sector line shows "Mines: armid 5 (belong to Guest 1)". |
| 24 | — | Header after an 11-minute pause (tests running) | — | **Confirmed on a person-style seat: TURNS 10/250**, log "Guest 1 ends the day early (249 turns skipped)". Four 120 s auto-WAITs = the saved day thrown away. |
| 25 | — | Generic forms | — | **Fixed live:** form labels were raw parameter names; now words (Planet / From / To / Quantity, "fuel ore"). `data-n` keeps the raw names for scripts and the AI seat. |
