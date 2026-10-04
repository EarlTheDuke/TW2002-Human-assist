# Port turns and regen

Moving into a sector still costs the warp. The first trade of a visit then costs 1 turn. Later trades in that same visit cost none. The visit ends when the player leaves the sector. Each day, every commodity on a port gains units from that commodity's productivity, scaled by the 5 percent regen setting. New ports open with no product on hand.

## Original rule

**Docking.** GAP_MAP row 2.7 says docking costs 1 turn, and trades at that port then cost no extra turns. It cites the Bible and the "Evil or Red Cashing" screen text. CONFIRMED as that row states it. The library file `classictw_docs_wiki/Evil_or_Red_Cashing.html` talks about a turn spent stealing, not about a second trade being free. The Bible file in this library does not print the dock sentence. Treating the GAP row as the rule is CONFIRMED by the map. The exact Bible line was not found in the saved text.

**Regen percent.** The v3.05 changelog says a TEDIT option sets port regeneration from 1 percent to 200 percent per day. Standard is 5 percent, which is the rate ports used in all previous versions. CONFIRMED. Source: `docs/reference/tw2002/classictw_museum_wiki/tw-attac_TW2002_v3_revision_history_to_v3.11.html`. A sample game settings screen shows 1 percent per day. SOURCE-CONFLICT. Source: `docs/reference/tw2002/cabal_strategy_site/twgs.html`. We keep 5 percent, the standard, as `PORT_REGEN_PER_DAY`.

**Productivity.** TEDIT labels F, G, and H "Productivity (units per day)". The same page says the port can handle 10 times that number in holds, up to 3,276 in MBBS. CONFIRMED. Source: `docs/reference/tw2002/cabal_strategy_site/economy2.html`. How the 5 percent setting multiplies those units is not printed. Applying 5 percent to the units-per-day figure is UNVERIFIED.

**Opening stock.** v3.03 says a port reports 0 buy/sell, 0 percent of max, until it opens, and it opens at 0 percent. Regeneration starts then. CONFIRMED. Source: the same revision history. `economy1.html` says ports that traders empty stay thin for days. CONFIRMED as a description of play. GAP_MAP row 2.9.

**Buy-port product.** On a port that is buying, 0 product means it will buy up to its maximum. On a port that is selling, 0 product means it cannot sell. CONFIRMED. Source: `economy2.html`.

## What this slice does

`PORT_DOCK_TURN_COST` is 1. `trade_turn_cost` returns that on the first successful trade in a sector, and 0 while `port_visit_sector_id` is still this sector. `end_port_visit` clears it. Warp, planet transwarp, the transporter, and death all call it, because those are the moves that change a player's sector. A failed trade that is not a refused counter spends 0 and does not open the visit. A refused counter still spends 1 turn, from the haggle slice.

Each day, each commodity gains `round(productivity * 0.05)` units, then the stock is held inside 0 to its max. A missing productivity adds nothing, so an old save still loads. The same seed stores the same productivity, so the same seed regens the same way.

New ports draw the old 35 to 95 percent figure and drop it, so the rest of the universe stream stays put. The stock actually placed is `PORT_START_STOCK_PERCENT` (0) times the maximum.

## Deliberate differences

- **5 percent, not the sample's 1 percent.** The changelog calls 5 percent the standard.
- **5 percent of the units-per-day number, not of capacity.** The page does not say which base the percent uses. Capacity stays whatever the universe already rolled. It is not rewritten to 10 times productivity.
- **Both sides gain units.** The old drift pulled a buying port toward 30 percent of max. This slice only adds. A buying port that fills up buys less.
- **A refused counter still costs 1 turn.** The visit rule charges the dock turn only when a trade happens. The haggle failure is the other turn.
- **Amounts under half a unit round away, and under that they add 0.** The original's rounding is not printed.

## Known effects

The first day has no selling-port stock anywhere. Ports open at 0 percent and regen runs at the day tick, which is the original rule. Seed 31's day-10 seat-brain finish is 347,690, against a ladder floor of 367,890. A later slice, not this one, will retune the seat brain for empty ports.

## Seat brain, seed 250925

Same command before and after: `python scripts/seat_brain_acceptance.py n1 --seeds 250925 --credits 100000,20000`.

Before, with the old 3-turn trade and the old stock fill:

- 100,000 credits: StarDock on day 1, 24 turns, trade profit 10,050, peak 100,000, end sector 301, rejected 0, ABA 0/184.
- 20,000 credits: no StarDock, trade profit 9,260, peak 29,260, end sector 110, rejected 0, ABA 0/251.

After, with a 1-turn dock and ports opening empty:

- 100,000 credits: StarDock on day 1, 24 turns, trade profit 0, peak 100,000, end sector 717, rejected 0, ABA 0/259.
- 20,000 credits: no StarDock, trade profit 0, peak 20,000, end sector 559, rejected 0, ABA 0/318.

The 100,000-credit seat still reaches StarDock. It no longer makes money on the way, because a selling port has nothing on the shelf. The 20,000-credit seat no longer earns either. A second map, seed 20260925, does the same: the rich seat docks on day 1 with profit 0, and the poor seat does not dock and does not earn.

Day 10 is a different picture. Seed 250925 still finishes at 478,853, over the 145,000 bar, with the ferry at 6.8 percent. Seeds 20260925, 230923, and 99 also stay above 85 percent of the fixed ladder. Seed 31 finishes at 347,690, and the ladder on that map finishes at 432,812, so 347,690 is under the 85 percent floor (367,890). This slice does not retune the brain. A later slice should teach a poor seat to sell into buying ports, which open ready, or to wait until the selling ports refill.
