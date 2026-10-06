# Corporate ships and furbing

`CORPSHIP_MODE` `tw2002` | `legacy`. Legacy is owner-only transport and tow, no furb, no defunct conversion, no new verbs, no new observation keys. Pin: `test_corpships_legacy_is_unchanged` (`85622347d694ff6224ec89bc` on 3b8f8e5).

| Row | Rule | Status | Constant | Test |
| --- | --- | --- | --- | --- |
| cs1 | `corp_ticker` None is personal | CONFIRMED | — | `test_cs2_flag_and_cfs_stays_corporate` |
| cs2 | Flag the manned ship. CFS cannot go personal | CONFIRMED; 0 turns UNVERIFIED | `CORPSHIP_SET_TURNS` 0, `CORPSHIP_SET_SCOPE` manned | `test_cs2_flag_and_cfs_stays_corporate` |
| cs3 | New ordinary hulls are personal. Corp-only hulls take the buyer's corp | UNVERIFIED default | `CORPSHIP_NEW_DEFAULT` personal | `on_new_hull` |
| cs4 | Corp mates may board an unmanned corporate ship | CONFIRMED | — | `test_cs4_cs7_cs8_corp_mate_password_and_personal_stays_private` |
| cs5 | Personal ships stay owner-only | UNVERIFIED | `CORPSHIP_PERSONAL_ACCESS` owner | same |
| cs6 | Password, max 8, exact case, 0 turns | length and case UNVERIFIED | `CORPSHIP_PASSWORD_MAX_LEN` 8, `CORPSHIP_PASSWORD_CASE` exact | `test_cs6_password_length_and_owner_event_has_no_secret` |
| cs7 | Non-owners must pass a non-blank password. The owner is not asked | CONFIRMED | — | `test_cs4_cs7_cs8_corp_mate_password_and_personal_stays_private` |
| cs8 | Wrong password is free and silent to the owner | UNVERIFIED | `CORPSHIP_BAD_PASSWORD` refuse_free, `CORPSHIP_TELL_OWNER` False | same |
| cs9 | Corp flag stays. The boarder becomes the owner | flag CONFIRMED; owner UNVERIFIED | `CORPSHIP_OWNER_ON_BOARD` pilot | same |
| cs10 | Boarding counts toward the 5-ship cap | UNVERIFIED | `CORPSHIP_BOARD_CAP` True | `test_cs10_fleet_cap_blocks_a_sixth_hull` |
| cs11 | Password stays on board | UNVERIFIED | `CORPSHIP_PW_ON_BOARD` keep | `test_cs4_cs7_cs8_corp_mate_password_and_personal_stays_private` |
| cs12 | Corp X-port list. Occupied corp ships are not parked, so they are absent | CONFIRMED | — | `test_cs12_xport_lists_corp_ship_not_a_manned_one` |
| cs13 | Corp mates may tow a corporate ship with the password | SOURCE-CONFLICT | `CORPSHIP_TOW` corp_with_password | `test_cs24_last_member_leaves_parked_ship_defunct_and_tow_drops` |
| cs14 | Failsafe refuses your own corp's corporate ship | CONFIRMED | — | `test_cs14_failsafe_and_cs16_own_personal_is_attackable` |
| cs15 | A corp mate's personal ship is attackable. Allies stay refused | CONFIRMED | — | `test_fl24_refusals_fedspace_own_corp_ally` |
| cs16 | Your own personal ship is attackable. No alignment loss | UNVERIFIED align | `CORPSHIP_OWN_KILL_ALIGN` 0 | `test_cs14_failsafe_and_cs16_own_personal_is_attackable` |
| cs17 | Holds gained = (holds + 3) / 3, capped at max_holds | CONFIRMED | `FURB_BONUS` 3, `FURB_DIVISOR` 3 | `test_cs17_formula_table` |
| cs18 | Current holds, not the hull base | CONFIRMED | — | `test_cs19_capture_does_not_furb_and_over_the_window_does` |
| cs19 | A capture does not furb. A destroy does | CONFIRMED | — | same |
| cs20 | Pods and Ferrengi do not furb | UNVERIFIED | `FURB_EXCLUDED_HULLS`, `FURB_FERRENGI` False | `test_cs17_formula_table` |
| cs21 | TOO excellent when the gain is 0 | text CONFIRMED; trigger UNVERIFIED | — | `test_cs21_too_excellent_when_already_full` |
| cs22 | No overkill limit | SOURCE-CONFLICT | `SALVAGE_OVERKILL` none | — |
| cs23 | Cargo, fighters, shields and credits are not salvaged | UNVERIFIED | `SALVAGE_CARGO` none | — |
| cs24 | Extinct corp: parked corporate ships become defunct and drop a tow | CONFIRMED | `DEFUNCT_OWNER` defunct | `test_cs24_last_member_leaves_parked_ship_defunct_and_tow_drops` |
| cs25 | The ship he is flying stays until he leaves it | CONFIRMED | — | `test_cs25_manned_corp_ship_turns_defunct_only_when_he_leaves_it` |
| cs26 | Defunct capture needs a corp. Otherwise the minimum attack destroys | UNVERIFIED outcome | `DEFUNCT_NONCORP_CAPTURE` destroy | `test_cs24_last_member_leaves_parked_ship_defunct_and_tow_drops`, `test_cs26_corp_member_captures_defunct` |
| cs27 | Defunct ships are nobody's net worth | UNVERIFIED | `DEFUNCT_NET_WORTH` 0 | owner id `defunct` is not a player |
| cs28 | A leaver's parked corporate ships pass to the CEO | UNVERIFIED | `CORPSHIP_ON_LEAVE` to_ceo | `test_cs28_leaver_parked_corp_ship_goes_to_the_ceo` |
| cs29 | A captured corporate ship becomes the captor's personal ship. Password cleared | UNVERIFIED | `CORPSHIP_CAPTURE_FLAG` captor_default | `test_cs26_corp_member_captures_defunct` |
| cs30 | Your own corp's ships are not attackable | CONFIRMED | — | `test_cs14_failsafe_and_cs16_own_personal_is_attackable` |
| cs31 | Labels personal / corp TKR / defunct Corp | CONFIRMED | — | `sector_label` |
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
