# Seat brain planet retune

The planner was still scoring a finished citadel as a free garrison. Credit costs already came from `CITADEL_TIER_COST`, which is what the engine charges while `CITADEL_COST_MODE` is `credits`.

## Where the old gift or the credit cost was used

| Place | What it did | Now |
|---|---|---|
| `_defense_value` | `1000 * level * 50 + 250 * level * 10` from level 2 up | Gift constants times those same purchase prices. Both constants are 0, so the value is 0. |
| `_tier_bonus` | Difference of that garrison between levels | The next tier's credit cost plus its colonists at 10 credits each. L1 stays a build visit. L2 is 30000, not 105000. |
| `_planned_tier` | A ferry when the garrison bonus was above 0 | Still a ferry when the credit tier needs colonists. The score is the 30000 credit cost, not the garrison. |
| `_genesis_expected_value` | Added the L2 garrison when enough days remained | Adds the L2 credit and colonist cost, not fighters. |
| `_ferry_for_planet` | Multiplied an L2 haul by 8 because of the fighter grant | No multiplier. The haul is worth its credit cost per turn. |
| `_opt_build` | Spent the trade float when the bonus was at least 100000 | The L2 score is 30000, so the float stays put. |
| `_opt_genesis` | Waited for every world to reach L2, described as the fighter grant | Still waits for citadel level 2. That is the L2 credit tier `_unfinished_l2_cash` already reserves, not a garrison. |
| `next_tier`, `_citadel_reserve`, `_unfinished_l2_cash`, `_genesis_trip_cost`, `_genesis_affordable_now` | Credit and colonist costs from `CITADEL_TIER_COST` | Unchanged. L1 is 5000 credits and 1000 colonists. L2 is 10000 credits and 2000 colonists. |

The planner does not emit `planet_destroy`. A build it cannot afford stays off `_citadel_ready`, which checks the credit cost before the action is chosen.

## Before and after

Old L2 garrison score: 1000 * 2 * 50 + 250 * 2 * 10 = 105000. That made an L2 ferry and an L2 trip win over trade.

| Choice | Before | After |
|---|---|---|
| Value of reaching L2 | 105000 free fighters and shields | 30000, which is 10000 credits plus 2000 colonists at 10 each |
| Ferry to unlock L2 | planned, then multiplied by 8 | planned, no multiplier |
| L2 credit cost kept in reserve | 10000 | 10000 |
| Seed 250925 day-10 net worth | bar 140000 | N3 149601, N2 ladder 134270, ferry 9.2%, citadels 1, 2, 2 |
| Bar | 140000 | 145000 |

Update 2026-10-05: 149601 was the legacy 18 / 25 / 36 table and an older brain. The same seed on the legacy table with today's brain finishes at 478,853. On the corrected tw2002 table (26 / 56 / 102) N3 finishes at 941,555, and the bar is a 650,000 to 1,450,000 band ([ECONOMY_CALIBRATION.md](../ports/ECONOMY_CALIBRATION.md)).

Scoring the haul at 0 raised that seed to 243704 and cut the ferry to 0%, and the colonist haul tests failed. That score was not kept.

Fighters the seat buys are 50 credits each. Shields the seat buys are 10 credits each. Neither is added when a citadel finishes.
