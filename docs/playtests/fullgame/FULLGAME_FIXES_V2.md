# Full-game fixes v2 (dividend transfer exploit, N3 hunting, neutral combat framing, slow-hull hint, Scout recovery)

Slice `fullgame-fixes-v2`, on `f10b080`. Follows [FULLGAME_FIXES_V1.md](FULLGAME_FIXES_V1.md). The trigger was the last full 7-seat test game on seed 250925, which had no ship-vs-ship combat and a planet-dividend exploit. A QC add-on covers seed 20260925, where two code seats spent the whole game stuck in Scouts. Target is TWGS 3.11, with MBBS breaking ties. Every behaviour change has its own `*_MODE` switch in `engine/constants.py`. `"legacy"` keeps the old code path byte-identical (see Pins).

| # | Fix | Switch (default `"tw2002"`) | Where |
| --- | --- | --- | --- |
| 1 | Ship<->planet transfers no longer count as dividend growth | `PLANET_DIVIDEND_MODE` | `runner.DIVIDEND_TRANSFER_VERBS`, `planets._pay_planet_value_tax` |
| 2 | N3 attacks ships and Ferrengi it clearly beats, and arms a hunting hull for it | `HUNT_MODE` (+ `HUNT_*`, `HUNT_ARM_*`) | `seat_brain._hunt`, `_hunt_arm`, `_opt_hunt_arm` |
| 2b | BattleShip / Missile Frigate read the shields of a trader in their own sector | `COMBAT_SCANNER_MODE` | `scanners.traders_in(combat_scan=True)` |
| 3 | The LLM prompt and hints show combat neutrally, with its rewards, costs and a win check | `COMBAT_FRAMING_MODE` | `prompts._combat_framing_prompt_text`, `observation._ferrengi_check/_trader_check` |
| 4 | BattleShip 4 turns/warp: prompt note, StarDock hint, and the N3 hull pick never slows the route | `SLOW_HULL_HINT_MODE` | `prompts`, `observation._slow_hull_line`, `seat_brain._best_combat_hull` |
| 5 | A hull that cannot carry a Genesis Torpedo never flies to StarDock for one | `GENESIS_HULL_MODE` | `seat_brain._no_genesis_hull` |
| 6 | Armid damage past the shields counts only the part the shields did not absorb | `MINE_OVERFLOW_MODE` | `runner._apply_sector_hazards` |

## 1. Planet dividend: deposits are not growth

The dividend is our own rule (GAP_MAP 6.13). Each day it pays 30% (`PLANET_VALUE_TAX_RATE`) of a planet's new value since `last_tax_value`. In TW2002 a planet grows only through colonist production, and the citadel treasury earns interest (TWFAQ_20PLANET.txt; Iago_War_Manual.txt). A stored fighter, credit or colonist earns nothing.

**Exploit (v1 doc, reproduced):** deposit 5,000 fighters on your planet and tick, and you are paid 75,000 cr (5,000 x 50 x 30%). Withdraw them (the baseline drops and nothing is clawed back), deposit again, and you are paid 75,000 again. Treasury deposits, dumped cargo and assigned colonists pumped the same way.

**Fix:** under `PLANET_DIVIDEND_MODE = "tw2002"`, every ship<->planet transfer verb (`load_planet_cargo`, `dump_planet_cargo`, `assign_colonists`, `deposit_treasury`, `withdraw_treasury`, `deposit_planet_defense`, `withdraw_planet_defense`) shifts `last_tax_value` by exactly the dividend value it moved. Only production, colonist growth, treasury interest and citadel work still pay. The baseline may now go below 0, so a same-day withdrawal does not swallow that day's real production. Legacy keeps the `max(0, ...)` clamp and the old baseline.

| | legacy | tw2002 |
| --- | --- | --- |
| 3 deposit/withdraw cycles of 5,000 fighters (test) | +75,000 per deposit | 0 |
| 200k treasury + 50 equipment deposited, 1 tick (test) | 30% of 200k+ | 30% of one day's interest only |
| Total dividend paid, 10-day match, seed 250925 (all seats) | 109,443 cr (f10b080) | 75,431 cr |

