# v311 default-profile soak

Plan only. Read on `feature/grokbot-player` at `513da8f0e61981fdee997ba50d17ffd555ebe3ed` (`docs: P3 readiness onto tip #410`, #411). Parent is `f178e0d8a00c50b60384b04f10c4aa023f801197` (`docs: stills inbound map through #409`, #410), whose parent is `e35e064ca67ac000239d6ef3a2d9bb47266c1b63` (`docs: batch-5 readiness onto tip #408`, #409). #411 changes only `docs/plans/cockpit-ship-stage-p3-readiness.md`. This note leaves that file alone. The grade map, the #408 switch inventory, and the profile defaults cited below are the same bytes as on #410. This file does not change live behavior.

A difference from TWGS 3.11 stays only where a cited plan already names it and leaves the switch at its stored value, or where the v3.11 profile leaves a helper out on purpose. MBBS breaks a tie only where those plans already use it.

## The gap

Two defaults sit side by side.

The stored default is legacy. In `src/tw2k/engine/constants.py`, `V311_PROFILE` is `"legacy"` and `TW2002_LIVE_PROFILE` is `"legacy"`. `docs/plans/gap-map-refresh-v6.md` grades a row Match-behind-flag when the TWGS 3.11 rule is coded and the named switch stays off until `V311_PROFILE` is `"v311"`, unless the profile section says that helper is left out on purpose. A process that never sets the profile still runs those stored values.

The new-game form already asks for the profile as an overlay. `src/tw2k/public/pages.py` `new_game` opens Rule set at `rules` `"v311"`, labeled `v3.11 (recommended)`, with `Legacy (this project)` as the other choice. `src/tw2k/public/security.py` defaults `rules` to `"v311"`. The profile line on that form says the choice is the profile the new game will use, and that it does not change the stored defaults. `src/tw2k/public/workers.py` `switch_overlay` sets `V311_PROFILE` to `"v311"` only when `rules` is `"v311"`. The same function also sets `DAY_ROLL_CLOCK_MODE` and `LEGACY_DAY_CLOCK_MODE` to `"live"` for every lobby game. A Legacy rules game from that form additionally sets `PORT_STOCK_FIDELITY_MODE` and `SEAT_IDLE_START_MODE` to `"live"`.

A pure v3.11 profile is `V311_PROFILE == "v311"`. That selects `V311_PROFILE_HELPERS` and leaves each switch's stored string where it is. `docs/plans/v311-profile-v1.md` heads that set "165 helpers". The dict at this tip has 165 entries. The pure profile also leaves out the switches in that file's "Left as they are" table. `docs/plans/mbf-switch-test-coverage.md` names the same intentional offs: `ALLIANCE_MODE`, `GOLD_ALIEN_MODE`, and `UNIVERSE_TOPOLOGY_MODE` stay off; `ECON_WIN_MODE` stays legacy so the 100,000,000 credit finish remains (R14 A); `ALLIANCE_OFF_MODE` is the GAP 14.6 switch the profile does select. Six switches already store the 3.11 value, so they are outside this gap: `PLANET_ECONOMY_MODE`, `FED_MODE`, `DEATH_MODE`, `SHIP_TW_MODE`, `ECONOMY_SCALE_MODE`, and `CLASS0_EXTERN_PLANET_RULE`.

The constant flip, `V311_PROFILE = "v311"` inside `constants.py`, is the step `docs/plans/future-stages-v1.md` calls R-4. This note does not take it. The form overlay is the per-game path that already exists.

## Grade status

The every-row list in `docs/plans/gap-map-refresh-v6.md` is 171 ids. Counted on this tip: 75 Match, 96 Match-behind-flag. That list has no Partial, Different, Missing, or Ben-decision grade. The counts table in the same file is Match 75, Match-behind-flag 96, Partial 0, Different 0, Missing 0, Ben-decision 0, total 171. `docs/plans/GAP_MAP.md` points at those live totals and says v6 calls no row Partial. The October 3 grid in that file (9 / 34 / 59 / 69) is the old picture.

There is no row 5.16, 7.1, or 8.5, which is why the id count is 171. The v5-to-v6 diff table still prints 6.12 as Partial. The every-row line grades 6.12 Match, and the counts table sets Partial to 0. This note follows the every-row list and the counts table.

## Switch inventory (#408)

`35817fc192e39a3b9b81c458fdf04e2acafd191b` is #408, the parent of #409. It added `docs/plans/mbf-switch-test-coverage.md` and `tests/test_mbf_switch_literals_v1.py`. That plan is the inventory: 96 Match-behind-flag rows, 120 switches named on those rows plus `QUASAR_ATM_ORDER_MODE` and `ATTACK_TURN_MODE`, 120 covered. The table at this tip has 120 switch rows. This note does not edit that plan or that test.

The four new tests set the switch itself and leave `V311_PROFILE` and `TW2002_LIVE_PROFILE` at `"legacy"`. The numbers below are the assertions in `tests/test_mbf_switch_literals_v1.py` and the Findings section of the #408 plan. This note did not re-run them.

| Switch | 3.11 with the switch set and both profiles legacy | Legacy beside it | Test |
|---|---|---|---|
| `FED_TOW_LIMIT_MODE` | tow limit 50; a ship with 51 fighters is towed, a ship with 50 stays | `fed_tow_fighter_limit()` is 98; stored `FED_TOW_FIGHTER_LIMIT` stays 98 | `test_fed_tow_limit_live_tows_above_50_and_legacy_stays_98` |
| `FEDSAFE_FIGHTER_CAP_MODE` | more than 50 fighters removes FedSpace protection; 50 stays safe | legacy ignores the fighter count (51 fighters still fedsafe) | `test_fedsafe_fighter_cap_live_is_50_and_legacy_ignores_fighters` |
| `TAX_RULE_MODE` | 10 percent at 50,000 or more, alignment above 0 (`tax_terms()` is 10, 49999, 1) | 5 percent over 100,000 (`tax_terms()` is 5, 100000, 0) | `test_tax_rule_v311_is_ten_percent_over_49999_and_legacy_stays_five` |
| `TRADE_IN_PARTS_MODE` | itemised merchant-cruiser receipt total 34,844 | 25 percent of the sticker | `test_trade_in_parts_live_itemises_and_legacy_stays_25_percent` |

## Before the stored default moves

The stored default stays `"legacy"`. Before anyone sets `V311_PROFILE = "v311"` in `constants.py`, all three bars below are true. This file meets none of them. It only writes them down.

### Suite pins, both profiles left at legacy

A legacy run still matches the written pins, and a test that sets both profiles to `"legacy"` still owns them:

- Bank pin `9b607d3dae940c0b1a69f6d7`, named in `docs/plans/v311-profile-v1.md` and `docs/plans/V311_SOAK_REPORT.md`.
- 10-day action digests `24863a3d` (seed 250925) and `98a47c8a` (seed 4242), rejected 0/0, same two plans.
- The four literal tests above still pass with both profiles at `"legacy"`.

This note did not re-run the suite. R-4 in `docs/plans/future-stages-v1.md` is the later step that records new pins and keeps these pins in a test that sets `"legacy"` explicitly.

`docs/plans/gap-map-refresh-v6.md` records a helper check on `60b17fef`: with `V311_PROFILE` set to `"v311"` after import, 114 helpers in `V311_PROFILE_HELPERS` returned true. This tip's dict has 165 entries, and the profile doc heading says 165. The suite bar for a later flip re-checks the dict at the tip where the flip is proposed, inside the test process. This note did not run that check.

### Playtest soak with Player of Games

`docs/plans/COMMANDER_NEXT.md` gives PoG (Player of Games) gameplay and playtests. Dev does not drive seats. Before the stored default moves, Player of Games plays one new game created with Rule set left on `v3.11 (recommended)`. That game uses `switch_overlay`. It does not write the stored flags. The four contrasts above should show the profile-on numbers: tow above 50, FedSpace protection lost above 50 fighters, tax of 10 percent at 50,000, itemised merchant-cruiser trade-in of 34,844.

A second new game on `Legacy (this project)` is the form-level rollback reading for the profile. `switch_overlay` omits `V311_PROFILE` on that path. The day-clock switches, and `PORT_STOCK_FIDELITY_MODE` plus `SEAT_IDLE_START_MODE`, are still set, so that lobby game is a different object from the suite-pin process. The suite pins stay the reading for a process that never applies `switch_overlay`.

`docs/plans/V311_SOAK_REPORT.md` (NOTE 160) is an in-process soak. Its own text leaves the stored default at `"legacy"` and counts 133 helpers. It is an older scripted run. It is not a Player of Games lobby playtest at `513da8f0`, and it does not clear this gate. No playtest result is claimed here.

### Rollback stays the switches

Rollback of the profile on a new game is the Legacy choice on the form, which leaves `V311_PROFILE` unset in the overlay. Each Match-behind-flag switch keeps its stored default, so that game comes back without an edit to `constants.py`. The four tests are the written legacy numbers beside the 3.11 numbers.

A pure-profile flip leaves the intentional offs off. Setting `ALLIANCE_MODE`, `GOLD_ALIEN_MODE`, `UNIVERSE_TOPOLOGY_MODE`, or `ECON_WIN_MODE` to its on value would be a different game from the one `docs/plans/v311-profile-v1.md` and the #408 inventory write down.

## What this file does

It adds this plan. It leaves `V311_PROFILE` at `"legacy"`, leaves every switch default where the tip has it, and leaves the new-game form on the overlay it already uses. Live behavior is the tip's behavior.
