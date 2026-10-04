# Ship roster and caps

task_id: ship-roster-caps-v1

Purchase prices and caps are the Bible chart in `Bible_TWGS_edit_2007_Clme.htm` ("Ship Charts for DefaultGame Setup"). The first number in each cost cell is the hull price. The second number is that chart's "cost to max holds". This slice does not replace the hold-price formula with that second number.

Where the Bible chart and `Someguy_MBBS_manual.txt` disagree, the MBBS figure is the one the yard uses. `OldBBS_2002SHIP.txt` is an older sheet. Its base costs are lower, and they are not charged. Combat odds and fighters per attack are copied onto the spec and are not used by any fight. The planet-offense wave still reads the legacy `SHIP_SPECS` table.

`ECONOMY_SCALE_MODE = "legacy"` keeps the old ten-ship table, the old prices, and the old 150-hold ceiling. `"tw2002"` uses the table below.

Merchant Freighter is already in `SHIP_SPECS`. The task text that said it was missing from that dict is wrong. Its stats in the old dict do not match the chart.

## Chart versus the yard

Included holds are what `buy_ship` puts on the hull. The Merchant Cruiser's 20 is the chart's known start. The other nine ships we already sold keep the included count they had, unless that count was over the chart max (Havoc Gunstar was 65, the chart max is 50). The six ships that were not in the yard use the OldBBS basic-hold count when that sheet has a column. That included count is SOURCE-CONFLICT. The Interdictor has no OldBBS column, so its included 20 is UNVERIFIED.

| Ship | Price | Holds max (included) | Fighters | Shields | Mines | Genesis | Photons | TPW | Per attack | Off. odds | Mark |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Merchant Cruiser | 41300 | 75 (20) | 2500 | 400 | 50 | 5 | 0 | 3 | 750 | 1.0 | Price SOURCE-CONFLICT (OldBBS 26300). Stats CONFIRMED. |
| Scout Marauder | 15950 | 25 (25) | 150 | 100 | 0 | 0 | 0 | 2 | 250 | 2.0 | Fighters SOURCE-CONFLICT. Chart and OldBBS say 250. MBBS says 150. Yard uses 150. Price SOURCE-CONFLICT (OldBBS 13200). |
| Missile Frigate | 100800 | 60 (40) | 5000 | 400 | 5 | 0 | 10 | 3 | 3000 | 1.3 | Stats and photon count CONFIRMED on the chart. Included 40 is the old package, not an OldBBS minimum (that sheet says 12). Price SOURCE-CONFLICT (OldBBS 28800). |
| BattleShip | 88500 | 80 (80) | 10000 | 750 | 25 | 1 | 0 | 4 | 3000 | 1.6 | Stats CONFIRMED. Price SOURCE-CONFLICT (OldBBS 40500). Old dict had shields 400 and 3 turns per warp. |
| Corporate Flagship | 163500 | 85 (85) | 20000 | 1500 | 100 | 10 | 0 | 3 | 6000 | 1.2 | Shields SOURCE-CONFLICT. Chart says 1000. MBBS and OldBBS say 1500. Yard uses 1500. Still corp-membership only. Price SOURCE-CONFLICT (OldBBS 71000). |
| Colonial Transport | 63600 | 250 (50) | 200 | 500 | 0 | 5 | 0 | 6 | 100 | 0.6 | Stats CONFIRMED. Included 50 is the old package (OldBBS minimum is 40). |
| CargoTran | 51950 | 125 (75) | 400 | 1000 | 1 | 2 | 0 | 4 | 125 | 0.8 | Stats CONFIRMED. Included 75 is the old package (OldBBS minimum is 40). Old dict had shields 100 and 3 turns per warp. |
| Merchant Freighter | 33400 | 65 (65) | 300 | 500 | 2 | 2 | 0 | 2 | 100 | 0.8 | Stats CONFIRMED. It was already in `SHIP_SPECS` at 350000, 2500 fighters, 750 shields, 3 turns per warp. |
| Havoc Gunstar | 79000 | 50 (50) | 10000 | 3000 | 5 | 1 | 0 | 3 | 1000 | 1.2 | Stats CONFIRMED. Included holds dropped from 65 to the chart max. TransWarp range 16 is not this slice. |
| Imperial StarShip | 339000 | 150 (150) | 50000 | 2000 | 125 | 10 | 5 | 4 | 10000 | 1.5 | Stats and photon count CONFIRMED. Shields were 5000 and turns per warp were 3. Alignment gate stays 2000 and the hull stays unique. Commission is not this slice. Price SOURCE-CONFLICT (OldBBS 128600). |
| Star Master | 61300 | 73 (30) | 5000 | 2000 | 50 | 5 | 0 | 3 | 1000 | 1.4 | Chart stats CONFIRMED. Price SOURCE-CONFLICT with the Bible narrative and OldBBS, both 48000. Included 30 is the OldBBS basic hold. Was not in the yard. |
| Constellation | 72500 | 80 (20) | 5000 | 750 | 25 | 2 | 0 | 3 | 2000 | 1.4 | Chart stats CONFIRMED. The chart spells it Constilation. Price SOURCE-CONFLICT (narrative and OldBBS 40500). Included 20 is the OldBBS basic hold. Was not in the yard. |
| T'Khasi Orion | 42500 | 60 (30) | 750 | 750 | 5 | 1 | 0 | 2 | 250 | 1.1 | Chart stats CONFIRMED. Price SOURCE-CONFLICT (narrative and OldBBS 36000). Included 30 is the OldBBS basic hold. Was not in the yard. |
| Tholian Sentinel | 47500 | 50 (10) | 2500 | 4000 | 50 | 1 | 0 | 4 | 800 | 1.0 | Chart stats CONFIRMED. The chart spells it Sentinal. Defending a corporate planet at 4:1 is a fight rule and is not applied. Price SOURCE-CONFLICT (narrative and OldBBS 27000). Included 10 is the OldBBS basic hold. Was not in the yard. |
| Taurean Mule | 63600 | 150 (40) | 300 | 600 | 0 | 1 | 0 | 4 | 150 | 0.5 | Chart stats CONFIRMED. Price equals the Colonial Transport. SOURCE-CONFLICT with the narrative and OldBBS 53600. Included 40 is the OldBBS basic hold. Was not in the yard. |
| Interdictor Cruiser | 539000 | 40 (20) | 100000 | 4000 | 200 | 20 | 0 | 15 | 15000 | 1.2 | Chart stats CONFIRMED. Included 20 is UNVERIFIED (no older minimum). The generator, the landing ban, and "cannot flee" are not this slice. Was not in the yard. |