Part of the old total was colonist ferrying (`assign_colonists`) paid out as "growth". That income moves to the colonists' real production on later days.

## 2. N3 hunting (`HUNT_MODE`, `COMBAT_SCANNER_MODE`)

Before this slice, N1/N2/N3 attacked only to clear a fighter challenge (`_ship_attack`: "Other ships are not hunted this slice").

`SeatBrain._hunt` (N3 / `value_allocator` only) runs before the trade options. It acts only when all of these hold:

- outside FedSpace, not landed, not in a pod, and `attack` is legal;
- the target is in its own sector: a Ferrengi it can see (fighters, shields, hull), or a trader (fighters and hull). It never targets a Federal or a pod;
- one attack is deterministic (power = qty x hull odds; the target dies when power >= (shields + fighters) x its odds), so "clearly beats" means power >= `HUNT_STRENGTH_MARGIN` (2.0) x the worst-case defence it can see. A trader's shields are hidden, so the hull's **max** shields are assumed. A BattleShip or Missile Frigate reads the real value (`COMBAT_SCANNER_MODE`; Someguy_MBBS_manual.txt: the Battleship has a "built-in Combat Scanner which shows how many shields your victim has when you attack");
- the estimated alignment cost (x12/a1 + x13/a2; the victim's alignment is hidden, so it assumes the hunter's own + `HUNT_ALIGN_UNCERTAINTY` 50) keeps the hunter >= `HUNT_ALIGN_FLOOR` 0. It never hunts itself evil or out of FedSpace protection. An evil target costs nothing;
- at most `HUNT_MAX_ATTACKS_PER_TARGET_DAY` (2) attacks per target per day.

Ferrengi come first (the one hailing us, then the biggest bounty), then traders.

**Why the first version never fired:** across 166 sightings in the after1 match, none was winnable. N3 carries the 200-fighter defence floor, a CargoTran can send only 125 fighters per attack at 0.8 odds, and the smallest Ferrengi seen had 761 fighters. **Arming** (`_hunt_arm`, `HUNT_ARM_*`) runs only where `_buy_defense` would buy nothing, and on the N3 options path when the seat is already docked (`_opt_hunt_arm`, value `HUNT_ARM_OPTION_VALUE`; it never diverts to StarDock). It arms only a hunting hull (odds >= 1.3 that can send 1,500 in one attack: BattleShip, Missile Frigate, Imperial, ...). The seat needs credits >= 150k. It buys toward 1,500 fighters, one buy per game day, at most 25% of cash above working capital, and never drops below 150k. BattleShip with 1,500 fighters = 2,400 power, 2x a 761-fighter Ferrengi Assault Trader.

## 3. LLM combat framing (`COMBAT_FRAMING_MODE`)

The old full prompt said "FERRENGI are NPC pirates. Low-aggression ones are easy XP. High-aggression will wreck you." It also said combat tools are "SITUATIONAL - a solo trader who never allies or attacks can still win". The new text says:

- Ferrengi are a fair target outside FedSpace. A kill pays 1,000 cr x aggression bounty, salvage, experience x aggression and +10 alignment. It gives the one-attack win rule against the shown fighters/shields/hull odds, and notes that ignoring a hail pays tribute.
- Attacking a trader outside FedSpace: what a kill earns (experience + 10% of the victim's; the victim loses ship and cargo) and what it costs (lost fighters, alignment: half a good victim's, sign reversed). Shields are hidden, so assume the hull's max.
- "Trade, alliances and combat are all legitimate paths ... Weigh the reward against the risk."

The minimal-hint prompt gets a one-line version. Action hints in your sector show a per-target check, for example `ferr_1 (aggression 2, 300 ftrs / 50 shields x1): kill = 2,000 cr bounty + salvage, ...; your 2000 ftrs = power 3200 vs defence 350 -> you destroy it in one attack`, and the same for traders ("beatable even at max shields" / "not a sure kill"). Nothing says to attack.

## 4. Slow hull (`SLOW_HULL_HINT_MODE`)

