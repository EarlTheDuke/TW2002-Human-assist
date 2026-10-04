# Ship roster tests

task_id: ship-roster-hardening-v1

No new hull and no number change. The expected figures below are copied from `SHIP_ROSTER.md`. The tests do not read those expected figures out of the spec. Scout fighters stay 150. The Bible chart and OldBBS say 250. That other figure stays UNVERIFIED. It is not the yard number.

The one code change is the planet-offense wave. The original ten hulls still take max fighters and max shields from the legacy `SHIP_SPECS` table. A hull that table does not list uses `ship_specs()`, so the wave is not stuck at 1.

## What each test pins

| Test | Protects | Plant that fails it |
| --- | --- | --- |
| `test_chart_numbers_are_literals` | All 16 prices, hold caps, included holds, fighters, shields, mines, genesis, photons, and turns per warp. Scout fighters are the literal 150. | Scout `max_fighters` set to 250. |
| `test_tholian_shields_are_4000` | Tholian Sentinel shield cap is the literal 4000. | That ship's `max_shields` set to 1000. |
| `test_cargotran_warp_spends_four_turns` | A real CargoTran warp lowers `turns_today` by 4. | CargoTran `turns_per_warp` set to 3. |
| `test_every_hull_warp_spends_its_chart_turns` | A real warp for every hull spends the chart turns, including the Interdictor's 15. | Interdictor `turns_per_warp` set to 2. |
| `test_mine_cap_is_one_shared_total` | Armid, limpet, and atomic share one mine total. 30 armid plus 21 limpet on a Merchant Cruiser (cap 50) is refused. | The buy handler counts mines already aboard as 0. |
| `test_day_done_reads_the_tw2002_warp` | Server `_is_day_done` uses the tw2002 turns per warp. A CargoTran with 3 turns left is done for the day once a trade is also out of reach. An Interdictor with 10 left is done. Sixteen left is not. | `_is_day_done` reads legacy `SHIP_SPECS`. |
| `test_runner_warp_reads_the_tw2002_table` | The engine warp of an Interdictor spends 15, not the legacy miss that falls back to 2. | `_warp_cost_for` reads legacy `SHIP_SPECS`. |
| `test_imperial_alignment_gate` | Alignment 1999 is absent from the legal list and the buy is refused. Alignment 2000 is offered and the buy lands. | The handler's alignment check is removed. The legal-list check, removed on its own, fails the same test. |
| `test_old_hulls_keep_the_legacy_wave` | A Scout's offense wave uses legacy 250 fighters and 100 shields, not the tw2002 150. The other nine original hulls match their legacy fighter and shield totals. | The wave reads `ship_specs()` for every hull. |
| `test_new_hull_wave_uses_the_live_spec` | Star Master wave cap is `5/4` of 5000 fighters plus 2000 shields. It is not 1. | The wave reads only legacy `SHIP_SPECS`. |

## Planted bugs

Each one was planted, the named test failed, and the line was put back.

- Scout fighters set to 250. Failed `test_chart_numbers_are_literals`.
- Tholian shields set to 1000. Failed `test_tholian_shields_are_4000`.
- CargoTran turns per warp set to 3. Failed `test_cargotran_warp_spends_four_turns`.
- Interdictor turns per warp set to 2. Failed `test_every_hull_warp_spends_its_chart_turns`.
- Mine total forced to 0 in the buy handler. Failed `test_mine_cap_is_one_shared_total`.
- `_is_day_done` pointed at the legacy table. Failed `test_day_done_reads_the_tw2002_warp`.
- `_warp_cost_for` pointed at the legacy table. Failed `test_runner_warp_reads_the_tw2002_table`.
- The buy handler's alignment check removed. Failed `test_imperial_alignment_gate`.
- The legal list's alignment check removed. Failed `test_imperial_alignment_gate`.
- The offense wave pointed at the live spec for every hull. Failed `test_old_hulls_keep_the_legacy_wave`.
- The offense wave pointed only at the legacy table. Failed `test_new_hull_wave_uses_the_live_spec`.