Fighters per attack on the chart disagree with OldBBS on several hulls (Merchant Cruiser 750 on the chart, 1000 on OldBBS; Tholian 800 versus 1000). The yard stores the chart number and does not use it.

## Not for sale

The Escape Pod (chart: price 0, 5 holds, 50 fighters, 50 shields, 6 turns per warp, odds 0.6, no mines, no genesis, no photons) is not a yard hull. The three Ferrengi types (Assault Trader, Battle Cruiser, Dreadnought) are NPC ships. The Dreadnought's chart photon count is 1. None of the four is a `buy_ship` choice.

## Deliberate differences

- Odds, fighters per attack, TransWarp, the Interdictor generator, the Tholian defend-odds, Federal commission, and stripping fighters or cargo on a trade-in are not applied. Extras stay on the hull you are flying.
- A trade-in is 25 percent of `ship_cost` of the old hull. If that credit is larger than the new hull's price, the yard charges 0. It does not pay the surplus out as cash.
- Probes, cloaks, beacons, and a separate atomic cap are gap-map row 4.17. This slice caps holds, fighters, shields, mines (one total across armid, limpet, and atomic), genesis, and photons. The three mine types share that one number. A ship with photon cap 0 cannot buy a photon.
- The planet-offense wave still reads legacy `SHIP_SPECS`. A hull that exists only on the tw2002 table is not on that wave path.
- The seat brain still buys a CargoTran by name. It reads the live turns-per-warp so a hop it plans is the hop the engine charges. No weight, floor, or ferry cap was moved.

## Planted bugs

Each one was planted, the named test failed, and the line was put back.

- Wrong cap. Merchant Cruiser `max_holds` set to 999. Failed `test_merchant_cruiser_hold_cap_is_the_chart`.
- Wrong trade-in. The buy handler priced the old hull from the legacy `SHIP_SPECS` cost. Scout to CargoTran then moves the wrong number of credits. Failed `test_scout_to_cargotran_uses_ship_cost_trade_in`.
- Missing ship. The legal list skipped `star_master`. Failed `test_star_master_is_on_the_legal_list`.
- Cap not enforced. `buy_equip` accepted holds past `max_holds`. Failed `test_buy_equip_stops_at_the_hold_cap`.

## Seat brain

CargoTran turns per warp go from 3 to 4, and its shield cap goes from 100 to 1000. The brain still buys that hull by name. It reads the live turns-per-warp, so a hop it plans is the hop the engine charges. No weight, floor, or ferry cap was moved.

The day-10 bench still clears 145k, ferry under 40 percent, rejected 0, and 85 percent of the N2 ladder run on the same seeds. Absolute net worth is lower than the turns-per-warp-3 bench, because both the ladder and the allocator pay 4 turns a hop after the upgrade.

| Seed | N2 | N3 | N3 ferry | Organics |
| --- | --- | --- | --- | --- |
| 250925 | 2947603 | 7255106 | 0.0% | 9 |
| 20260925 | 2221042 | 7283009 | 0.1% | 19 |
| 230923 | 5995548 | 8176663 | 0.0% | 25 |
| 99 | 3905412 | 6290432 | 0.0% | 25 |
| 31 | 3342509 | 8532299 | 0.0% | 25 |