- Prompt price sheet: `battleship 88,500, 80 holds, 4 turns/warp (at 50 turns/day ~12 warps: a combat hull, slow for trading)`.
- At StarDock, in a day of 100 turns or fewer, when not already flying one: `BattleShip: 4 turns per warp = about N warps in your T-turn day; it is a combat hull and hurts trading. Compare turns_per_warp before buy_ship.`
- Heuristic: `_best_combat_hull` skips any hull with more turns per warp than the current one. A Merchant Cruiser (3) is never "upgraded" to a BattleShip (4). CargoTran (4) -> BattleShip (4) is still allowed. Legacy may still pick the slower hull (test).

## 5. Scouts stuck after a loss (QC add-on, seed 20260925; `GENESIS_HULL_MODE`, `MINE_OVERFLOW_MODE`)

**Diagnosis** (traced on ad21ac6, same result on f10b080, N3,N3,N2,N2,N1,H, 10 days):

1. The Ferrengal is sector 420, a dead end 7-11 hops from the FedSpace starts, with 50 armids and 1,000 Ferrengi fighters (`place_ferrengal`; Bible: 50 mines). On day 1, P1, P2, P3 and P5 all explored into it ("explore -> 420 (earn: look for ports)"). In 20-fighter Merchant Cruisers with no shields, the armids (25 hits x 20) killed them. This matches the rules (TW2002 mines hit any entering ship; the home sector is not shown to players). It is not the bug.
2. Each seat traded its pod for the free Scout Marauder. The N3 seats waited for the CargoTran trade-in (`hull_wait`) and recovered (CargoTran on day 2).
3. **The bug:** the N1/N2 ladders treat "no worlds and credits >= torpedo + L1 citadel" as "genesis is affordable - autopilot to StarDock". The Scout carries **no** Genesis Torpedo (`max_genesis` 0, TW2002 ship chart), so StarDock never sells one. The seat then picks a trade route, gets one hop out, and the same check sends it back. On day 3, P5 made 159 of 190 decisions as `plot_course` between StarDock and a port. Credits stayed at 27,867 (P3) and 31,141 (P5) from day 2 to day 10.

**Fix:** under `GENESIS_HULL_MODE`, genesis counts as reachable only when `ship.genesis_cap > 0`. This covers `_needs_stardock`, the N3 `_opt_genesis` and the second-world check. In a 0-cap hull the seat keeps trading until the CargoTran trade-in is affordable, then upgrades. Legacy observations carry no `genesis_cap`, so the check is inert there as well.

**Rule deviation found on the way:** `_apply_sector_hazards` computed the armid overflow after zeroing the shields, so a ship with some shields lost fighters for the **full** damage. Example: 100 shields + 300 fighters, 200 damage: 100 fighters left, not 200. `MINE_OVERFLOW_MODE = "tw2002"` subtracts only what the shields did not absorb. It did not change these two seats, which had no shields.

| seed 20260925, 10 days | N2-P3 net worth | N1-P5 net worth | P3 / P5 hull at end |
| --- | --- | --- | --- |
| before (ad21ac6 and f10b080) | 40,392 (frozen from day 2) | 41,116 (frozen from day 2) | Scout / Scout |
| after (this slice) | 673,633 | 398,333 | CargoTran / CargoTran |

Net worth spread across all six seats: 811,699 -> 365,843. Not changed: the Ferrengal placement and its 50 mines / 1,000 fighters (`FERRENGAL_FIGHTERS` is still marked UNVERIFIED in ferrengi-aliens-v1), and the free Scout after a loss. Open idea, not done: a holo or density scan before exploring a dead end would show the Ferrengal fighters.

## Matches (scripted, `combat_match.py` wrapper around `scripts/run_scripted_match.run_match`, tw2002 defaults, no server, no ports)

Before = `f10b080` (origin at rebase). After = this slice. Seats N3,N3,N2,N2,N1,H, 1,000 turns/day, 20k start, Ferrengi on. Combat counts come from `combat` / `ship_destroyed` events.

**Seed 250925, 10 days**

