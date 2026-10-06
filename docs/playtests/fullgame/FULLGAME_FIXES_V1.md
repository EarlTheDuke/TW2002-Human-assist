# Full-game fixes v1 (net worth of hardware, LLM buy reserve)

Slice `fullgame-fixes-v1`. Findings from the seed 250925 full multi-bot game (commit 2756bdc, 8 days x 50 turns, 250k start, P1-P2 Kimi, P3-P4 Qwen, P5 N2, P6 N3, P7 Grok via xAI). Sources under `C:\Users\sugar\tw2002_reference\`. Target TWGS 3.11; MBBS breaks ties.

## What happened to the Grok seat

| day | action | credits after | net worth |
| --- | --- | --- | --- |
| 1 | `buy_ship battleship` (88,500 less 10,325 trade-in) and a density scanner | ~170k | 217k |
| 2-3 | five round trips, 80 holds, 4 turns a warp | 172,116 | ~217k |
| 4 | `buy_equip fighters 815` = 171,965 cr (211 each) | 151 | 88k |
| 5-8 | 1-2 unit organics trades (+5 to +10 cr a trip), then waits | 151 | 88k |

Root causes:

1. **Net worth counted a fighter at 50 while StarDock charged the 160..239 wave.** 815 fighters cost 171,965 and added 40,750, a 131k drop. Shields had the same gap once Class 0 put them on the wave (priced ~200, counted 10).
2. **The hints pushed the buy.** Every deep-space turn said `UNDEFENDED IN DEEP SPACE ... 500 fighters = N cr`. At StarDock the hint said `StarDock max buy_equip now: fighters 815`. Grok's next goal became "buy max fighters (815)". Nothing said how much cash to keep, and nothing said what a fighter is worth on the scoreboard.
3. **The system prompt's price sheet was stale:** `fighters 50 cr each`, `shields 10 cr per point`. Kimi and Qwen sized their buys on it: "380*50=19,000cr" was really 77,140 cr. They still kept 100k+ because they had planned genesis and colonist buys. N2/N3 buy defence only above 100k credits, cap it at 400 fighters, and keep a cash buffer (`DEFENSE_CASH_GATE`, `cash_buffer`).
4. The Battleship's 4 turns a warp left Grok with 3-turn leftovers at day end. It waited them out 11 times.

## Net worth: before and after

TW2002 has no net-worth score. Players rank by experience and alignment (GAP_MAP 12.5: "scores are exp/alignment ranks"; Bible, EIS TradeWars.html). Our net worth is our own metric, so the rule only needs to be consistent and documented.

What the sources say about hardware value:

- Fighter price: `price = (base + amp/2) + sin(day/period * 2pi) * amp/2`, base 160, amp 80, period 87, so 160..239 with a midpoint of 200 (Hekate, `stardock_manuals_and_text_docs/Misc_FigShieldPrices.txt`). Shields run the other way (CLASS0_TERRA.md t13; numbers UNVERIFIED).
- No sell-back price for fighters or shields. The shipyard takes "fighters, accessories, mines, etc." in a trade-in at an unstated price (Gypsy_Big_Dummies_Guide.html Shipyards <B>; EIS ShipyardMenu.html). UNVERIFIED.
- A base hull resells for about 50-90 percent of its cost: Battleship 88,500 / 75,679, CargoTran 51,950 / 25,684 (Slice-10_Slice_War_Manual.txt, V2 ship specs). Our net worth uses 50 percent; our trade-in uses 25 percent. Both are unchanged.

| item | before (all modes) | after, `NET_WORTH_MODE = "tw2002"` | after, `legacy` |
| --- | --- | --- | --- |
| hull | 50% of StarDock price | 50% (`NW_HULL_FRACTION`) | 50% |
| ship fighter | 50 (`FIGHTER_COST`) | 100 = `NW_HARDWARE_FRACTION` 0.5 x `NW_WAVE_MID_PRICE` 200 | 50 |
| ship shield | 10 | 100 (same rule; mirror wave) | 10 |
| planet fighter | 50 | 100 | 50 |
| planet shield | 10 | 1,000 = 10 ship shields (`PLANET_SHIELD_SHIP_COST`), the deposit rate | 10 |
| mines, photons, probes, genesis, scanners, cloaks, v2 gear | at cost | at cost (unchanged) | at cost |

Wave-priced hardware counts the same share of its price as the hull. Depositing fighters (1:1) or shields (10:1) on a planet no longer moves net worth. If StarDock's price is flat (`ECONOMY_SCALE_MODE` legacy for fighters; `SHIELD_PRICE_MODE` flat or `CLASS0_MODE` legacy for shields), the old 50 / 10 stay. That is still the price paid.

Grok's buy under the new rule: 815 x (211 - 100) = 90,465 lost, not 131,215. Net worth after the buy would have been about 129k, not 88k. It is still a bad buy. The reserve hint below is what should stop it.

**The planet growth dividend keeps its old basis.** `planets._pay_planet_value_tax` pays 30% of each day's new planet value. If that read the new values, planet fighter production would pay twice the credits. That changes the economy, not just the score, and it made N1 beat N2 on seed 230923 in `test_n2_day10_beats_n1_and_keeps_organics`. The dividend and `last_tax_value` now read `victory.planet_tax_value(planet)`: fighters 50, shields 10, in every mode. Credits do not change.

## Buy reserve (LLM guardrail)

Not a TW2002 rule. `BUY_RESERVE_MODE = "tw2002"` (default) / `legacy` (off).

- `working_capital_reserve(holds) = max(BUY_RESERVE_FLOOR_CREDITS 20,000, holds x BUY_RESERVE_CR_PER_HOLD 200)`. That is one full trade load at about twice the equipment base (102).
- Action hint at StarDock and at Alpha Centauri / Rylos, shown only when buying the max of fighters or shields would dip into the reserve: for Grok's day-4 state (Battleship, 172,116 cr) the hint now reads `StarDock max buy_equip now: fighters 815, shields 750; ... Working capital: keep >= 20,000 cr after fighter/shield buys (trade stake for 80 holds); max that keeps it: fighters 720, shields 750. Today fighters cost 211 cr, count 100 toward net worth; shields cost 189 cr, count 100 toward net worth. Buy defence for a planned need, not to spend the bank.`
- The `UNDEFENDED IN DEEP SPACE` hint adds `Each counts 100 cr toward net worth; keep 20,000 cr working capital.`
- System prompt price sheet: fighters `160-239 cr each (daily wave; today's price is buy_equip unit_price_by; each counts 100 toward net worth)`; shields the same on the opposite wave; plus one working-capital line.
- `LLM_BUY_RESERVE_SOFT_CAP = False` (default). When True, `agents/llm.py::apply_buy_reserve_cap` cuts an LLM seat's fighter or shield buy to the qty that keeps the reserve. If no qty fits, the seat waits. Left off: the hint should be enough, and the cap changes what the model chose. Turn it on if a game shows a seat ignoring the hint.

## Combat: why nobody fought

24 Ferrengi spawned. There was 1 fighter deploy (Qwen, defensive), no attacks, no robs.

1. **Rob / steal did not exist on 2756bdc.** `rob-steal-v1` (430b8b9) landed later. On today's tree they need alignment <= `ROB_MIN_ALIGNMENT` (-100, TW2002 r1). Every seat trades honestly and stays >= 0, so rob and steal are never legal. N2/N3 `_rob_steal` checks the same gate. This is working as designed.
2. **No seat ever shared a sector with a Ferrengi.** Replaying warps, autopilot and `ferrengi_move` from events.jsonl finds 0 seat/Ferrengi co-locations. That is 24 raiders in 1,000 sectors, moving once per day tick, while seats ran short loops near StarDock and their planets. `attack` only lists targets in your sector.
3. **Seats did share sectors and still did not attack.** There were 32 sector/pair co-locations outside FedSpace: P5+P6 at 428 (41 events), P3+P4 at 401 and 452 (76), P1+P2 at 493. N2/N3 never attack a ship: `seat_brain._ship_attack` is never called ("Other ships are not hunted this slice"). They only attack to clear a fighter challenge. The LLM prompt frames attack as optional ("These tools are SITUATIONAL - a solo trader who never allies or attacks can still win"). Attack costs 5 turns, and the alignment/XP hit for attacking a good trader is spelled out. The TRAILING nudge ("Acting on the gap is optional") fired for Grok from day 4, but Grok never met anyone. The deep-space hints sell Ferrengi as a threat to defend against, not a target.
4. The old Ferrengi did not seek out players. ferrengi-aliens-v1 (9dbe56b) adds boarding / tribute, so the next full game should see encounters without any prompt change.

No combat code or prompt was changed. Making seats aggressive is a balance decision, not a safe fix.

## Pre-existing exploit found (not fixed)

The planet dividend counts deposited defence as growth. Deposit 5,000 fighters on an owned planet, then tick: 75,000 cr payout. Withdraw (the baseline drops, with no clawback), deposit again: 75,000 cr again, every two days. Reproduced on da25c47. Suggested fix for a later slice: `deposit_planet_defense` / `withdraw_planet_defense` move `last_tax_value` by the transferred tax value, so only production and growth pay.

## Pins

- All tw2002 `*_MODE` flipped to legacy (`tests/fed_legacy_digest.py`, N3,N2,N1,H, seed 250925, 3 days): `00135a9202e44a0e085ce978` on da25c47, d632aae and this tree. This is the suite's `test_ship_tw_legacy_is_unchanged`.
- Only `NET_WORTH_MODE` and `BUY_RESERVE_MODE` flipped, everything else at defaults: `9d2ddd075ab430e78e1a7885` on this tree. That equals d632aae (the base after the rebase) at defaults, so this slice is entirely behind its two switches. Before the rebase it was `b9a52b96095f12c7c453151b`, equal to da25c47 at defaults. QC check, not in the suite.
- Legacy fixtures that pin prompts and observations predate this slice and now flip `NET_WORTH_MODE` / `BUY_RESERVE_MODE` too (test_agency, test_class0_terra_qc_v1, test_experience_alignment_v1, test_scanners_hidden_info_v1). tw2002-mode value tests now read `K.nw_*` (test_phase_abc g5/g6, test_economy_scale_tests_v1). The dividend tests read `planet_tax_value`. The `game_over` media fixture moves +1,000 (20 starting fighters x 50).
- New: `tests/test_fullgame_fixes_v1.py` (20 tests).

## 10-day scripted match (N3,N3,N2,N2,N1,H, seed 250925)

`scripts/run_scripted_match.py --seats N3,N3,N2,N2,N1,H --seed 250925 --days 10` before = da25c47 and d632aae (identical tables), after = this slice before and after the rebase onto d632aae (identical tables):

| seat | net worth before | after | credits (both) | sells (both) | rejected |
| --- | --- | --- | --- | --- | --- |
| N3-P1 | 616,659 | 636,759 | 378,712 | 239 | 0/0 |
| N1-P5 | 338,175 | 345,875 | 173,815 | 317 | 0/0 |
| N3-P2 | 320,464 | 342,314 | 148,931 | 253 | 0/0 |
| N2-P4 | 263,308 | 272,058 | 47,611 | 276 | 0/0 |
| N2-P3 | 122,573 | 128,173 | 25,694 | 295 | 0/0 |
| H-P6 | 64,211 | 65,211 | 41,441 | 103 | 0/0 |

Credits, sells, ships, planets, deaths and rejections are identical, so the bots play the same game. Net worth rises only by the revaluation of fighters and shields they hold (+1,000 for the 20 starting fighters). The order is unchanged.