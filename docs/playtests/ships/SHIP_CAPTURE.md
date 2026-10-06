# Ship capture

`CAPTURE_MODE` `tw2002` | `legacy`. Capture runs only when `CAPTURE_MODE`, `COMBAT_MODE` and `FLEET_MODE` are all `tw2002`. Otherwise every beaten ship is destroyed as before this slice.

Ferrengi capture, furbing / salvage, corporate ships + passwords, and change of registration are not this slice. Tow rules cp17–cp21 are guarded until `TOW_MODE` `tw2002` (slice 51) is on origin. `tow_hooks_active()` is false on this tree.

| Row | Rule | Status | Test |
| --- | --- | --- | --- |
| cp1 | Capture is an outcome of `attack`, not a new verb | CONFIRMED | `test_legal_list_has_no_capture_param` |
| cp2 | Exact minimum fighters (`ceil(defense / odds)`, at least 1). Larger qty destroys. No combat rng | CONFIRMED shape; window UNVERIFIED | `test_cp2_window` |
| cp3 | `CAPTURE_FAIL_PCT` 0. Above 0, a dedicated `capture_rng` can force a destroy | Gold-only | `test_cp24_rng_and_fail_pct` |
| cp4 | Pod and Scout never (`CAPTURE_PODLESS` never / unoccupied / always) | CONFIRMED; Gold alternates recorded | `test_cp4_podless` |
| cp5 | CFS needs a corp | UNVERIFIED | `test_cp5_cfs_needs_corp` |
| cp6 | Sixth ship is destroyed, attack stays legal | UNVERIFIED | `test_cp6_fleet_cap_destroys` |
| cp7 | Capturing the ISS leaves exactly one | CONFIRMED shape | `test_cp7_unique_iss` |
| cp8 | Pilot pods; hull parks with the attacker; rewards match a kill | CONFIRMED shape | `test_cp8_manned_capture` |
| cp9 | Third loss: pilot is Ship Destroyed and the hull is still captured (`CAPTURE_WHEN_SD`) | UNVERIFIED | `test_cp9_third_loss` |
| cp10 | Bounty only if the pilot is Ship Destroyed | CONFIRMED | `test_cp10_bounty` |
| cp11 | Credits stay with the pilot | SOURCE-CONFLICT, d14 kept | `test_cp8_manned_capture` |
| cp12 | Unmanned capture changes owner, keeps `fleet_id`, corbomite stays, half odds | CONFIRMED | `test_cp12_unmanned` |
| cp13 | Former owner gets `SHIP_CAPTURED`, no pod | CONFIRMED shape | `test_cp12_unmanned` |
| cp14 | Hull-bound cargo, hardware, drive, limpet stay. Fighters and shields are 0 | CONFIRMED shape | `test_cp14_keeps_contents` |
| cp15 | Corbomite does not fire on capture. It fires on a fallback destroy | CONFIRMED | `test_cp2_window`, `test_cp6_fleet_cap_destroys` |
| cp16 | Sell price ignores extras (slice 50) | SOURCE-CONFLICT, kept | `test_cp14_transport_and_sell` |
| cp17 | Capturing the tower releases the tow | UNVERIFIED; dormant until slice 51 | `test_tow_hooks_dormant` |
| cp18 | Capturing a towed unmanned ship keeps the tow | MBBS addendum #6; dormant until slice 51 | `test_tow_hooks_dormant` |
| cp19 | A captured towee in FedSpace is repossessed unless the new owner holds it | Consistent with fl23 | `test_cp19_extern` |
| cp20 | A captured manned towee releases the tow | UNVERIFIED; dormant until slice 51 | `test_tow_hooks_dormant` |
| cp21 | Re-capture releases the tow on attack (REV wins) | SOURCE-CONFLICT; dormant until slice 51 | `test_tow_hooks_dormant` |
| cp22 | Ferrengi are not captured. NPCs never capture | SOURCE-CONFLICT, deferred | `test_cp22_no_npc` |
| cp23 | Feds never capture. FedSpace protection unchanged | CONFIRMED | `test_cp22_no_npc` |
| cp24 | No `universe.rng` draw. Fail percent uses `capture_rng` only | CONFIRMED | `test_cp24_rng_and_fail_pct` |
| cp25 | Captured hull and the victim's ship are different objects | CONFIRMED | `test_cp25_no_aliasing` |
| cp26 | `captured_from` / `captured_day` on the owner's fleet. Contents stay private. Outcome `captured` | CONFIRMED | `test_cp26_fog` |
| cp27 | Prompt states the minimum, the pod/Scout ban, and the parked hull | — | `test_cp27_prompt_and_bots` |
| cp28 | Spectator shows `ship_captured` and does not play the destroy burst for reason `captured` | — | web `app.js` feed |

## Deliberate differences

- The capture window is the exact minimum (`CAPTURE_SLACK` 0). The original's random combat modifiers are not modelled.
- No legal hint for the capture quantity.
- Over the 5-ship cap, or a CFS attacked by a corp-less trader, the ship is destroyed.
- A third loss of the day still hands the hull over (`CAPTURE_WHEN_SD` `capture`).
- Captured corbomite does not raise the sell price.
- Credits stay with the podded victim.
- Tow rules cp17, cp18, cp20, cp21 wait for slice 51.
- Ferrengi capture is deferred. Bots do not aim at the capture number (`BOT_CAPTURE_POLICY` `incidental`).
- StarDock is sector 1, so a captured hull left in FedSpace is repossessed at Extern.

## Legacy

`CAPTURE_MODE` `legacy` is the pre-slice engine: beaten ships are destroyed, combat outcomes stay `destroyed` / `hit` / `miss`, no `SHIP_CAPTURED`, no `captured_from` keys, no new rng. Pin: `test_capture_legacy_is_unchanged` (`622c3af79167631e894d61b1` on d632aae).