| seat | before NW | after NW | after fighters |
| --- | --- | --- | --- |
| N3-P1 | 820,569 | 747,201 | 828 (armed from day 9, BattleShip) |
| H-P6 | 604,003 | 552,814 | 150 |
| N2-P4 | 471,830 | 523,082 | 200 |
| N1-P5 | 447,200 | 445,423 | 20 |
| N2-P3 | 387,725 | 294,636 | 20 |
| N3-P2 | 316,312 | 240,690 | 20 |

Seat attacks: 0 before, 0 after. P1 has a BattleShip only from day 9, and P2 never upgrades. No winnable target met the 2x margin and the alignment floor in 10 days. Total dividend paid: 109,443 -> 75,431 cr (fix 1). Net-worth spread 504,257 -> 506,511. No exceptions, no rejected actions. Moving the dividend changes the N2/N3 cash curve: P3 loses 16k of ferry "growth" pay early and builds slower. That money was the exploit.

**Seed 250925, 20 days (after; the tree before the f10b080 rebase, same v2 code; a rebased re-run gave the same 10-day tables)**

| | |
| --- | --- |
| Seat attacks | 3: N3-P1 -> N1-P5 CargoTran (day 14, destroyed, P5 pods); N3-P1 -> Ferrengi Assault Trader `ferr_18_2_728` (day 18, destroyed, +2,000 cr bounty); N3-P2 -> N2-P4 BattleShip (day 20, destroyed, P4 pods) |
| Ferrengi kills | 1 |
| N3 fighters at end | P1 1,500, P2 1,500 (arming cap) |
| Net worth | N3-P1 1,512,793; H-P6 1,498,667; N2-P3 1,388,140; N2-P4 1,172,132; N3-P2 952,145; N1-P5 679,293 (spread 833,500) |
| Exceptions / rejected | 0 / 0 |

N3 still trades: 516 and 467 sells, against 433-496 for the N2s.

**Seed 20260925, 10 days (QC add-on)**

| seat | before NW | after NW | before hull | after hull |
| --- | --- | --- | --- | --- |
| N3-P1 | 852,091 | 763,303 | battleship | battleship (857 ftrs) |
| N3-P2 | 791,606 | 764,176 | battleship | battleship (643 ftrs) |
| N2-P4 | 708,296 | 552,131 | cargotran | cargotran |
| H-P6 | 231,844 | 491,199 | scout_marauder | scout_marauder |
| N1-P5 | **41,116** | **398,333** | scout_marauder | cargotran |
| N2-P3 | **40,392** | **673,633** | scout_marauder | cargotran |

Seat attacks 0 / 0. Net-worth spread 811,699 -> 365,843. The day-1 Ferrengal mine deaths (P1, P2, P3, P5) happen in both runs.

## Pins

- All tw2002 `*_MODE` flipped to legacy (`tests/fed_legacy_digest.py`, N3,N2,N1,H, seed 250925, 3 days): `00135a9202e44a0e085ce978` on ad21ac6 and on this tree (unchanged since da25c47; `test_ship_tw_legacy_is_unchanged`).
- Only this slice's seven switches flipped, everything else at defaults: `5e29f9528d7e5000218b575a`, the same as f10b080 at defaults. This slice is fully behind its switches. New test: `test_fullgame_fixes_v2_switches_off_equal_the_base`. Before the rebase, the same check on ad21ac6 gave `9b607d3dae940c0b1a69f6d7` on both sides.
- Single-mode legacy pins recorded on earlier parents now flip this slice's seven switches too, following the convention `CAPTURE_MODE` / `PLANET_TRADE_MODE` set. Their tw2002 defaults change the N3 game. The goldens are unchanged: `test_tow_legacy_is_unchanged` (`5032bedfb3722133d47b18eb`), `test_planet_trade_legacy_is_unchanged` (`77c7d444a0965a2c40cffcca`), `capture_legacy_pin`.
- The legacy prompt/rank fixtures in `test_class0_terra_qc_v1` and `test_experience_alignment_v1`, and the legacy-flag list in `test_agency`, now flip the v2 switches (their pins predate this slice).
- New: `tests/test_fullgame_fixes_v2.py` (29 tests).
