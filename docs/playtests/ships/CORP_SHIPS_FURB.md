# Corporate ships and furbing

`CORPSHIP_MODE` `tw2002` | `legacy`. Legacy is owner-only transport and tow, no furb, no defunct conversion, no new verbs, no new observation keys. Pin: `test_corpships_legacy_is_unchanged` (`85622347d694ff6224ec89bc`, 10-day N3,N3,N2,N2,N1,H seed 250925; CORPSHIP_MODE, PLANET_TRADE_MODE and the seven fullgame-fixes-v2 switches flipped; equals f10b080 with PLANET_TRADE_MODE flipped, per 4b85e21). QC tests: `tests/test_corpships_qc_v1.py`.

| Row | Rule | Status | Constant | Test |
| --- | --- | --- | --- | --- |
| cs1 | `corp_ticker` None is personal | CONFIRMED | — | `test_cs2_flag_and_cfs_stays_corporate` |
| cs2 | Flag the manned ship. CFS cannot go personal | CONFIRMED; 0 turns UNVERIFIED | `CORPSHIP_SET_TURNS` 0, `CORPSHIP_SET_SCOPE` manned | `test_cs2_flag_and_cfs_stays_corporate` |
| cs3 | New ordinary hulls are personal. Corp-only hulls take the buyer's corp | UNVERIFIED default | `CORPSHIP_NEW_DEFAULT` personal | `test_qc_a_bought_hull_is_personal_with_no_password` |
| cs4 | Corp mates may board an unmanned corporate ship | CONFIRMED | — | `test_cs4_cs7_cs8_corp_mate_password_and_personal_stays_private` |
| cs5 | Personal ships stay owner-only | UNVERIFIED | `CORPSHIP_PERSONAL_ACCESS` owner | same |
| cs6 | Password, max 8, exact case, 0 turns | length and case UNVERIFIED | `CORPSHIP_PASSWORD_MAX_LEN` 8, `CORPSHIP_PASSWORD_CASE` exact | `test_cs6_password_length_and_owner_event_has_no_secret` |
| cs7 | Non-owners must pass a non-blank password. The owner is not asked | CONFIRMED | — | `test_cs4_cs7_cs8_corp_mate_password_and_personal_stays_private` |
| cs8 | Wrong password is free and silent to the owner | UNVERIFIED | `CORPSHIP_BAD_PASSWORD` refuse_free, `CORPSHIP_TELL_OWNER` False | same |
| cs9 | Corp flag stays. The boarder becomes the owner | flag CONFIRMED; owner UNVERIFIED | `CORPSHIP_OWNER_ON_BOARD` pilot | same |
| cs10 | Boarding counts toward the 5-ship cap | UNVERIFIED | `CORPSHIP_BOARD_CAP` True | `test_cs10_fleet_cap_blocks_a_sixth_hull` |
| cs11 | Password stays on board | UNVERIFIED | `CORPSHIP_PW_ON_BOARD` keep | `test_cs4_cs7_cs8_corp_mate_password_and_personal_stays_private` |
| cs12 | Corp X-port list. Occupied corp ships are not parked, so they are absent | CONFIRMED | — | `test_cs12_xport_lists_corp_ship_not_a_manned_one` |
| cs13 | Corp mates may tow a corporate ship with the password | SOURCE-CONFLICT | `CORPSHIP_TOW` corp_with_password | `test_qc_corp_tow_needs_the_password_and_personal_stays_owner_only`, `test_qc_owner_tows_his_own_locked_corp_ship_without_the_password` |
| cs14 | Failsafe refuses your own corp's corporate ship | CONFIRMED | — | `test_cs14_failsafe_and_cs16_own_personal_is_attackable` |
| cs15 | A corp mate's personal ship is attackable. Allies stay refused | CONFIRMED | — | `test_qc_failsafe_matrix_and_legal_list_agree` |
| cs16 | Your own personal ship is attackable. No alignment loss | UNVERIFIED align | `CORPSHIP_OWN_KILL_ALIGN` 0 | `test_qc_own_kill_costs_no_alignment_but_a_rival_kill_does`, `test_qc_own_ship_at_the_exact_minimum_is_destroyed_and_furbed_not_captured` |
| cs17 | Holds gained = (holds + 3) / 3, capped at max_holds | CONFIRMED | `FURB_BONUS` 3, `FURB_DIVISOR` 3 | `test_cs17_formula_table` |
| cs18 | Current holds, not the hull base | CONFIRMED | — | `test_qc_furb_uses_current_holds_not_the_hull_base` |
| cs19 | A capture does not furb. A destroy does | CONFIRMED | — | same |
| cs20 | Pods and Ferrengi do not furb | UNVERIFIED | `FURB_EXCLUDED_HULLS`, `FURB_FERRENGI` False | `test_cs17_formula_table`, `test_qc_manned_kill_furbs_and_a_pod_kill_is_too_excellent` |
| cs21 | TOO excellent when the gain is 0 | text CONFIRMED; trigger UNVERIFIED | — | `test_cs21_too_excellent_when_already_full`, `test_qc_furb_cap_is_the_attacker_hull_max_not_its_base` |
| cs22 | No overkill limit | SOURCE-CONFLICT | `SALVAGE_OVERKILL` none (alt `ratio` not built) | `test_qc_furb_uses_current_holds_not_the_hull_base` (10 fighters on a 0-fighter hull still furb) |
| cs23 | Cargo, fighters, shields and credits are not salvaged | UNVERIFIED | `SALVAGE_CARGO` none | — |
| cs24 | Extinct corp: parked corporate ships become defunct and drop a tow | CONFIRMED | `DEFUNCT_OWNER` defunct | `test_cs24_last_member_leaves_parked_ship_defunct_and_tow_drops` |
| cs25 | The ship he is flying stays until he leaves it | CONFIRMED | — | `test_cs25_manned_corp_ship_turns_defunct_only_when_he_leaves_it` |
| cs26 | Defunct capture needs a corp. Otherwise the minimum attack destroys | UNVERIFIED outcome | `DEFUNCT_NONCORP_CAPTURE` destroy | `test_cs24_last_member_leaves_parked_ship_defunct_and_tow_drops`, `test_cs26_corp_member_captures_defunct` |
| cs27 | Defunct ships are nobody's net worth | UNVERIFIED | `DEFUNCT_NET_WORTH` 0 | `test_qc_extinction_touches_only_that_corps_ships_and_keeps_the_password` |
| cs28 | A leaver's parked corporate ships pass to the CEO | UNVERIFIED | `CORPSHIP_ON_LEAVE` to_ceo | `test_cs28_leaver_parked_corp_ship_goes_to_the_ceo`, `test_qc_ceo_leaving_hands_his_parked_corp_ships_to_the_first_remaining_member`, `test_qc_leaver_cannot_unflag_the_corp_ship_he_is_still_flying`, `test_qc_leaver_towing_a_corp_ship_drops_the_beam` |
| cs29 | A captured corporate ship becomes the captor's personal ship. Password cleared | UNVERIFIED | `CORPSHIP_CAPTURE_FLAG` captor_default | `test_cs26_corp_member_captures_defunct`, `test_qc_captured_corp_ship_becomes_personal_and_loses_its_password` |
| cs30 | Your own corp's ships are not attackable | CONFIRMED | — | `test_cs14_failsafe_and_cs16_own_personal_is_attackable` |
| cs31 | Labels personal / corp TKR / defunct Corp | CONFIRMED | — | `test_qc_destroy_event_reports_the_real_label` |
| cs32 | Net worth stays with the current owner | UNVERIFIED | `CORPSHIP_NW` owner | — |
| cs33 | Ferrengi, Feds and pods are unchanged | CONFIRMED by scope | — | furb is only on player destroy paths |

