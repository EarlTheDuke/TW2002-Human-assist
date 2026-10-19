# colonist-units-clarity-v1 (COMMANDER NOTE 101)

One colonist unit, checked from Terra through the citadel. No new switch. Rows 143 and 144 stay unused.

S1 section III, class M, prints Fuel Ore ratio 3, maximum colonists 30,000, max prod/day 15,000, max/day 5,000. Organics are 7 / 30,000 / 15,000 / 2,142. Equipment are 13 / 30,000 / 15,000 / 1,153. Section VII prints class M level 1 as Colo 1000. Ben's NOTE 19: the original planet display counts colonists in thousands. One Terra hold is 1,000 people, and that thousand is one planet unit. The live screen's 1,000,000 is those 1,000 units.

The free start is 45,000 + 65,000 + 81,000 = 191,000 people = 191 units. A Terra take of 30 holds is 30,000 people = 30 units. Level 1 wants 1,000 units. Both gifts are short of it. The cockpit was printing the people count with no unit name.

## Where the count lives

Checked with `V311_PROFILE` on, and again with it off. Under the profile the switches that already exist (`TERRA_COLONIST_MODE`, `CLASS_M_FIDELITY_MODE`, `CLASS_M_DROP_MODE`, `COLONIST_UNITS_MODE`, `COLONIST_NW_UNITS_MODE`, `PLANET_PROD_MODE`) are on together. Off, Terra stores one colonist per hold and a planet stores that same count. Nothing in the off path divides or multiplies by 1,000.

| Where | Unit under the profile | Example |
| --- | --- | --- |
| Terra pool and the hold | people | take 30 holds: cargo 30,000 people, 30 holds used, pool drops by 30,000 |
| Class M planet | people | those 30,000 land as 30,000 people = 30 thousands |
| Any other class | handbook thousands | those 30,000 land as 30 colonists; a remainder is refused |
| Growth and the class cap | thousands, stored as people on class M | 30,000 thousands per product pool (90,000 thousands across fuel, organics, and equipment). Half of one pool is the growth line |
| Production, class M | thousands, then the S1 ratio | 15,000 thousands on fuel (15,000,000 people) make 5,000 fuel. 3 thousands make 1. Ratios 3 / 7 / 13 |
| Citadel table | thousands in S1, people on a live class M | level 1 needs 1,000 thousands = 1,000,000 people. 999 thousands cannot start it |
| Net worth | thousands | 30,000 people on class M, or 30 handbook colonists on another class, score 30 times the colonist price. Cargo people score the same way |
| Planet card, citadel form, Terra form | the original label | `Colonists (1000s)` with the people count beside it |

No place applies a ratio or a cap to people while the citadel treats the same number as thousands. The class cap, the 3/7/13 ratios, fighter divisors, and the citadel table all divide class M people by 1,000 before they use the handbook figure. `COLONIST_UNITS_FIX_MODE` was not added.

## What the screen says

Behind `COCKPIT_LAYOUT=redesign` only. The planet card, the citadel form, and the Terra form say `Colonists (1000s)` and the people count when colonist clarity is on (the profile, or Terra live, or the colonist-unit switch, or the cockpit block). At 221 thousands the citadel sentence is:

`Level 1 needs 1,000 (thousands) colonists = 1,000,000; you have 221 (thousands); about 26 more Terra trips with 30 holds`

26 is the shortfall (779 thousands) divided by a 30-hold Terra take, rounded up. The note's "about 33" is the empty-world figure (1,000 / 30). The form uses the shortfall. The 30-hold haul is the note's example, not a published trip size (UNVERIFIED).

The same numbers are on the observation as `citadel_next_build` with `need`, `have`, and `unit`, omitted while clarity is off. `/bot` keeps a hidden `data-obs` span for that field and does not show it.

## Seat gaps

`price at a port you are not docked at` and `how stock moves price` are left alone. The original never prints them.

| Gap | Already on this branch | What this note adds |
| --- | --- | --- |
| Holds total and the rise per hold | `web/redesign.js` `holdTotalLine` already prints the typed total when `cockpit.hold_quote` is present (cockpit-gaps-v1). `COCKPIT_FIELDS_MODE` stays legacy and is not turned on by the profile, so a v3.11 seat never saw it and bought 5 at a time | `per_hold` on the quote, drawn after the total. The same quote is on `buy_equip` when `ACTION_RESULT_MODE=report` (already on under the profile) or the cockpit block is on |
| Verdict on the POST | `action_result_report()` already returns `ok`, `rejected`, `error`, `turns_spent` (`src/tw2k/server/harness.py` and `ExternalAgent.wait_result`) | the POST also carries `reason`, `credits_change`, `credits`, and `day`. The seat reads that answer and does not have to open status `last_result` |
| Counter offer as its own field | the redesign trade form already has `data-haggle="counter"` when the cockpit block is on (`haggleLines`) | while that block is off, `trade` params carry `counter` under the same report switch, and the form prints it as its own line |

The NOTE 95 two-day seat test (`tests/test_cockpit_ai_seat_v3.py`) is on `feature/grokbot-player` and is not on this branch. It gets rerun after PR #22 merges and this branch is rebased onto that tree.
