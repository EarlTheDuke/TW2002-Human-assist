# Ship TransWarp, Type 1

Slice `ship-transwarp-v1` (slice 48). The three TransWarp hulls can buy a Type 1 Hyvarinen drive at StarDock and jump. **Not this slice:** Type 2 (tow), the TWarp upgrade, multi-ship ownership, the ship transporter, tractor towing and furbing (part 2+). Planet TransWarp is unchanged and is a different verb (`planet_transwarp`).

Sources under `C:\Users\sugar\tw2002_reference\`. Target TWGS 3.11; MBBS breaks ties. Marks: CONFIRMED / SOURCE-CONFLICT / UNVERIFIED. Every value lives in a named constant in `engine/constants.py`.

## Switches

| constant | default | other |
| --- | --- | --- |
| `SHIP_TW_MODE` | `tw2002` | `legacy` (no drive, no verb, no keys, no events) |
| `SHIP_TW_BLIND` | `density0` (original: fuse on density > 0) | `refuse` (handler refuses a blind jump; not original) |
| `SHIP_TW_FED_LOCK` | `commissioned` | `fighter_only` |
| `SHIP_TW_TURN_COST` | `tpw` (one ship turns-per-warp) | `hops` (TPW times hops) |
| `SHIP_TW_FRIENDLY` | `own_corp_ally` | `own_only` |
| `SHIP_TW_CLOAK_POLICY` | `allow_decloak` (UNVERIFIED) | - |
| `SHIP_TW_FUSE_REFUNDS` | `False` (UNVERIFIED) | `True` (a fuse spends no turns) |
| `SHIP_TW_LIST_CAP` | 40 | legal-list length cap |

`SHIP_TW_HULLS` = Imperial StarShip, Corporate FlagShip, Havoc Gunstar. `SHIP_TW_TYPE1_COST` = 12,500. `SHIP_TW_ORE_PER_HOP` = 3.

## Legacy

`SHIP_TW_MODE = "legacy"`: `Ship.transwarp_drive` is never set (it and `Player.arrived_by_transwarp` are left out of dumps while unset, saved once set; SHIP_FLEET.md Saves), `buy_equip item=transwarp_drive` is absent and refused, `ship_transwarp` is absent from the legal list and the handler answers `unsupported action`, no `ship.transwarp` observation block, no new events, no prompt paragraph, no rng draws.

Pins (`tests/test_ship_transwarp_v1.py::test_ship_tw_legacy_is_unchanged`, recorded on 9dbe56b, the commit before this slice, with `tests/fed_legacy_digest.py`; scripted match N3,N2,N1,H, seed 250925, 3 days, every observation JSON + prompt text + action/result + event + 3 end-of-day universe states):

- every tw2002 `*_MODE` flipped to legacy: `00135a9202e44a0e085ce978` (in the suite);
- only `SHIP_TW_MODE` flipped, every other switch at its default: `85fb398575b2a69e92e0bc17`, identical to 9dbe56b at defaults (QC check, recorded in the test file; not in the suite because later slices that retune tw2002 play will move it).

## Rules table

| # | rule | mark and source | this slice | test |
| --- | --- | --- | --- | --- |
| tw1 | Only ISS, Corporate FlagShip and Havoc Gunstar may buy or fit a drive. Interdictor and escape pod cannot. | CONFIRMED: docs wiki TransWarp_Drive.html ("available only to the Imperial StarShip, Corporate FlagShip, and Havoc Gunstar"); Gypsy Hardware Emporium `<W>` ("Only Imperial Starships, Corporate Flagships and Havoc Gunstars"); EIS HardwareMenu; Bible ship charts. | `buy_equip item=transwarp_drive` hidden and refused on every other hull. | `test_tw1_buy_only_on_tw_hulls_at_stardock` |
| tw2 | Bought at the StarDock Hardware Emporium only (sector 1). Class 0 does not sell it. | CONFIRMED: docs wiki, Gypsy, EIS HardwareMenu. | Hidden and refused at Alpha Centauri / Rylos / anywhere else, and under legacy. | `test_tw2_buy_at_stardock_only_and_never_under_legacy` |
| tw3 | Type 1 costs 12,500. Type II 20,000 and the 9,000 upgrade are recorded, out of scope. | CONFIRMED as the TEDIT sample: cabal twgs.html ("Type I TWarp : $12,500"). | `SHIP_TW_TYPE1_COST = 12_500`; listed price = charged price. | `test_tw3_type1_price_is_12500` |
| tw4 | One drive per ship; no Type 2 / upgrade item. | CONFIRMED in shape: HardwareMenu sells it once. | `Ship.transwarp_drive` is `None` or `"type1"`; a second buy is refused "already fitted". | `test_tw4_one_drive_per_ship_and_no_type2` |
| tw5 | Trade-in and death drop the drive with the hull; the escape pod has none. | CONFIRMED in shape: Bible pod; HardwareMenu extras go with the ship. | `_strip_ship` (death) and `buy_ship` (trade-in) clear it. | `test_tw5_drive_lost_on_pod_and_trade_in` |
| tw6 | Verb `ship_transwarp {sector_id}`, not `planet_transwarp`. Refused without a drive, on a planet, in a fighter challenge, or without the turn cost. Cloak: allowed, decloaks on arrival. | Verb name is this game's. Cloak policy UNVERIFIED. | `SHIP_TW_CLOAK_POLICY = "allow_decloak"`. | `test_tw6_no_drive_refused_and_challenge_refused`, `test_tw6_cloak_drops_on_arrival` |
| tw7 | Lock: the destination holds at least one fighter of yours, a corp-mate's, or an ally's. Enemy fighters do not lock. | CONFIRMED own fighter: docs wiki ("jump to a sector containing at least one friendly fighter"), Gypsy ("at least one fighter in your destination sector"), cabal glossary Blind Warp. Corp CONFIRMED (corp play). Allies UNVERIFIED (this game's stand-in for corp). | `SHIP_TW_FRIENDLY = "own_corp_ally"` via `combat._are_allied`; `own_only` switch. | `test_tw7_corp_and_ally_fighters_lock_enemy_does_not` |
| tw8 | A commissioned trader (alignment >= 1000) may jump into FedSpace 1..10 with no fighter there; below 1000 FedSpace needs a fighter lock like anywhere else. | CONFIRMED: docs wiki Imperial_StarShip.html ("Commissioned players gain the ability to transwarp directly into FedSpace"); Gypsy ("Once you have a commission and an ISS, you can Twarp direct to fedspace (sectors 1-10 and SD)"). SOURCE-CONFLICT (minor): both sources talk about the ISS; the perk is given to all three TW hulls here (the commission is the gate). | `SHIP_TW_FED_LOCK = "commissioned"` uses `victory.is_commissioned`; `fighter_only` turns it off. FedSpace 1..10 join the legal list when the perk applies. | `test_tw8_commission_fedspace_lock` |
| tw9 | 3 Fuel Ore from the holds per hop of the shortest warp path (warps out, one-ways respected, avoids ignored). Same sector refused. Short ore refuses and consumes nothing. | CONFIRMED: Gypsy ("Twarp uses 3 fuel (from your holds) per sector distance"); docs wiki TransWarp_Drive.html ("three ore per warp along the shortest route"). | Local BFS (`ship_transwarp.hop_count`). | `test_tw9_locked_jump_burns_three_ore_per_hop`, `test_tw9_hop_metric_is_shortest_path_along_warps_out` |
| tw10 | Range is floor(ore aboard / 3); holds cap the ore. Havoc with 50 holds of ore is 16 hops. | CONFIRMED as the holds/3 reading of MBBS / Bible "TransWarp range 16" for the Havoc. | No per-hull range constant; `ship.transwarp.max_hops_now`. | `test_tw10_max_hops_is_ore_over_three` |
| tw11 | Turn cost = the time of one adjacent warp. | Real-time wording CONFIRMED (docs wiki); the turn mapping is UNVERIFIED. | Default one ship TPW (`runner._warp_cost_for`); `hops` = TPW x hops. Planet TransWarp turns untouched. | `test_tw11_turn_cost_is_one_ship_tpw_and_hops_switch` |
| tw12 | Arrival is a normal sector entry: carried-photon, NavHaz, limpet, armid, quasar, fighters, avoid prompt; `arrived_by_transwarp` set, cleared on the next warp or liftoff; no retreat while it is set. A planetary Interdictor holds a TransWarp out like a warp. After the move the evil-ISS repossession check runs, as after a warp. | CONFIRMED in shape: docs wiki; gap 5.10 / REV / cabal fleeing.html ("Cannot retreat if you arrived by ... TransWarp"). Interdictor CONFIRMED: cabal planets.html ("attempt to back out of the sector or TransWarp out, the Interdictor will use 500 fuel ore preventing you from leaving"). | `ship_transwarp._land` reuses the warp hazard helpers; `combat.retreat_block`; `runner._try_interdict`; `fed.check_iss_repo_on_move`. | `test_tw12_retreat_blocked_until_a_normal_warp`, `test_tw12_locked_arrival_still_runs_sector_hazards`, `test_tw12_planet_interdictor_holds_a_transwarp_out` |
| tw13 | No friendly fighter and no commission FedSpace lock = blind jump. | CONFIRMED: docs wiki Blind Jumping; cabal glossary; Gypsy. | | `test_tw14_blind_density0_succeeds_and_dense_fuses` |
| tw14 | Blind succeeds only into density exactly 0; density > 0 destroys the ship (`transwarp_fuse`, DEATH_MODE pod). A lone limpet is enough. | CONFIRMED: docs wiki ("destination sector must have zero density ... your ship will be destroyed"); Gypsy ("safe as long as the destination sector is completely empty. If it's not, you get a shinny new escape pod"). | `scanners.density_reading` (fighters, mines, ships, Ferrengi hulls, ports, planets, Terra, Feds, NavHaz, beacons). `refuse` switch. | `test_tw14_blind_density0_succeeds_and_dense_fuses`, `test_tw14_limpet_alone_fuses`, `test_tw14_refuse_switch_hides_and_refuses_blind` |
| tw15 | A fuse still spends the ore and the turns. | UNVERIFIED. | `SHIP_TW_FUSE_REFUNDS = False`. | `test_tw15_fuse_spends_ore_and_turns` |
| tw16 | The original asks "are you sure" on a blind jump. | Deliberate difference. | The legal list lists locks only (+ commission FedSpace); forged args still run tw14. Legal list == handler. | `test_tw16_legal_list_matches_handler_and_never_lists_blind`, `test_tw16_legal_list_off_when_drive_ore_or_turns_short` |
| tw17 | No `universe.rng` draw for the hop search, legal list or a quiet locked jump. | Deliberate (seed digests stay put). | | `test_tw17_hop_search_and_locked_jump_do_not_draw_rng` |
| tw18 | No Type 2, tow, transporter, multi-ship, parking, furbing. | Out of scope. | Items/verbs absent. | `test_tw4_one_drive_per_ship_and_no_type2` |
| tw19 | Planet TransWarp is a separate handler, not retuned. | Already built. | | `test_tw19_planet_transwarp_is_a_different_handler` + `tests/test_planet_transwarp_v1.py` |
| tw20 | Own ship block `transwarp: {fitted, ore_per_hop, max_hops_now, fed_lock}`; legal params `sector_id.choices/hops_by/ore_by`. Events `ship_transwarp` (actor + destination occupants; facts from/to/hops/ore/locked/blind) and `ship_transwarp_fuse` (actor only + spectator). No other seat sees your drive or ore. | This game's fog rule. | `observation._ACTOR_ONLY_EVENTS` gains the fuse. | `test_tw20_other_seats_never_see_the_drive_ore_or_fuse`, `test_tw20_arrival_is_seen_by_destination_occupants` |
| tw21 | LLM prompt paragraph: who can buy, 12,500, 3 ore/hop, lock vs blind fuse, commission perk, never blind-jump, not planet TransWarp. Off under legacy. | This slice. | `agents/prompts._SHIP_TW_NOTE`. | `test_tw21_prompt_names_the_drive` |
| tw22 | Spectator draws the jump as a move line from origin to destination and a fuse flash. | This slice. | `web/app.js` (warp trail handles `ship_transwarp`; combat flash on `ship_transwarp_fuse`), `web/bot.js` verb form + combat group button. | manual |

## Bots

- `seat_brain`: `_transwarp_instead` swaps a ladder `plot_course`/`warp` whose target is on the `ship_transwarp` legal list when the jump saves `SHIP_TW_MIN_TURNS_SAVED` (8)+ turns over walking and the jump ore is aboard; drive owners hold back only the ore of their planned jump (SHIP_FLEET.md Bots). Never a blind target (not listed). `_buy_transwarp_drive` buys at StarDock only when the engine lists the drive (TW hull, no drive) and `SHIP_TW_SPARE_CASH` (150,000) / working capital stays in the bank. Under legacy both no-op (no legal entry, no shelf item).
- `heuristic` (H): only a listed StarDock lock (commissioned FedSpace or own fighter), 3+ hops, 2x ore, credits > 50k.
- Tests: `test_bots_swap_a_long_walk_for_a_listed_lock_only`, `test_bots_buy_the_drive_only_on_a_tw_hull_with_spare_cash`, `test_heuristic_jumps_only_to_a_stardock_lock`.

## Deliberate differences

- Type 2, the upgrade, multi-ship, the ship transporter, tractor towing and furbing wait for a later slice.
- No interactive confirm. The legal list simply omits blind targets; a forged blind jump still follows tw14.
- One ship turns-per-warp stands in for the real-time "same time as an adjacent warp" (`hops` is the other reading).
- Ally fighters count as a lock (the original is corp-centric).
- The commission FedSpace lock applies to all three TW hulls (sources describe the ISS).
- Federation nav-beacon locks are not modelled; marker beacons are player hardware and do not lock.
- Jumping while cloaked is allowed and decloaks on arrival (UNVERIFIED).
- A fuse spends the turns and the ore (UNVERIFIED).
- No XP is awarded for a TransWarp (a normal warp awards `warp` XP here; the original has no XP for moves).
- Toll fighters cannot block a locked arrival: one fighter deployment per sector, and a lock means it is friendly.
- StarDock stays sector 1, so the commission jump to StarDock is a jump to sector 1.
- `Ship.transwarp_drive` and `Player.arrived_by_transwarp` are left out of model dumps while unset so legacy dumps stay byte-identical; once set they are saved and restored (SHIP_FLEET.md Saves).
- Day-10 trade bots rarely own an ISS / FlagShip / Havoc, so a scripted match may show zero buys and jumps. That is reported, not forced.

- Follow-up after d632aae: `K.SHIP_TW_FED_LOCK_HULLS = "all_tw"` (default, the commission FedSpace lock on all three TW hulls) | `"iss_only"`; see SHIP_FLEET.md add-ons. Test: test_fed_lock_hulls_switch.