## Deliberate differences

- Flag and password are set on the manned ship only.
- Personal ships stay owner-only for corp mates.
- There is no separate "allow ship transfers" toggle.
- Boarding a corp ship makes the boarder the owner.
- A wrong password is free and the owner is not told.
- Ferrengi keep their cargo salvage and do not furb. Pods give no holds.
- No overkill limit. Player cargo is not salvaged.
- A leaver's parked corporate ships pass to the CEO.
- Defunct ships count for nobody.

## Playtest (e1faeeb)

Scripted seed 250925, 10 days, Ferrengi on, seats N3,N3,N2,N2,N1,H. `CORPSHIP_MODE` legacy and tw2002 were the same match: rejected 0/0, no exceptions. Bots do not flag, password, or furb, so furbed, defunct, flag, and password-fail events were 0. Ship destroyed 2 (H-P6).

| Seat | Net worth | Ship | Planets | Deaths |
| --- | --- | --- | --- | --- |
| N3-P1 | 747,201 | battleship | 3 | 0 |
| H-P6 | 552,814 | scout_marauder | 0 | 2 |
| N2-P4 | 523,082 | cargotran | 4 | 0 |
| N1-P5 | 445,423 | merchant_cruiser | 2 | 0 |
| N2-P3 | 294,636 | cargotran | 2 | 0 |
| N3-P2 | 240,690 | cargotran | 2 | 0 |

