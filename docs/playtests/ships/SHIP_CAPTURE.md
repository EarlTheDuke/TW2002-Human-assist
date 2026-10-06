# Ship capture

`CAPTURE_MODE` `tw2002` | `legacy`. Capture runs only when `CAPTURE_MODE`, `COMBAT_MODE` and `FLEET_MODE` are all `tw2002`. Otherwise every beaten ship is destroyed as before this slice.

Ferrengi capture, furbing / salvage, corporate ships + passwords, and change of registration are not this slice. Tow rules cp17–cp21 call slice 51's `tow.release` / `towed_by`. `tow_hooks_active()` is true when `TOW_MODE` is `tw2002`.

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
| cp17 | Capturing the tower releases the tow (`tower_captured`). A parked tower hull's dormant tt12 lock is released the same way on an unmanned capture | UNVERIFIED (spec cp17) | `test_cp17_tower_capture_releases_and_towed_ship_stays`, `test_qc_captured_parked_tower_drops_its_dormant_lock` |
| cp18 | Capturing a towed unmanned ship keeps the tow and tells the tower. The tower keeps dragging it; the captor's sale or boarding releases it (`towee_gone`; slice 51 has no separate `towee_boarded` reason) | MBBS addendum #6 | `test_cp18_capturing_a_towed_ship_keeps_the_tow`, `test_qc_towed_capture_tower_is_told_and_keeps_dragging`, `test_qc_captor_sells_the_towed_ship_at_stardock`, `test_qc_captor_boards_the_towed_ship_and_the_tow_breaks` |
| cp19 | A captured towee in FedSpace is repossessed unless the new owner holds it | Consistent with fl23 | `test_cp19_extern`, `test_cp19_old_tower_does_not_hold_a_captured_ship_at_extern` |
| cp20 | A captured manned towee releases the tow (`towee_gone`) | CONFIRMED shape | `test_cp20_capturing_a_manned_towee_releases` |
| cp21 | Re-capture releases the tow on attack (REV wins); the tower is not sent `TOW_TARGET_CAPTURED` for his own capture | SOURCE-CONFLICT; `TOW_ON_ATTACK` release | `test_qc_tower_recaptures_its_towee_and_re_engages` |
| cp22 | Ferrengi are not captured. NPCs never capture | SOURCE-CONFLICT, deferred | `test_cp22_no_npc` |
| cp23 | Feds never capture. FedSpace protection unchanged | CONFIRMED | `test_cp22_no_npc` |
| cp24 | No `universe.rng` draw. Fail percent uses `capture_rng` only | CONFIRMED | `test_cp24_rng_and_fail_pct` |
| cp25 | Captured hull and the victim's ship are different objects | CONFIRMED | `test_cp25_no_aliasing` |
| cp26 | `captured_from` / `captured_day` on the owner's fleet (saved once set, omitted while unset). Contents stay private. Outcome `captured` | CONFIRMED | `test_cp26_fog`, `test_qc_captured_from_survives_save_and_resume`, `test_qc_former_owner_elsewhere_sees_ship_captured_without_contents` |
| cp27 | Prompt states the minimum, the pod/Scout ban, and the parked hull | — | `test_cp27_prompt_and_bots` |
| cp28 | Spectator shows `ship_captured` and does not play the destroy burst for reason `captured` | — | web `app.js` feed |

## Deliberate differences

- The capture window is the exact minimum (`CAPTURE_SLACK` 0). The original's random combat modifiers are not modelled.
- No legal hint for the capture quantity.
- Over the 5-ship cap, or a CFS attacked by a corp-less trader, the ship is destroyed.
- A third loss of the day still hands the hull over (`CAPTURE_WHEN_SD` `capture`).
- Captured corbomite does not raise the sell price.
- Credits stay with the podded victim.
- Capturing the tower releases with reason `tower_captured`. Capturing the towed unmanned ship keeps the lock and emits `TOW_TARGET_CAPTURED`. Capturing a manned towee releases with reason `towee_gone`. The old tower does not hold that hull at Extern.
- Ferrengi capture is deferred. Bots do not aim at the capture number (`BOT_CAPTURE_POLICY` `incidental`).
- StarDock is sector 1, so a captured hull left in FedSpace is repossessed at Extern.

## Legacy

`CAPTURE_MODE` `legacy` is the pre-slice engine: beaten ships are destroyed, combat outcomes stay `destroyed` / `hit` / `miss`, no `SHIP_CAPTURED`, no `captured_from` keys, no new rng. Pin: `test_capture_legacy_is_unchanged` (`76d447b221cd26ce16dcd3fd` on the slice-51 parent, identical to that parent with capture off).
