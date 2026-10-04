# Economy scale tests

task_id: ports-economy-scale-tests-v1

Tests only. No game rule changed. Each test was proved by planting the bug, watching that test fail, and putting the line back.

## Holds already owned

`hold_total_price` is `B*q + 20*(q*held + q*(q-1)/2)`. Buying 5 holds when the ship already has 20 costs 2955 on day 0 (B 151) and 3445 on day 9 (B 249). Dropping the `q*held` term failed `test_five_holds_on_top_of_twenty_keep_the_owned_term`. The StarDock handler charges that same total.

## Fighter wave

Hand values of `200 + sin(day/87*2*pi)*40`, rounded: day 0 is 200, 10 is 226, 30 is 233, 44 is 199, 65 is 160, 87 is 200, and day 100 is 232. Each of those stays inside 160 to 239, so the clamp is not what picks the number. Day 22 rounds to 240 and the function returns 239, so the clamp does decide that one day. Changing the amplitude from 40 to 90 failed `test_fighter_wave_matches_the_hand_sine_and_the_clamp_is_idle`.

## Ship purchase

A real `buy_ship` charges `ship_cost(new) - 25 percent of ship_cost(old)`. Merchant Cruiser to Battle Ship is 88500 - 10325 = 78175. Scout to CargoTran is 51950 - 3987 = 47963. The legal list `trade_in` and `net_cost_by` equal the credits that moved.

The Merchant Cruiser stored cost and `ship_cost` are both 41300, so a legacy trade-in on that hull does not move. The Scout stored cost is 75000 against `ship_cost` 15950, so the Scout leg is the one that fails. Charging the stored Battle Ship cost (880000) or the stored CargoTran cost (43500) fails the same test. Both plants failed `test_buy_ship_charges_ship_cost_trade_in_and_shows_that_net`.

## Net worth

A fresh Scout with 20 fighters and no shields is credits plus `int(ship_cost * 0.5)` plus `20 * 50`. Using the stored Scout cost failed `test_fresh_ship_net_worth_uses_ship_cost`. Fighter value in net worth stays 50.

## Empty shelf

On a generated universe the seat stands at a port that sells fuel and buys organics, with fuel stock 0. The legal buy qty is 0. Remembered `known_ports` current is 0. The brain does not send a buy. `_empty_shelf_buy` is true for a qty-0 buy. Making that function always return false failed `test_empty_shelf_and_unseen_port_are_not_bought`.

The same seat with this port left out of `known_ports` is the unseen case. Treating `seen is None` as stocked (so the function returns false) failed that test too.

## CargoTran guard

At StarDock with credits one below the CargoTran net, the brain sends no `buy_ship`. The inner `if v.credits < net: return None` is reached only when the computed net still looks affordable and the legal list's net is higher. Removing that guard failed `test_stardock_does_not_buy_a_hull_the_list_prices_above_credits`.

## Files

`tests/test_economy_scale_tests_v1.py` and this doc. No `src` change.