30-day headless, 2 heuristic agents, seed 42, no gate: finished, winner P2 on time net worth (1,085,694 vs P1 853,240). Both alive. Events: 25 ship_destroyed, 0 furb, 0 defunct, 0 flag, 0 capture. A furb emit no longer moves the pod: the hull is snapshotted, the pod is placed, then the furb event fires (`e1faeeb`).

## QC (Commander, slice 53 review)

Fixed in QC:

- The SHIP_FURBED event was emitted before the manned victim's loss, which moved `universe.seq` and so the pod's seeded escape path; `test_qc_capture_pod_path_matches_a_destroy` failed on 84b7039 (Windows and Linux). Cur fixed it in e1faeeb while QC had the identical change (furb reads a copy of the victim hull before the loss and emits after it); the QC copy was dropped on rebase.
- A leaver still flying his old corp's hull (cs25) could `ship_set_personal` it (or re-flag it to a new corp) and keep it for good. Both verbs now refuse "this is another corporation's ship", from one block function shared with the legal list.
- Attacking your own personal unmanned hull with the exact minimum "captured" it (no-op owner change, SHIP_CAPTURED, no furb). Your own hull now always destroys and furbs (cs16).
- A leaver towing a corporate hull of the corp he left kept the beam on a ship he no longer has access to (EIS <X>); the beam drops with reason `left_corp`.
- SHIP_FURBED `capped` was `gained == 0`; it is now "the attacker's max_holds cut the gain" (true also for a partial cap).
- `tow_engage` legal params gain `detail_by` {owner, class, password_required, ownership} like the X-port list (spec VERBS section).
- UNMANNED_SHIP_DESTROYED carries `ownership` (personal / corp TKR / defunct Corp) under CORPSHIP_MODE (cs31 / REV 516).
- Alt branches now do what their names say: `DEFUNCT_NONCORP_CAPTURE = "refuse"` refuses the attack; `CORPSHIP_PASSWORD_CASE` other than exact compares case-blind. No `FLEET_UNMANNED_KILL_EXP` for an own hull (0 by default).

Planted bugs: the 25 spec plants re-created (pb10 is structural: manned ships are not ParkedShip records) plus 33 QC plants. With the QC tests 57/58 are caught; the one miss (X-port pool includes defunct) is an equivalent mutant because board_block still refuses it. Cur's tests alone caught 17 of the 25 spec plants (missed pb2, pb3, pb7, pb12, pb17, pb19, pb23, pb25).

Not changed (judgment calls): a corp mate towing a corp hull owned by someone else does not get the Extern hold (tt22 checks the owner's beam); trading in a borrowed corp hull at StarDock (cs25 leaver) is allowed; corbomite on your own hull fires on you.
