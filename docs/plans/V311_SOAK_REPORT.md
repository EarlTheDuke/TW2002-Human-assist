# V311 soak (NOTE 160)

Ten-day games with `V311_PROFILE=v311`, so every helper in `V311_PROFILE_HELPERS` is on together (132, including the stacked rows 177-180). The stored default stays `legacy`. The profile-off action digests and the bank pin were re-run after the stack and still match.

## How the games were run

`scripts/v311_note160_soak.py` builds one universe the way the server does (`opening_loadout`, then `grant_starting_planet` while the profile is on) and drives it in process. `regen_now` is held at 0, and a finished day refills turns, same as `scripts/run_scripted_match.py`. `AI_COCKPIT_SEAT_MODE` is `tw2002` in that process only. The profile does not turn that switch on, and the script does not write the stored value.

Lineup, in seat order:

| Seat | Who | Decides |
|---|---|---|
| P1 | AI cockpit | cockpit scripted trader (`tw2k.agents.cockpit_seat.SeatBrain`), no model key |
| P2 | AI cockpit 2 | the same trader, its own notes |
| P3 | N3 | code bot |
| P4 | N2 | code bot |
| P5 | N1 | code bot |
| P6 | H | heuristic code bot |

Universe 1,000 sectors, Ferrengi and planets on, 10 days. Seeds 250925, 4242, 99, and 7. Each action is checked for negative credits, bank, fighters, shields, cargo, and a cargo count that does not fit the holds, and for fighters past the hull room. Each day end also checks port stock, sector fighters and mines, planet colonists, treasury, quoted buy and sell prices, trade-ledger unit prices, experience, and alignment. A quoted price or a paid unit outside 1..100,000 is recorded. A net worth that grows past 20 times the day-1 figure, and by at least a million, is recorded.

The rendered-page trader (`scripts/ai_cockpit/trader.py`) was not in this loop. These two seats use the harness scripted trader, which posts the same action kinds through `apply_action`.

## Findings

No crashes, no exceptions, no negative stock, credits, or fighters, no impossible prices, no net-worth outlier, and no deadlock. Every seed finished day 10 with `game_over` false. No engine change came out of this soak.

| Seed | Day | What happened | Switches | Severity |
|---|---|---|---|---|
| 250925 | 1-10 | 5,681 actions, 0 rejected, 0 exceptions. All six seats used the 250-turn day. Highest net worth 254,444 (AI cockpit). | all 132 profile helpers | none |
| 4242 | 1 | N2 ends day 1 with 0 credits and net worth 24,322, then spends days 2-10 plotting and warping (468 plots, 271 warps, 1 trade). Net worth rises to 43,526. Credits never go negative. 5,688 actions, 0 rejected, 0 exceptions. | `STARTING_PACKAGE_MODE` (300-credit opening) with the rest of the profile. The empty pocket is spent cash, not a leak. | low |
| 99 | 5 | H reaches 0 credits on day 5 (was 10,710 on day 4) and stays at 0 through day 10 while still warping and trading. Net worth 24,094 then 35,972. 5,015 actions, 0 rejected, 0 exceptions. | profile on, including death and trade. Cash hit zero after a drop in net worth on day 4 (59,732 to 29,224) and did not go negative. | low |
| 7 | 10 | N3's two refused trades: "You only have 0 Fuel Ore in your holds." and "You only have 1 empty holds." The other 6,483 actions were accepted. 0 exceptions. N1 holds 9 to 11 credits all game and mostly plots. Highest net worth 258,683. | trade legality with the profile on (`HAGGLE_TABLE_MODE`, `COLONIST_UNITS_MODE`, `STARTING_PACKAGE_MODE`). The refusal matches empty fuel and one free hold. | low |

N1 on seed 7 and N2 on seed 4242 are poor, not stuck: they keep spending turns, and nothing forced a seat off after a string of zero-turn actions.

## Profile off

Same scripted match as the pin, seats N3, N2, N1, H, 10 days, profile left at legacy:

| Seed | Action digest | Rejected | Exceptions |
|---|---|---|---|
| 250925 | `24863a3d` | 0/0 | 0 |
| 4242 | `98a47c8a` | 0/0 | 0 |

Citadels: seed 250925 `{"P1": [2, 2, 2, 0], "P2": [0], "P3": [1]}`, seed 4242 `{"P1": [2, 0], "P2": [0], "P3": [2]}`. `tests/test_bank_tax_legacy_pin.py` passed in the same pytest run as the stacked note tests (32 passed).

## Stack

This branch is `feature/grokbot-player` plus the unmerged notes #83, #86, #87, and #88. Row 177 stays inactive-user deletion and row 178 stays the lobby timeout. Extra two-way lanes are row 179. The free Scout's re-entry fighters are row 180. Each switch still defaults to legacy and still turns on with `V311_PROFILE=v311`.
