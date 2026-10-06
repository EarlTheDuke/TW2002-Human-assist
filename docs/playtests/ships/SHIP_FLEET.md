# Ship fleet + ship transporter

Slice `ship-fleet-transporter-v1` (slice 50, TransWarp part 2a). A trader can own more than one ship: buy a hull at the StarDock Shipyard **without trading in** (you stay aboard; the new hull waits unmanned in orbit at StarDock), sell extra ships in orbit there, and use the Transporter Pad to beam into any own unmanned ship within the **current** ship's transporter range. Unmanned ships show on density (38) and holo, can be attacked outside FedSpace, and are repossessed at Extern if left in FedSpace.

**Not this slice** (part 2b+, suggested slice 51 `ship-tow-transwarp2-v1`): tractor tow, Type 2 TransWarp + TWarp Upgrade, the Extern tow-lock exception, planet transport with a tow, capture (3.19), citadel ship exchange (6.9), corporate ships + ship passwords (10.9), furbing (5.15).

Sources under `C:\Users\sugar\tw2002_reference\` (short names as in GAP_MAP.md). Target TWGS 3.11; MBBS breaks ties. Marks: CONFIRMED / SOURCE-CONFLICT / UNVERIFIED. Every value lives in a named constant in `engine/constants.py`. Code: `engine/fleet.py` (+ hooks in runner, legality, observation, scanners, combat, hardware, victory). Tests: `tests/test_ship_fleet_v1.py`.

## Switches

| constant | default | other |
| --- | --- | --- |
| `FLEET_MODE` | `tw2002` | `legacy` (one ship per player, no new verbs, keys, events, density or rng draws) |
| `FLEET_MAX_SHIPS` | 5 (manned ship included; ours) | any int |
| `FLEET_XPORT_METRIC` | `directed` (warp direction, avoids ignored) | `undirected` |
| `FLEET_XPORT_SAME_SECTOR` | `True` (distance 0 in range for every hull) | `False` |
| `FLEET_XPORT_INTERDICT` | `ignore` | `block` (planetary interdictor holds a transport) |
| `FLEET_POD_ON_LEAVE` | `discard` | `park` |
| `FLEET_CLOAK_ON_LEAVE` | `decloak` | `keep` (parked hull density 0 + anomaly, unattackable) |
| `FLEET_LIMPET_POLICY` | `hull` | `pilot` |
| `FLEET_FED_REPO` | `fedspace` | `off` |
| `FLEET_UNMANNED_ODDS_FACTOR` | 0.5 | float |
| `FLEET_UNMANNED_ALIGN` | `v2_penalty` | `none` |
| `FLEET_UNMANNED_KILL_EXP` | 0 | int |
| `FLEET_SELL_WHERE` | `stardock_orbit` | - |
| `BOT_FLEET_POLICY` | `spare_only` | `off` |
| `DENSITY_PER_UNMANNED` | 38 | - |
| `SHIP_TRANSPORT_RANGE` | Bible chart (fl9) | - |
| `TURN_COST["ship_transport"]` | 1 | - |

## Legacy

`FLEET_MODE = "legacy"` is today exactly: `Universe.parked_ships` stays empty, `Ship.fleet_id` is never set (these, `Universe.next_ship_id`, `Player.arrived_by_transport` and `LimpetTrack.target_ship_id` are excluded from dumps), `buy_ship` ignores `trade_in` like any unknown arg and lists no `trade_in` param, `sell_ship` / `ship_transport` are absent from the legal list and their handlers answer `unsupported action`, `attack ship:<id>` answers today's `target ship:<id> not found`, density unchanged, no `unmanned_ships` / `fleet` observation keys, no new events, no Extern repo step, no rng draws, prompt unchanged.

Pins (`tests/fed_legacy_digest.py`, seed 250925, 3 days, every observation JSON + prompt text + action/result + event + 3 end-of-day universe states), recorded on **da25c47**, the commit before this slice:

- every tw2002 `*_MODE` flipped to legacy, seats N3,N3,N2,N2,N1,H: `8e1a3a968cef4347d2558a64` (`test_fleet_legacy_is_unchanged`, in the suite); the slice-48 4-seat pin `00135a9202e44a0e085ce978` also still holds;
- only `FLEET_MODE` flipped, every other switch at its default, seats N3,N2,N1,H: `b9a52b96095f12c7c453151b`, identical to da25c47 at defaults (QC check, recorded in the test file; not in the suite because later slices that retune tw2002 play will move it).

## Rules

| row | rule (FLEET_MODE tw2002) | mark | source | test |
| --- | --- | --- | --- | --- |
| fl1 | Registry `Universe.parked_ships: {id: ParkedShip{id, owner_id, sector_id, ship, parked_day}}`, `next_ship_id` counter (never rng). `Ship.fleet_id` set the first time a hull is parked or bought as a spare, kept for life. `player.ship` stays THE manned ship. | CONFIRMED | EIS ShipyardMenu ("Sell Extra Ships ... all your ships in orbit"); FAQ20 "HOW DO I GET MORE THAN ONE SHIP?"; REV 02/06/97; MBBS "Spare Ships" (manual l.1484) | test_fl4_fl5_spare_full_price_pilot_stays_spare_parked_empty, test_fl29_no_rng_draws |
| fl2 | At most `FLEET_MAX_SHIPS` = 5 per player, manned ship included. | UNVERIFIED (ours) | no per-player cap found; TEDIT caps total ship records per game | test_fl2_cap_counts_the_manned_ship |
| fl3 | Swaps move Ship objects; a parked hull never aliases `player.ship` (the death strip mutates `player.ship` in place). | engine invariant | - | test_fl3_no_aliasing_after_death_or_buy_equip |
| fl4 | `buy_ship trade_in=false`: full `ship_cost`, the pilot stays aboard, the new hull appears unmanned at sector 1. No arg = today's trade-in path, byte-identical. | CONFIRMED | REV 02/06/97 (revision history l.872 "When buying a ship without trade-in, trader stays in original ship"); FAQ20 ("Just answer no") | test_fl4_fl5_..., test_fl4_trade_in_default_is_todays_path |
| fl5 | Spare = a very basic model: spec holds, nothing else aboard (0 fighters/shields, no mines, genesis, photons, probes, scanner, cloak, corbomite, beacons, disruptors, detonators, psychic probe, drive), name = display name. | CONFIRMED in shape | EIS ShipyardMenu ("New ships are very basic models") | test_fl4_fl5_... |
| fl6 | Same gates as the trade-in buy (corp_only CFS, min alignment ISS, unique ISS) plus the cap; unique now scans manned AND parked ships (legal list and handler, both buy paths). 0 turns. A pod pilot may buy a spare at full price. | CONFIRMED (gates); ours (cap) | Bible ship chart; EIS ShipyardMenu | test_fl6_spare_gates_location_legacy_corp_alignment, test_fl6_unique_iss_counts_parked_ships, test_fl6_spare_legal_list_matches_handler, test_fl6_spare_ignored_under_legacy |
| fl7 | `sell_ship {ship_id}`: only at StarDock, only an own parked ship in orbit there (sector 1), never the manned ship. Credit = `trade_in_credit(hull)` (25%); everything aboard is lost. 0 turns. A parked pod (only under `FLEET_POD_ON_LEAVE=park`) sells for 0. | CONFIRMED location/extras; UNVERIFIED price | EIS ShipyardMenu; REV v3.05 (no fighter/shield transfer when selling); Gold v3.10 resale formula not used | test_fl7_sell_in_orbit_pays_trade_in_credit_and_drops_contents, test_fl7_sell_refusals |
| fl8 | `ship_transport {ship_id}` beams the pilot from the manned ship into an own parked ship. | CONFIRMED | EIS Computer.html "<X> Transporter Pad"; TWINSTR; Gypsy | test_fl9_fl10_range_exact_and_off_by_one |
| fl9 | Range table `SHIP_TRANSPORT_RANGE`: pod 0, MC 5, Scout 0, Missile Frigate 2, BattleShip 8, CFS 10, COLT 7, CargoTran 5, Merchant Freighter 5, ISS 10, Havoc 6, StarMaster 3, Constellation 6, T'khasi Orion 3, Tholian Sentinel 3, Taurean Mule 5, Interdictor 20; legacy-roster keys not on the chart get 0. | CONFIRMED; SOURCE-CONFLICT recorded | Bible ship chart "Transporter Range" = MBBS "Teleport Range" table (manual l.528+); docs wiki Glossary (COLT 7). MBBS prose "ISS ... 15 hop transporter beam range" (l.1444) vs both charts 10: charts kept | test_fl10_range_is_the_source_hull |
| fl10 | Range is the SOURCE ship's (the one you are in). Distance = shortest warp path from the pilot's sector, warp direction followed, avoids ignored, own BFS (no rng). | CONFIRMED source rule; UNVERIFIED direction | EIS Computer.html ("the transport range of your ship"); FAQ20 l.31 ("if the range on your ship is 7 ...") | test_fl10_range_is_the_source_hull, test_fl9_fl10_range_exact_and_off_by_one, test_fl10_directed_vs_undirected |
| fl11 | Same sector (0 hops) is in range for every hull, incl. range-0 Scout and pod (the MBBS spare-ship path). | UNVERIFIED | no source forbids it; MBBS "Spare Ships" | test_fl11_range_zero_boards_in_the_same_sector |
| fl12 | Own ships only: never another player's, a corp mate's or an ally's. | CONFIRMED | FAQ20 l.32 ("You can't transport to an unmanned ship that isn't yours") | test_fl12_own_ships_only |
| fl13 | Boarding a corp_only hull (CFS) needs current corp membership; the CFS you fly stays usable. | CONFIRMED in shape | REV v3.09 (extinct corp: "once you leave the ship you won't have access to it again") | test_fl13_cfs_needs_corp_membership |
| fl14 | 1 turn flat, no fuel, whatever the hops or turns per warp. | CONFIRMED | Gypsy SST loop; OldFAQ #20 ("3 turns per each side"); cabal corps.html; docs wiki Glossary RTR | test_fl14_fl15_one_turn_no_ore_no_hazards |
| fl15 | No sector-entry hazards: no NavHaz, limpet attach, armid hit, quasar, fighter challenge / attack / toll, interdict. The destination and its warps go on the pilot's map. The Fed f6/f22 presence check still runs (fl17e). | CONFIRMED (MBBS tie-break) | MBBS Transporter-crime note ("They can even enter a 100% Haz this way, unarmed, and never be harmed"); TWGS silent | test_fl14_fl15_one_turn_no_ore_no_hazards |
| fl16 | Preconditions: alive, not landed (planet device stays `planet_transport`), no fighter challenge (CHALLENGE_REFUSAL), no open Ferrengi encounter (refused before tribute), turns left; target exists, own, not manned, fl13, in range. Interdiction ignored by default. Refusals spend nothing. | UNVERIFIED (interdict) | - | test_fl16_preconditions_landed_challenge_turns, test_legal_list_equals_handler_for_every_advertised_choice |
| fl17 | Effects: (a) the hull you leave parks here (fleet id assigned; a pod is discarded by default); (b) the target record is removed and its Ship becomes `player.ship`; (c) occupants both sides, port visit ends, `photon_damped_sector_id` cleared, `arrived_by_transwarp` False, `arrived_by_transport` True (retreat refused until the next warp / TransWarp / liftoff); (d) SHIP_TRANSPORT event; (e) `fed.check_iss_repo_on_move`. | CONFIRMED (e); UNVERIFIED (a pod, c retreat - inferred from REV 02/06/97 non-adjacent TransWarp rule) | REV 02/06/97; docs wiki Imperial_StarShip.html ("If they do not quickly transport to another ship, Zyrain ...") | test_fl17a_pod_discarded_or_parked, test_fl17c_retreat_refused_after_transport_cleared_by_warp, test_fl17e_evil_pilot_boarding_iss_meets_f22 |
| fl18 | Hull-bound: holds, cargo, cargo_cost, fighters, shields, mines, genesis, photons, probes, scanner, cloaks + state, corbomite, beacons, disruptors, detonators, psychic probe, transwarp_drive, photon_disabled_ticks, name, fleet_id. Pilot-bound: credits, exp, alignment, turns, maps, corp, alliances, pods_today, deaths, last_crime_sector_id, flee_penalty, commission. | CONFIRMED in shape | REV ("ship record" vs "user record"); EIS ShipyardMenu (extras belong to the ship) | test_fl18_hull_bound_stays_pilot_bound_travels |
| fl19 | Limpets stay on the hull: when the tracked pilot leaves, the track follows the parked hull (`query_limpets` / `limpets_owned` report its sector); boarding that hull points it at the pilot again. StarDock limpet removal acts on the manned hull only. | CONFIRMED in shape | Gypsy / Slice ("Attached limpets will reduce the trade in value") | test_fl19_limpet_follows_the_hull_and_retargets |
| fl20 | Leaving a cloaked hull decloaks it (default); boarding never cloaks. | UNVERIFIED | no rule found for an empty cloaked hull | test_fl20_leaving_a_cloaked_hull_decloaks_it |
| fl21 | `planet_transport` unchanged: moves the pilot and the manned ship only. | engine | Slice tow oddity is part 2b | (unchanged code path; suite planet-transport tests) |
| fl22 | New sector key `unmanned_ships: [{ship_id, hull, owner_name, own}]` (current sector, holo / probe view, adjacent "seen"), never in occupants / traders / rivals. Own hulls add fighters + shields; a rival hull adds fighters only where rival manned ships already show them (INFO_MODE tw2002 traders list). Never cargo, hardware, drive, corbomite or limpets. Density 38 per uncloaked unmanned ship (manned 40); a cloaked parked hull reads 0 + anomaly. | CONFIRMED | cabal formulas.html density table ("Unmanned" 38); REV v3.0x (l.795 "occupied ships as 40, unoccupied as 38") | test_fl22_density_38_and_never_an_occupant, test_fl20_... |
| fl23 | Extern (tick_day, before the Fed tows): every unmanned ship in sectors 1..10 (incl. StarDock) is repossessed, no refund, FLEET_REPOSSESSED (owner + spectator), in ship-id order. Own fleet list flags `repo_at_extern`. | CONFIRMED | cabal glossary Extern; docs wiki Glossary Extern #3; OldFAQ #18; cabal tips #4 | test_fl23_extern_repossesses_fedspace_only |
| fl24 | `attack target=ship:<id>`: same sector, outside FedSpace, not own / corp / ally, not cloaked. tw2002 ship-attack math with the hull's offensive odds x 0.5; never flees; destroyed = record gone, corbomite aboard blasts the attacker; owner keeps pod, deaths and exp; attacker exp +0; alignment -= int(alignment x 0.10 x fighters_destroyed / 1000) (`v2_penalty`). Attackable ships are listed in a NEW `target.unmanned_choices`; `target.choices` unchanged. | UNVERIFIED for v3 (odds, FedSpace, alignment); CONFIRMED no-flee | OldFAQ #18 (v2); REV l.518 ("unmanned ships to flee ... fixed"); REV v3.05 (attacks on unoccupied ships exist) | test_fl24_refusals_fedspace_own_corp_ally, test_fl24_half_odds_never_flees_and_kill_rules, test_fl24_alignment_none_switch |
| fl25 | Ferrengi and Feds ignore unmanned ships (only fl23 applies). | deliberate / UNVERIFIED | - | (no NPC code reads parked_ships) |
| fl26 | A pod / Ship Destroyed leaves parked ships untouched; elimination removes the owner's parked ships. | CONFIRMED (spare survives); deliberate (elimination) | MBBS "Spare Ships ... beam into the spare" | test_fl26_owner_pod_leaves_parked_ships |
| fl27 | `full_net_worth` adds each own parked hull valued exactly like `Player.net_worth` values the manned ship; sold / repossessed / destroyed hulls drop out; no double count. | engine | - | test_fl27_net_worth_counts_parked_hulls_once |
| fl28 | Fake bust stays per pilot (`last_crime_sector_id`): alternating two ports by transporter never fake-busts; the same port twice still does. The port visit ends on transport. | CONFIRMED | OldFAQ #20; cabal / docs wiki Glossary Fake Bust, RTR | test_fl28_steal_transport_loop_no_fake_bust |
| fl29 | No universe.rng draws (BFS, ids, repo order, unmanned combat). | engine | - | test_fl29_no_rng_draws |
| fl30 | Own-seat observation `fleet: {max_ships, transport_range, manned_ship_id, ships: [{ship_id, hull, name, sector_id, hops, in_range, fighters, shields, holds, cargo, transwarp, repo_at_extern}]}`. Events SHIP_TRANSPORT (pilot + both sectors), FLEET_SPARE_BOUGHT (owner + StarDock), SHIP_SOLD (owner), FLEET_REPOSSESSED (owner), UNMANNED_SHIP_DESTROYED (attacker + owner + sector). | engine | - | test_fl22_..., test_fl23_... |
| fl31 | Prompt paragraph (`_FLEET_NOTE`). | engine | - | test_prompt_explains_the_fleet_under_tw2002 |
| fl32 | Spectator: SHIP_TRANSPORT beam line, fleet events in the feed (web/app.js); cockpit forms for sell_ship / ship_transport (web/bot.js). Per-sector hollow unmanned icon not drawn yet (open). | partial | - | - |
| fl33 | Out of scope: see top. | - | cabal twgs.html Type II 20,000 / upgrade 9,000 vs OldFAQ v2 80,000 / 40,000 (SOURCE-CONFLICT recorded for slice 51) | - |

## Bots

`BOT_FLEET_POLICY = "spare_only"`: N-bots never buy spares, never sell and never attack `ship:<id>`. The only new branch (`SeatBrain._board_spare`): in an escape pod (or the free Scout after a death), beam into an own parked hull in transporter range that costs more than the hull flown. seat_brain and heuristic never pass `trade_in`, so every existing buy_ship call is today's path. Day-10 scripted fleet use is expected to be 0 (see the Delivered note).

## TransWarp add-ons (Ben, 2026-10-05)

- `SHIP_TW_FED_LOCK_HULLS = "all_tw"` (default: the commissioned FedSpace lock on ISS, CFS and Havoc, as shipped in slice 48) | `"iss_only"`. Test: test_fed_lock_hulls_switch.
- Drive owners keep an ore reserve: a seat whose ship has a Type 1 drive sees `min(2 x SHIP_TW_ORE_PER_HOP x SHIP_TW_RESERVE_HOPS (6), holds // 2)` fuel ore as not for sale (seat_brain `tw_reserve_view`), and tops the hold up to it at an ore port (`_top_up_tw_ore`). `_transwarp_instead` reads the real hold. Seats without a drive get the observation back untouched, so their play is byte-identical. Tests: test_tw_ore_reserve_only_for_drive_owners, test_tw_ore_reserve_tops_up_at_an_ore_port.

## Deliberate differences

- Per-player fleet cap of 5 (the original caps only total ship records per game).
- Own ships only on the transporter: no corporate ships, no ship passwords (FAQ20 l.33), no corp X-port list.
- Sell price reuses the yard's 25% trade-in credit; extras aboard add nothing (original trade-in valued extras; Gold resale formula not used). A parked pod sells for 0.
- Leaving a cloaked hull decloaks it; leaving an escape pod discards it; interdiction does not block a transport (all UNVERIFIED, switchable).
- Retreat refused after a transport (inferred from the non-adjacent TransWarp rule). The Ferrengi flee path is not a retreat and stays open.
- An open Ferrengi encounter refuses a transport (instead of taking tribute first like other verbs), per spec fl16.
- Unmanned-ship attack uses v2-era numbers (half odds, 10% alignment per 1000 fighters destroyed, no FedSpace attacks) - UNVERIFIED for v3, switchable. The tw2002 attack math is used even under COMBAT_MODE legacy.
- Ferrengi and Feds ignore unmanned ships (only Extern FedSpace repossession applies).
- Elimination removes the owner's parked ships (original: assets go rogue at timeout).
- No Extern tow-lock exception yet (needs tractor tow, part 2b): every unmanned ship in FedSpace at Extern is lost. The repo runs whenever FLEET_MODE is tw2002 (not gated on FED_MODE).
- Fleet registry fields are excluded from universe dumps (like slice 48's drive fields), so a save / replay dump does not carry parked ships.
- Bots default to `spare_only`: no spares, sells, RTR / SST loops or unmanned attacks in this slice.
- StarDock stays sector 1 (existing deliberate), so "in orbit at StarDock" is FedSpace and Extern repossession applies there, as in the original.
