# Planetary Trade Agreement (slice 54, planetary-trading-v1)

Status: built behind `K.PLANET_TRADE_MODE` (`"tw2002"` default, `"legacy"` = the slice-51 game + bots QC fixes, pinned).
Code: `src/tw2k/engine/planet_trade.py` (eligibility, quote, lot price, haggle on the total, apply, legal spec),
one dispatch entry in `runner.py` (`_bind_planet_trade`; the refused-counter turn and the flee penalty reuse the trade
rules in `apply_action`), `legality.py` (verb after the tow verbs), `observation.py` (port block
`planet_trade_available`, `PLANET_TRADE` event facts / feed switch), `prompts.py` (`_PLANET_TRADE_NOTE`),
`server/harness.py` (`/rules` verbs), `seat_acceptance.py` (validator), `seat_brain.py` (`_planet_trade`),
`web/bot.js`, `web/app.js`. `economy.py` is only read (no ship-trade change).
Tests: `tests/test_planet_trade.py`, `tests/test_planet_trade_legacy_pin.py` (+ `test_parity_s4` builder,
`test_parity_s6` verb count, legacy fixtures that pin the system prompt / goldens).

Sources (under `C:\Users\sugar\tw2002_reference\`): EIS = eis_tw2002_v3_docs Navigate.html 55-75 (also GYPSY 136,
TWINSTR 229); PTW = docs wiki Planetary_Trading.html 76-106 (port menu transcript); PTG = docs wiki
Planet_Trading.html; MBBS = Someguy_MBBS_manual.txt 960-1012; REV = classictw_museum_wiki revision history
135-139 ("100% Planetary Trading"); CABAL = cabal glossary.html 289-291, planets.html 603-612, economy1.html 600-615.

## Rules table

| Row | Rule (short) | Tag | Source | Constant | Test |
|---|---|---|---|---|---|
| pt1 | Verb `planet_trade {planet_id, commodity, qty, offer?}` = port menu `<N>`; needs a port and the planet in the trader's sector | CONFIRMED | EIS Navigate 55-75, PTW transcript | `PLANET_TRADE_MODE` | `test_pt1_verb_sells_planet_stock_at_a_port_in_the_same_sector` |
| pt2 | Commodity ports only (repo classes 1-7 = original 1-8); StarDock (repo 8 = original 9) and Class 0 refused | CONFIRMED | PTW (trading-port menu) | - | `test_pt2_stardock_and_class0_have_no_agreement` |
| pt3 | Trader in his ship in the sector, alive, not landed; otherwise the ship-trade guards (a pod may trade, Ship Destroyed is out of turns) | CONFIRMED | PTW (menu reached by docking) | - | `test_pt3_landed_trader_refused_and_pod_trades_like_a_ship` |
| pt4 | Own planet, or a planet whose `corp_ticker` is the trader's (non-None) corp | CONFIRMED (corp: CABAL economy1); listing UNVERIFIED | CABAL economy1 600-615 | `PLANET_TRADE_WHO="owner_or_corp"` (alt `"owner"`) | `test_pt4_eligibility_matrix`, `test_pt4_who_owner_switch`, `test_pt4_planet_in_another_sector_refused` |
| pt5 | Sell only, and only what the port is buying ("We are buying up to 3000") | CONFIRMED | PTW | - | `test_pt5_sell_only_and_only_what_the_port_buys` |
| pt6 | Max = min(port buying room, planet stock); any 1..max, default max; 0 / above max refused with no turn | CONFIRMED | PTW "How many units ... [3000]?" | - | `test_pt6_qty_matrix`, `test_pt6_default_qty_is_the_offered_max` |
| pt7 | Port room exactly as `can_trade` computes a ship sell (maximum - current) | CONFIRMED | same port | - | `test_pt7_port_room_is_can_trade_capacity` |
| pt8 | One commodity per action; later commodities / ship trades follow the visit rule | CONFIRMED (we split per commodity) | PTW walks Ore -> Org -> Equ | - | `test_pt8_one_commodity_per_action`, `test_pt9_turn_matrix` |
| pt9 | Turn cost = `trade_turn_cost` (1 on the first trade of the visit, else 0); `begin_port_visit` like `_handle_trade` | CONFIRMED | MBBS "a single turn to sell the whole lot" | - | `test_pt9_turn_matrix` |
| pt10 | Lot price: "curve" = steps of 100 units, each at `port_buy_price` for the stock after the previous steps, summed; alt "end" (whole lot at the post-sale price) and "mbbs100" (whole lot at the opening bid) | **SOURCE-CONFLICT** (MBBS / REV 100% vs TWGS "isn't the best price"); TWGS % UNVERIFIED | MBBS 960-1012, REV 135-139, PTW | `PLANET_TRADE_PRICING="curve"`, `PLANET_TRADE_CURVE_STEP=100` | `test_pt10_lot_price_table_curve_end_mbbs100`, `test_pt10_curve_step_and_pricing_switch_reach_the_handler` |
| pt11 | Quote "We'll buy them for N credits"; offer defaults to N; legal list shows the quote for max | CONFIRMED (text) | PTW | - | `test_pt11_quote_is_what_an_accepted_lot_pays` |
| pt12 | One counter on the total: above N judged by `haggle_bound(N, mcic, "sell")`; inside -> paid the offer + good-counter exp; outside -> "We're not interested.", no sale, the visit turn (if any) spent; under N -> paid the offer | CONFIRMED (one prompt); bound reuse UNVERIFIED | PTW "Your offer [215,987]?" | `PLANET_TRADE_HAGGLE="as_ship_sell"` (alt `"no_counter"`) | `test_pt12_haggle_matrix`, `test_pt12_refused_counter_inside_a_visit_costs_nothing_more`, `test_pt12_no_counter_switch` |
| pt13 | Credits to the trader (not the planet or corp treasury) | CONFIRMED-by-context, destination UNVERIFIED | PTW / PTG | `PLANET_TRADE_PAYEE="trader"` (alt `"planet"`) | `test_pt13_pt14_payee_and_conservation`, `test_pt13_payee_planet_switch` |
| pt14 | Planet stock -qty; port stock +qty once (as one ship sale); port vault pays like a ship sale | CONFIRMED | - | - | `test_pt13_pt14_payee_and_conservation`, `test_pt14_port_stock_updated_once_and_matches_a_ship_sale` |
| pt15 | Experience as one ship sale of qty (port familiarity, trade award, first dock, good-counter exp per unit) | UNVERIFIED | - | `PLANET_TRADE_EXP="as_trade"` (alt `"none"`) | `test_pt15_experience_as_one_ship_sale` |
| pt16 | No alignment change | CONFIRMED-by-analogy | - | - | `test_pt16_alignment_unchanged` |
| pt17 | A trader busted at this port cannot negotiate; a corp-mate may sell the corp planet | CONFIRMED | CABAL economy1 600-615 | - | `test_pt17_busted_trader_refused_but_a_blue_corp_mate_may_sell` |
| pt18 | Fuel ore may be sold | CONFIRMED | PTW (advice only: "Don't sell fuel ore") | - | `test_pt18_fuel_ore_may_be_sold` |
| pt19 | Colonists and citadel credits never sellable | CONFIRMED | - | - | `test_pt19_colonists_and_treasury_never_sellable` |
| pt20 | Same sector only; a planet TransWarped in today may trade at once | CONFIRMED; no cooldown UNVERIFIED | EIS, MBBS Twarp round trip | `PLANET_TRADE_TWARP_COOLDOWN=0` | `test_pt20_planet_twarped_in_today_trades_and_cooldown_switch` |
| pt21 | Several planets: pick by `planet_id` | CONFIRMED | PTW "Negotiate agreement with which planet ?" | - | `test_pt21_several_planets_pick_by_id` |
| pt22 | No `universe.rng` draws (the ship sale draws none) | CONFIRMED (engine rule) | - | - | `test_pt22_no_rng_draws_like_a_ship_sale` |
| pt23 | The rest of the visit (ship prices, regen, class) sees the new port stock at once | CONFIRMED | - | - | `test_pt23_rest_of_the_visit_sees_the_new_stock` |
| pt24 | Event `PLANET_TRADE {trader, planet_id, port_sector, commodity, qty, price, quote, countered}`; seen like a port trade (actor + sector witnesses + spectator); facts never carry the planet's remaining stock | UNVERIFIED visibility | - | `PLANET_TRADE_FEED="public_summary"` (alt `"actor_only"`) | `test_pt24_event_visibility_and_payload` |
| pt25 | `victory.planet_stock_unit_price` unchanged (base price for unsold stock) | CONFIRMED | - | - | `test_pt25_victory_planet_stock_price_unchanged` |
| pt26 | Ferrengi, Feds, NPC ports unchanged; Ferrengi never negotiate | CONFIRMED by scope | - | - | `test_pt26_ferrengi_never_negotiate` |

Legal list == handler: `test_legal_list_matches_handler` (4 port / stock shapes; every listed planet x commodity x
qty in {1, max/2, max} succeeds at `lot_price`, the listed quote is what max pays, max+1 and every unlisted
pair are refused), `test_legal_list_absent_reasons_and_flee_penalty`.
Fog: `test_fog_rival_planet_never_shown_or_inferable`, `test_observation_port_flag`.
Bots: `test_bot_sells_organics_or_equipment_lot_at_the_quote_and_never_counters`,
`test_bot_never_sells_fuel_ore_and_respects_min_lot`, `test_bot_policy_off_and_legacy_never_use_it`,
`test_bot_action_passes_the_seat_validator`. Legacy: `test_legacy_mode_has_no_verb_key_event_or_prompt`,
`test_planet_trade_legacy_is_unchanged`.

SOURCE-CONFLICT: pt10 (`PLANET_TRADE_PRICING`: `"curve"` default = TWGS; `"mbbs100"` = MBBS / REV "100% Planetary
Trading"; `"end"` alternate). UNVERIFIED constants: `PLANET_TRADE_CURVE_STEP=100` (pt10), `PLANET_TRADE_WHO`
(pt4), `PLANET_TRADE_HAGGLE` (pt12), `PLANET_TRADE_PAYEE` (pt13), `PLANET_TRADE_EXP` (pt15),
`PLANET_TRADE_TWARP_COOLDOWN` (pt20), `PLANET_TRADE_FEED` (pt24).

## Verb, legal list, observation

`planet_trade {planet_id, commodity, qty?, offer?}`. The legal entry is always present under tw2002 (illegal with a
reason when there is no agreement here). When legal, `params.planets` = `[{planet_id, name, owner: self|corp,
sellable: {commodity: max}, quote: {commodity: lot price for max}, unit_bid: {commodity: opening bid}}]`,
plus `planet_id.choices`, `commodity.choices`, `qty.max_by[planet_id][commodity]`, `offer` and `turn_cost`
(and `flee_penalty_turns` after a flee). When illegal, `planets` is empty. The port block gains
`planet_trade_available` (same answer as the legal list). Refusal for a rival / missing / other-sector planet is
always "no such planet in this sector you can trade from".

## PLANET_TRADE_MODE pin

`K.PLANET_TRADE_MODE = "legacy"`: no verb in the legal list (dead-seat list included) or `/rules`, the handler
answers "unsupported action", no `planet_trade_available` key, no `PLANET_TRADE` event, no prompt paragraph, no rng
draws, bots never use it. `test_planet_trade_legacy_is_unchanged` compares `PLANET_TRADE_LEGACY_GOLDEN =
77c7d444a0965a2c40cffcca` (observation + prompt + action/result + event + end-of-day state digest, seats
N3,N2,N1,H, seed 250925, 3 days) recorded on origin 3b8f8e5 (slice 52 tip) before the slice. Same convention as the slice 48-51
pins (3 days in-suite); the spec's 10-day 6-seat digests were also compared outside the suite (Checks).

## Bots

`K.BOT_PLANET_TRADE_POLICY = "sell_surplus"`: the seat brain (N1-N3) checks `planet_trade` right before its
ladder. Docked with a legal agreement, it sells the biggest organics or equipment lot of at least
`BOT_PLANET_TRADE_MIN_LOT = 500` units at the quote (no `offer`, so no wasted haggle turn); never fuel ore
(`BOT_PLANET_TRADE_KEEP_ORE = True`); organics keep the colony's feed reserve (`max(75, 4 days of burn)`, the
stockpile-haul reserve). `"off"` never uses it. The H heuristic is not planet-aware (unchanged). LLM seats see the
verb in the legal list, the port block flag and the `_PLANET_TRADE_NOTE` prompt paragraph (same exposure as the
fleet / tow verbs).

## Deliberate differences

From the spec:
- The TWGS agreement percentage is unknown, so the 100-unit curve (pt10) stands in for it; `mbbs100` is one switch away.
- One commodity per action instead of one `<N>` menu session (Ore -> Organics -> Equipment); the visit turn rule
  makes the second and third commodity free, as in the original.
- Sell only (no buying onto a planet); corp planets eligible; credits to the trader; bots never counter and never sell ore.
- The public event shows the sale but not the planet's remaining stock.

Added in the build:
- Repo port classes: 1-7 trade, 8 is StarDock, 0 is Federal. "Classes 1-8" in the spec map to repo 1-7; StarDock /
  Class 0 are refused.
- An offer under the quote is paid at the offer (spec pt12). A ship sale under the list price still pays the list
  (economy.py unchanged); the difference is deliberate and only reachable by a seat that underbids itself.
- Good-counter experience is the ship formula on the per-unit bargain: `min(PORT_HAGGLE_XP_CAP, round((offer -
  quote) / qty))`.
- A refused counter (`We're not interested.`) is a `TRADE_FAILED` event (actor only) and does not open the port
  visit, exactly like a failed ship counter; it spends the visit turn if one was due.
- An escape pod may negotiate (the ship-trade guards let a pod trade; pt3 says reuse them).
- Like a port trade, a planet trade drops an engaged tow (SHIP_TOW.md tt11 "port"). tow.py is not edited (spec rule):
  `planet_trade.py` calls the public `tow.release(..., "port")`.
- The flee penalty applies to `planet_trade` as a port action (same as `trade`).
- `qty` may be omitted (PTW default `[max]`); the seat validator still requires it from bots.

## Planted bugs

`qc_bridge\ptrade_artifacts\patch\plants_pt.py` (same approach as slices 50/51: each plant is a one-anchor source
mutation applied in place, the slice tests run against it, then the original bytes are restored). pb22 is planted
twice (legality exposes the verb; observation exposes `planet_trade_available`), so 23 plants for 22 bugs.

**23 / 23 caught** on the first pass (pb1-pb21, pb22a, pb22b). Catching tests per plant are in
`ptrade_artifacts\plants.log`; e.g. pb13 (curve flat = mbbs100) and pb14 (every step priced at the pre-sale stock)
by `test_pt10_lot_price_table_curve_end_mbbs100`, pb18 (extra rng draw) by `test_pt22_no_rng_draws_like_a_ship_sale`,
pb20 (rival stock in the refusal) by `test_fog_rival_planet_never_shown_or_inferable`, pb21 (bot sells ore) by
`test_bot_never_sells_fuel_ore_and_respects_min_lot`.

## Checks (slice 54 build)

- PLANET_TRADE_MODE pin: `PLANET_TRADE_LEGACY_GOLDEN = 77c7d444a0965a2c40cffcca` recorded on origin 3b8f8e5 (slice 52
  tip; seats N3,N2,N1,H, seed 250925, 3 days) and matched by this slice with PLANET_TRADE_MODE flipped. First built on
  a54fa5b (golden `9b607d3dae940c0b1a69f6d7` there, also matched), re-pinned after rebasing onto slice 52. The
  single-mode pins of earlier slices now flip PLANET_TRADE_MODE too (same as slice 52 did for the tow pin):
  `test_tow_legacy_is_unchanged` flips TOW + CAPTURE + PLANET_TRADE (golden `5032bedfb3722133d47b18eb` unchanged)
  and `tests/capture_legacy_pin.py` sets PLANET_TRADE_MODE legacy (golden `76d447b221cd26ce16dcd3fd` unchanged). All-legacy pin unchanged
  (N3,N2,N1,H `00135a9202e44a0e085ce978`). Outside the suite, 6 seats N3,N3,N2,N2,N1,H, 10 days: PLANET_TRADE flipped
  `221826d9bd9a6a6c85668224` before and after; all-legacy `729097a6c16903bae284813a` before and after.
- Scripted match `--seats N3,N3,N2,N2,N1,H --seed 250925 --days 10` (`qc_bridge\ptrade_artifacts\ptrade_match.py`):

| Seat | NW before (a54fa5b) | NW after (slice 54) | ship trades | turns | planet trades | planet stock day 10 (ore/org/eq) |
|---|---|---|---|---|---|---|
| P1 N3 | 820,569 | 820,569 | 493 | 10,000 | 0 | 0 / 193 / 71 |
| P2 N3 | 316,312 | 316,312 | 462 | 10,000 | 0 | 141 / 93 / 26 |
| P3 N2 | 387,725 | 387,725 | 365 | 10,000 | 0 | 653 / 41 / 21 |
| P4 N2 | 471,830 | 471,830 | 412 | 10,000 | 0 | 138 / 176 / 32 |
| P5 N1 | 447,200 | 447,200 | 685 | 10,000 | 0 | 0 / 246 / 132 |
| P6 H | 604,003 | 604,003 | 2,477 | 10,000 | 0 | - |

  Rejected 0, seat exceptions 0, forced stops 0, violations 0. Planet trades 0, so net worth is unchanged to the
  credit. Why: the seat brain ferries its worlds' organics and equipment off every day (the stockpile haul), so no
  world reaches `BOT_PLANET_TRADE_MIN_LOT = 500` of a sellable commodity, and most genesis worlds are not under a
  port (solo N3 probe, seed 250925, day 10: 1 of 3 worlds sits under a port, a Class 7 BBB, holding 92 organics /
  46 equipment). Fuel ore piles up (P3 653) but the bots keep ore (PTW "Don't sell fuel ore").
- 5-seed `seat_brain_acceptance.py n3 --seeds 250925,20260925,230923,99,31`: output identical before and after
  (PASS, rejected 0; no planet trade in the solo runs either).
- QC lab (`ptrade_artifacts\qc_lab.py`, spec (d)), Class 3 port (sells ore, buys organics and equipment), planet
  3,000 / 3,000 / 3,000, merchant hull:

| step | result | credits | turns |
|---|---|---|---|
| sell 3,000 organics at the quote | ok | +214,700 | 1 |
| sell 3,000 equipment, same visit | ok | +391,100 | 0 |
| try fuel ore | refused "this port is not buying fuel_ore" | 0 | 0 |
| counter 100,716 on a 1,000-organics quote of 75,500 (bound 100,717) | ok, paid the offer | +100,716 | 1 |
| counter 100,718 (above the bound) | "We're not interested.", no sale | 0 | 1 |
| corp-mate sells 500 organics from the corp planet | ok | +38,200 | 1 |
| rival on the corp planet | refused with the "no such planet" text; legal entry illegal, no planets listed, `planet_trade_available` false; same text as a made-up planet id | 0 | 0 |
| busted trader | refused | 0 | 0 |

  Credits a turn: planet trade 605,800 for 6,000 units in 1 turn (101.0 a unit). Hauling the same goods by ship
  with the lab's 20-hold hull (land, load, lift off, sell): 4,000 units sold in 1,000 turns for 417,040 (104.3 a
  unit, 417 a turn). The curve pays slightly less a unit than single shiploads and is ~1,450x faster a turn, which is
  TWGS's "isn't the best price but it is quick".
