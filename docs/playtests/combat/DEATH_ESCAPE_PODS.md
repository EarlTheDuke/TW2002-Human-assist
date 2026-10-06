# Death and escape pods

Rules table first, then what the engine does. Sources are the files under `docs/reference/tw2002/` (the gap map rows are 5.12 to 5.15). Marks: CONFIRMED (a source prints it), SOURCE-CONFLICT (sources disagree, the reading is given), UNVERIFIED (no source prints it; the value here is chosen and says so).

Today's build (before this slice, kept as `DEATH_MODE = "legacy"`): a destroyed ship sends the pilot to StarDock in a fresh Merchant Cruiser, cargo and equipment are lost, credits drop to 75 percent, `deaths` goes up by one, and the third death removes the player from the match for good (planets they own alone become unclaimed).

## Rules table

| # | rule | original | mark and source | this slice |
| --- | --- | --- | --- | --- |
| d1 | A ship with a pod | When the ship is destroyed the pilot rushes to the escape pod and abandons ship. The pod is a ship of its own. | CONFIRMED. `stardock_manuals_and_text_docs/Misc_shipodds.txt` ("You rush to an escape pod and abandon ship... Your trusty Escape Pod is functioning normally"). `stardock_manuals_and_text_docs/Someguy_MBBS_manual.txt` ("0) Escape Pod: This is what you wind up in when your ship gets blown up"). | Built. The hull becomes `escape_pod`. |
| d2 | The pod hull | Bible chart: cost 0 (cannot be bought), 6 turns per warp, odds 0.6:1, 50 fighters max and 10 per attack, 50 holds, 50 shields, no mines, no photon, no TransWarp, no genesis. MBBS chart: 5 holds, 50 fighters, 50 shields, odds 0.7, 6 turns. | SOURCE-CONFLICT on holds (50 or 5) and odds (0.6 or 0.7). `S3_tw2002_bible_v1.htm` ship chart, `stardock_manuals_and_text_docs/Someguy_MBBS_manual.txt` ship table. The Bible (TWGS) is taken for the caps and the odds. What a fresh pod carries is UNVERIFIED. | Built as the Bible caps and odds. A fresh pod has 5 empty holds (the MBBS figure), 0 fighters, 0 shields. |
| d3 | Hulls with no pod | The Scout Marauder has no pod. A pilot already in a pod has nothing left to eject into. | CONFIRMED. `stardock_manuals_and_text_docs/Gypsy_Big_Dummies_Guide.html` ("Scouts also have NO pod if you die in a scout you are out of the game until 12am the following day"). `Someguy_MBBS_manual.txt` (Scout "does not have an escape pod"; killed "in a Scout Marauder or in a Pod, you are Dead for the day"). `stardock_manuals_and_text_docs/TWFAQ_TW2002.faq.txt` item 12 shows the scout pod was argued about between versions. | Built. `scout_marauder` and `escape_pod` go straight to Ship Destroyed. |
| d4 | Where the pod goes, killed by someone else | The pod flees along a "safe path": pick a bunch of random sectors 3 to 20 hops away, plot to them, and move as far along one path as possible through safe sectors. Safe means empty, or holding your own or your corp's fighters. If every first hop is unsafe the pod stays where the ship died. | CONFIRMED for the method. `cabal_strategy_site/pods.html` (Dr. Bad, written for TWGS .55; the author says the 3 and 20 are not exact and that the rules changed often). `stardock_modernmanual/reference__pod-mechanics.md` repeats it. How many random sectors, and which path wins, is UNVERIFIED. | Built. 5 random targets 3 to 20 hops away (seeded), shortest paths, the pod takes the path that gets farthest. Safe = no deployed fighters of a player outside your corp. Mines do not count (the article leaves mines open). |
| d5 | Where the pod goes, self-inflicted | The pod goes to your "previous sector". Self-inflicted means you pressed the keys: quasar cannons, military reaction, navigation hazard, offensive sector fighters, attacking Captain Z. Someone else pressed the keys when their fighters hit your ship, or they blew up the planet or port you were on. | CONFIRMED. `cabal_strategy_site/pods.html`. | Built. Killed by someone else: another player's ship attack, a Ferrengi attack (UNVERIFIED that an NPC counts as "someone"). Self-inflicted: mines, sector fighters, planet defences and quasar cannons, an attacker that loses its own attack, surrender. No previous sector yet: the pod stays (UNVERIFIED). |
| d6 | What sets the previous sector | Manual warp or retreat: the sector you left. Transport ship to ship: the sector you left. TransWarp: the destination. B-warp: unchanged. Planet warp: sector 1 in older builds, unchanged later. | CONFIRMED. `cabal_strategy_site/pods.html`, `reference__pod-mechanics.md`. What a flee sets is left as "an exercise for the reader". | Built for warp, autopilot hops (each is a warp) and retreat. Planet transporter, planet TransWarp and the combat flee leave it alone (UNVERIFIED for those engine moves). |
| d7 | The pod meets nothing on arrival | v3.11 fixed a bug where a pilot destroyed by a quasar cannon "still had to face fighters in the escape pod". | CONFIRMED for that case. `classictw_museum_wiki/tw-attac_TW2002_v3_revision_history_to_v3.11.html` (pending v3.11). Applying it to every arrival is UNVERIFIED. | Built. Mines, fighters and quasar cannons do not fire on the pod's arrival, and no challenge opens. |
| d8 | Experience when podded | Lose 10 percent of experience, no alignment. | CONFIRMED. `cabal_strategy_site/formulas.html` ("If you are podded, you loose 10% of your exp"; "-10% exp and -0% align if podded", tested on Gold and MBBS). `Someguy_MBBS_manual.txt` ("you lose 10% of your XP points"). Rounding is UNVERIFIED. | Built. The loss rounds down. |
| d9 | Ship Destroyed (#SD#) | Blown up in a pod, in a hull with no pod, or a third time in one day: lose 50 percent of experience and 50 percent of alignment, and stay out of the game until midnight. | CONFIRMED. `formulas.html` ("If you are #SD#, then you loose 50% of your exp, and 50% of your alignment"). `Someguy_MBBS_manual.txt` ("Dead for the day, and lose 50% of your XP points"). `classictw_docs_wiki/Ship_Destroyed.html`. `S7_softdocs_slice-10.txt` #16 (lost pod, "couldn't get back into the game until the next day"). `classictw_docs_wiki/Glossary.html` Midnight ("Players that died the previous day are allowed back in"). | Built. Experience and alignment move halfway to zero (rounded toward zero). No turns are left today. |
| d10 | Pods per day | Two pods a day. The third loss that day is Ship Destroyed even if the ship has a pod. The count resets at extern ("Recover deaths (2 pods)"). | CONFIRMED. `tw-attac_TW2002_v3_revision_history_to_v3.11.html` ("Limit of 2 pods per user per day is now enforced as in MBBS"). `Someguy_MBBS_manual.txt`. `S1_planet_handbook_v1.01.html` ("podded twice per day and survive, but the third podding will destroy your ship"). `classictw_docs_wiki/Glossary.html` Extern item 8. SOURCE-CONFLICT on scope: `Ship_Destroyed.html` counts losses "while piloting the same ship number" (anti cross-podding). | Built per player per game day (the v3 line). The count resets at the day tick. |
| d11 | Coming back after #SD# | The next day you start in a Scout Marauder the game gives you. | CONFIRMED. `stardock_manuals_and_text_docs/Iago_War_Manual.txt` ("attack a port at the end of your turns for the day. The next day, you'll start in a scout"; "Players in scouts may have gotten them due to getting an escape pod blown up"). `stardock_manuals_and_text_docs/Gypsy_Big_Dummies_Guide.html` ("get *Ship Destroyed* the game will give you one for free"). Where you start is UNVERIFIED. | Built. The free scout is parked at StarDock at once; the pilot has no turns until the next day. |
| d12 | Death delay | A sysop setting. 0 (the 1.0x behaviour) lets you fly the pod at once; 1 or more keeps you out in the pod past that many midnights. Not shown on the V screen. | CONFIRMED. `S7_softdocs_slice-10.txt` #16. | Not built. This game behaves as death delay 0. |
| d13 | Self-destruct | Costs 50 percent of experience and the ship, and keeps you out today and tomorrow. | CONFIRMED. `Someguy_MBBS_manual.txt`, `stardock_manuals_and_text_docs/Iago_War_Manual.txt`, `S7_softdocs_slice-10.txt`. | Not built. There is no self-destruct verb. |
| d14 | Credits on hand | No source says a podded or #SD# pilot loses credits on hand. | UNVERIFIED. | Kept in `BANK_MODE` legacy (today's build keeps 75 percent). Lost in tw2002 (gb13, `GALACTIC_BANK_TAX.md`). |
| d15 | Cargo and equipment | They go with the ship. The pod starts empty. | UNVERIFIED (no source lists it; the pod chart has no room for them). | Built: cargo, fighters, shields, mines, genesis, photons and probes are lost. |
| d16 | What the killer gets | Experience +10 percent of the victim's and alignment +50 percent of the victim's for a pod or #SD# kill. Credits can be recovered "for destroying ships other than escape pod and marauder". The winner may salvage the wreck ("TOO excellent! You can't salvage anything from it!"); holds go to the attacker (furbing). | CONFIRMED that these exist: `formulas.html`, `tw-attac_TW2002_v3_revision_history_to_v3.11.html`, `Misc_shipodds.txt`, `eis_tw2002_v3_docs/Tactical.html`. The credit amount and the salvage amounts are UNVERIFIED. | Not built on purpose. Kill rewards are gap row 9.3 and salvage is row 5.15, both their own slices. The killer keeps today's rewards. |
| d17 | Trading the pod in | Never stay in a pod; trade it for a Scout right away. The pod has enough resale value to buy one. | CONFIRMED. `stardock_manuals_and_text_docs/Iago_War_Manual.txt` ("You can trade it in for a scout right away, and you should"). `Someguy_MBBS_manual.txt` ("the pod has enough resale value to buy one"). The Bible's "0 / NA" is the purchase price. | Built. The pod is worth a Scout: at StarDock it buys a Scout at no cost, and toward any other hull it counts as a Scout's trade-in (25 percent of 15,950). The pod is never for sale. (QC: it used to count as the full Scout price toward anything, which made losing a ship worth more than trading it in.) |
| d18 | A pod cannot be captured | Only destroyed. | CONFIRMED. `Someguy_MBBS_manual.txt`; `tw-attac_TW2002_v3_revision_history_to_v3.11.html` ("Can't capture when the ship is a Scout Marauder or Escape Pod"). | Built in ship-capture-v1: under CAPTURE_PODLESS never, a pod or Scout is destroyed. See docs/playtests/ships/SHIP_CAPTURE.md cp4. |
| d19 | Permanent elimination | The original has none; a dead player is back the next day. TWGS tournaments add a "Lockout Mode": "Pods and Deaths", "Deaths Only" or "None", with a kill threshold. | CONFIRMED. `classictw_museum_wiki/TWGS_v2_Revision_History.html`. | Built as the game setting `GameConfig.elimination_deaths`. Unset means the mode default: 3 in legacy, off in tw2002. A number turns on elimination after that many ship losses, pods and deaths alike ("Pods and Deaths"). "Deaths Only" is not built. |
| d20 | Surrender | Defensive and toll fighters let you "surrender your ship". TWGS warns you if you still have fighters. | CONFIRMED that the ship is given up (`formulas.html`, `TWGS_v2_Revision_History.html`). That the pilot then gets the pod is UNVERIFIED: it follows from d1 (a lost ship with a pod is a pod) and d5 (you pressed the key, so the previous sector). | Built. Surrender runs the death path with the pod rules: the pod goes to the previous sector (the sector the challenge came from), 10 percent experience, and it counts toward the two pods a day. A scout or pod that surrenders is Ship Destroyed. |

## Switch

`K.DEATH_MODE` defaults to `tw2002`. `legacy` is the old path, unchanged: StarDock, a fresh Merchant Cruiser, credits x0.75, and elimination at `K.MAX_DEATHS_BEFORE_ELIM` (3). `GameConfig.elimination_deaths` overrides the threshold in either mode (0 turns elimination off).

## What the engine does (tw2002)

`combat._destroy_ship(universe, pid, reason, killer_id, by_other=False)` is the one place a ship is lost. In tw2002 it runs `_destroy_ship_tw2002`:

1. `deaths` goes up by one and the `last_death_*` fields are set, as before.
2. A new game day resets `pods_today`. Two pods a day: the ship gets a pod when its hull is not in `K.PODLESS_HULLS` and `pods_today` is under `K.PODS_PER_DAY` (2).
3. Pod: `pods_today` goes up, experience drops 10 percent (rounded down), the ship becomes an `escape_pod` with 5 empty holds and nothing else, and the pod lands in `_pod_destination`: the safe path (`_pod_safe_path`) when `by_other`, otherwise the previous sector. Placement skips every arrival hazard.
4. Ship Destroyed: experience and alignment drop 50 percent, the ship becomes a free `scout_marauder` at StarDock, and `turns_today` is set to `turns_per_day` so nothing that costs a turn is legal until the day tick.
5. `SHIP_DESTROYED` carries `outcome` (`escape_pod` or `ship_destroyed`), `pod_sector`, `pods_today`, `exp_lost` and `align_lost`. The observation shows the victim `outcome` only; `pod_sector` stays out of the event facts and out of the summary text ("escaped in a pod [pod 1/2 today]") so the killer and the witnesses do not learn where the pod went (fog). The pod sector, or StarDock for the free Scout, goes on the pilot's own map.
6. Elimination runs only when `K.elimination_deaths(config)` is non-zero.

`by_other=True` is passed by the ship-to-ship defender loss (`_defender_destroyed`) and the Ferrengi kill. Every other loss is self-inflicted.

Warp sets `prev_sector_id` to the sector left, just before the hazards in the new sector run; a tw2002 loss on entry leaves the pilot where the pod went instead of moving it on. Retreat sets `prev_sector_id` to the sector retreated from. In tw2002 `apply_action` clamps `turns_today` to `turns_per_day` so a Ship Destroyed day never shows negative turns.

The pod uses the shared hull lookup `K.hull_spec` everywhere the roster was used for the current ship (warp cost in the legal list and the handler, equipment room, combat odds, planet waves, observation caps). `K.ship_specs()` still lists only what StarDock sells, so the pod is never offered. A pod is worth a Scout: `K.net_hull_cost("escape_pod", "scout_marauder")` is 0, and `K.trade_in_credit("escape_pod")` is a Scout's trade-in (3,987) toward anything else, the same as taking the free Scout and trading that in.

The observation adds two action hints in tw2002: "YOU ARE IN AN ESCAPE POD ..." (go to StarDock and trade it for a Scout or better) and the warning after two losses in a day that the next one is SHIP DESTROYED. The seat prompt's death line and the survival question were rewritten to match. Lives in the cockpit and the bot sidebar show "no limit" when elimination is off.

## Deliberate differences

- Kill rewards (experience and alignment for the killer, credit recovery) and salvage or furbing are not built (d16). They belong to gap rows 9.3 and 5.15.
- Death delay is 0 (d12). Self-destruct is not built (d13).
- A Ferrengi kill counts as "someone else" and walks the safe path (d5, UNVERIFIED).
- The pod meets nothing on arrival anywhere, not only after a quasar kill (d7).
- Credits on hand are kept (d14); today's build took 25 percent.
- The free Scout after Ship Destroyed is parked at StarDock at once, with no turns left today (d11).
- Two pods a day is counted per player per game day, not per ship number (d10).
- Elimination is a game setting, off by default in tw2002; "Deaths Only" lockout is not built (d19).
- A Ship Destroyed pilot can still use verbs that cost no turns (for example buying a ship at StarDock); everything that costs a turn waits for the day tick.
- A Ferrengi kill during the day tick happens after the turn reset, so a Ship Destroyed from it costs that whole new day.
- Planet transporter, planet TransWarp and the combat flee do not change the previous sector (d6).
- The media fixtures (`scripts/media_record_fixtures.py`) pin `DEATH_MODE = "legacy"`, the same way they pin `COMBAT_MODE`, so the recorded clips stay byte-stable.
- Legacy unchanged: `DEATH_MODE = "legacy"` gives StarDock, a fresh Merchant Cruiser, credits x0.75 and elimination on the 3rd death, checked by golden rows recorded on 019987d.

## Seat brains

The seat brains (N1, N2, N3) get one small new rung, `_leave_pod`, right after answering a fighter challenge. In a pod at StarDock they trade it in: a Cargotran if they can afford it above their cash buffer, otherwise a Scout (no cost). Away from StarDock they plot a course to StarDock, through the ship-combat QC check `_avoid_held` so a pod does not fly back into fighters it retreated from today. Everything goes through the legal list, so no rejected actions. The heuristic seat (H) gets the same rung, `HeuristicAgent._leave_pod` (QC: before it wandered in the pod and never reached StarDock, and it had no ship purchase at all). It also caps its StarDock fighter buy at the hull's legal room (a Scout holds fewer than it used to ask for) and WAITs when the only thing stopping a warp is turns.

## Tests pinned to legacy

These older tests assert today's death (StarDock, merchant cruiser, credits x0.75, elimination) and now pin `DEATH_MODE = "legacy"` with monkeypatch: `test_engine.py` (`test_pvp_kill_respawns_victim_without_crash`, `test_pvp_kill_elimination_after_max_deaths`), `test_interdictor_v1.py` (`test_the_quasar_can_destroy_the_held_ship`), `test_ports_turns_regen_tests_v1.py` (the death-ends-the-visit test), `test_siege_path_v1.py` (`test_attacker_loses_and_the_ship_is_destroyed`), `test_phase_abc.py` (a4, l4a, l13, l14, o2), and `test_ship_combat_core_v1.py` (the legacy golden test). In `test_ship_combat_core_v1.py` the beating-defence and surrender tests now expect a pod. `scripts/planet_invariants_fuzz.py` skips its x0.75 credit check when the event has an `outcome`.

## Scripted match (before and after)

`scripts/run_scripted_match.py --seats N3,N3,N2,N2,N1,H --seed 250925 --days 10`. Before = d5bf0c1 (same numbers as 019987d), after = this slice.

| Seat | Net worth before | after | Credits before | after | Ship after | Planets | Deaths | Sells before / after | Rejected (check/engine) after |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N3-P1 | 891,932 | 884,249 | 700,959 | 693,276 | cargotran | 3 | 0 | 243 / 240 | 0/0 |
| N3-P2 | 737,794 | 758,742 | 573,373 | 587,421 | cargotran | 3 | 0 | 235 / 235 | 0/0 |
| N2-P4 | 597,840 | 612,615 | 384,365 | 394,856 | cargotran | 2 | 0 | 219 / 222 | 0/0 |
| N2-P3 | 548,778 | 557,047 | 361,087 | 368,106 | cargotran | 2 | 1 | 242 / 236 | 0/0 |
| N1-P5 | 411,004 | 406,374 | 306,300 | 300,150 | merchant_cruiser | 2 | 0 | 359 / 357 | 0/0 |
| H-P6 | 41,170 | 41,170 | 18,400 | 18,400 | merchant_cruiser | 0 | 0 | 0 / 0 | 0/9 (same as before) |

The one loss: day 7, a Ferrengi kills N2-P3 in sector 643. Before: ejected to StarDock in a Merchant Cruiser with credits x0.75. After: escape pod to sector 38 by the safe path (pod 1/2 today, 212 experience lost, credits kept); the seat flew the pod to StarDock the same day (12 warps) and traded it for a Cargotran at 36,000 net (the pod counts as a Scout's price). The other seats shift a little because the pod's flight changes who is where at the ports from day 7.

## Planted bugs

21 plants, one at a time, on the real engine path (the harness restores each file byte for byte and checks its sha256). Tests run: `tests/test_death_escape_pods_v1.py` and `tests/test_ship_combat_core_v1.py`. Caught 21 of 21.

| # | planted bug | where | caught by |
| --- | --- | --- | --- |
| p1 | pod exp loss not applied | handler | `test_self_inflicted_loss_puts_the_pod_in_the_previous_sector`, `test_surrender_takes_the_pod_to_the_previous_sector`, `test_third_loss_in_a_day_is_ship_destroyed_and_the_count_resets` |
| p2 | pods-per-day limit off by one (<=) | handler | `test_fuzz_random_deaths_all_sixteen_hulls`, `test_third_loss_in_a_day_is_ship_destroyed_and_the_count_resets` |
| p3 | pod counter never resets at a new day | handler | `test_third_loss_in_a_day_is_ship_destroyed_and_the_count_resets` |
| p4 | scout treated as having a pod | handler | `test_a_podless_hull_is_ship_destroyed[escape_pod]`, `test_a_podless_hull_is_ship_destroyed[scout_marauder]`, `test_a_scout_that_surrenders_is_ship_destroyed` ... |
| p5 | Ship Destroyed alignment not halved | handler | `test_a_podless_hull_is_ship_destroyed[escape_pod]`, `test_a_podless_hull_is_ship_destroyed[scout_marauder]` |
| p6 | Ship Destroyed not locked out until midnight | handler | `test_a_podless_hull_is_ship_destroyed[escape_pod]`, `test_a_podless_hull_is_ship_destroyed[scout_marauder]`, `test_a_scout_that_surrenders_is_ship_destroyed` ... |
| p7 | safe path ignores hostile fighters | handler | `test_fuzz_random_deaths_all_sixteen_hulls`, `test_killed_by_another_player_walks_the_safe_path`, `test_surrounded_pod_stays_in_the_death_sector` |
| p8 | self-inflicted loss takes the safe path | handler | `test_a_pod_meets_nothing_on_arrival`, `test_fuzz_random_deaths_all_sixteen_hulls`, `test_no_previous_sector_leaves_the_pod_where_it_died` ... |
| p9 | credits x0.75 kept in tw2002 | handler | `test_fuzz_random_deaths_all_sixteen_hulls`, `test_self_inflicted_loss_puts_the_pod_in_the_previous_sector`, `test_surrender_takes_the_existing_death_with_a_warning` |
| p10 | elimination ignores the game setting | handler | `test_elimination_deaths_setting_turns_it_on` |
| p11 | legacy path drifts (credits x0.8) | handler | `test_legacy_mine_warp_is_unchanged`, `test_legacy_mode_is_unchanged` |
| p12 | warp does not set the previous sector | handler | `test_a_retreat_sets_the_previous_sector`, `test_surrender_takes_the_existing_death_with_a_warning`, `test_surrender_takes_the_pod_to_the_previous_sector` |
| p13 | retreat does not set the previous sector | handler | `test_a_retreat_sets_the_previous_sector` |
| p14 | pod moved on into the sector that killed it | handler | `test_self_inflicted_loss_puts_the_pod_in_the_previous_sector`, `test_ship_destroyed_inside_an_action_never_runs_past_the_day` |
| p15 | Ship Destroyed turns not clamped on later actions | handler | `test_a_scout_that_surrenders_is_ship_destroyed`, `test_ship_destroyed_inside_an_action_never_runs_past_the_day` |
| p16 | pod warp cost missed (falls back to the default 2) | legal list | `test_the_pod_flies_slow_and_carries_little` |
| p17 | pod warp cost missed (falls back to the default 2) | handler | `test_the_pod_flies_slow_and_carries_little` |
| p18 | escape pod offered for sale | legal list | `test_the_pod_trades_for_a_scout_at_no_cost` |
| p19 | pod trade-in worth 0 (legal list net cost and handler) | legal list + handler | `test_a_pod_buying_a_bigger_hull_counts_as_a_scout_trade_in` (renamed in QC), `test_seat_brains_in_a_pod_stay_legal[stardock]`, `test_switch_defaults_and_the_pod_hull` ... |
| p20 | pod equipment caps ignored | legal list + handler | `test_switch_defaults_and_the_pod_hull`, `test_the_pod_flies_slow_and_carries_little` |
| p21 | pod sector leaked through fog | observation | `test_observation_shows_the_pod_and_hides_where_it_went_from_others` |

## QC fixes (escape pods QC fixes)

Independent QC of 4b8fd31. Tests: `tests/test_death_escape_pods_qc_v1.py` (each failed on 4b8fd31).

| # | Bug | Fix |
| --- | --- | --- |
| q1 | Fog leak: the `SHIP_DESTROYED` summary said "escaped in a pod to sector N", and the killer and every witness see the summary. The killer could chase the pod. | The summary no longer names the sector (`combat._destroy_ship_tw2002`). |
| q2 | Credits from nothing: the pod counted as the full Scout price (15,950) toward any hull, more than the 25 percent trade-in of every podded hull under 63,800 (Merchant Cruiser 10,325, Merchant Freighter 8,350). Surrendering a Merchant Cruiser and buying a Cargotran from the pod saved 5,625 credits over trading the live cruiser in. | The pod is worth a Scout (d17): a Scout at no cost, a Scout's trade-in toward anything else (`K.trade_in_credit`, `K.net_hull_cost`). |
| q3 | The heuristic seat (H) never left a pod: it had no ship purchase and no way to StarDock, so it wandered at 6 turns a warp every day, and ended each day on a rejected warp loop. | `HeuristicAgent._leave_pod`: plot to StarDock, trade the pod for a Cargotran or a Scout. |
| q4 | H in a Scout at StarDock (after Ship Destroyed or a pod trade) asked for 200 fighters past the Scout's cap: a 0-turn rejection loop. | The fighter buy is capped by the legal list's room. |
| q5 | The pod (and the free Scout) landed in a sector missing from the pilot's map (`known_sectors`, `known_warps`). | `combat._place` records it. |
| q6 | Pre-existing, made worse by 6-turn pod warps: H sent a warp it could not pay for at the end of the day. | H WAITs when only turns stop the warp. |

The scripted match table above was recorded before q2: the pod-to-Cargotran trade there would now cost 47,963 net, not 36,000.

Checked and left as is: legacy-pinned tests fail under tw2002 only on legacy assertions (StarDock, elimination, last-life hint, orphans); a Ship Destroyed pilot's zero-turn verbs mint nothing (see the QC notes); pods-per-day resets on the first loss of a new day and the hint checks `pods_day`.
