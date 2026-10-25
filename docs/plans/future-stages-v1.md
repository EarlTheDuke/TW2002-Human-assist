# future-stages-v1 (COMMANDER NOTE 58, part B)

Cursor's plan for the next stages, written as a comparison against `C:\Users\sugar\tw2002_reference\MASTER_PLAN.md` (Grok Bot, 2026-10-17). Plan only; no source, web, test or constants file was changed.

Stages covered: the AI cockpit player, the voice front end, the v3.11 profile rollout, the richer 2D map, and four parallel tracks with file ownership:
- A: combat and Ferrengi
- B: planets, citadels, economy
- C: cockpit, rules docs and map
- D: the AI player, then voice

Code read (read only): `C:\Users\sugar\qc_bridge\wt_wire` at its working tip. That tip includes NOTEs 55-57, which landed after MASTER_PLAN's base `c86958a` (NOTE 54). NOTE 59 is in progress in the same tree. Rules: `RULINGS_v311.md` s1-s7 and Addendum A. Rule questions go to v3.11 first, MBBS as tie-break.

## 1. Standing constraints (every slice below respects them)

1. Batch O stays on hold. Nothing here schedules it.
2. The 3D map stays out. Only 2D map layers are planned.
3. Every engine change lands behind a new flag whose default is legacy. Default games keep the bank pin `9b607d3dae940c0b1a69f6d7` and the 10-day digests `24863a3d` / `98a47c8a`.
4. Cockpit work goes behind `COCKPIT_LAYOUT=redesign`. `/bot` (`web/bot.html`, `bot.js`, `bot.css`, `bot-parity.js`) stays unchanged. A byte-hash test should guard it.
5. NOTE 59 (in progress) makes `V311_PROFILE` also turn on `KILL_CASH_MODE` (`kill_cash_held`: killer not paid) and a new `POD_CASH_MODE` (`pod_cash_live`: the pod keeps 25 credits), per RULINGS Addendum A. This plan treats both as part of the profile, so the profile has 62 helpers once NOTE 59 lands.

## 2. Where MASTER_PLAN is already out of date

MASTER_PLAN read the code at `c86958a` (NOTE 54). Since then:

| MASTER_PLAN row | It says | The tree now | Source |
|---|---|---|---|
| AI-b turn loop, AI-c gap logger, AI-d 10-day run | missing | Mostly done. NOTE 55 `CockpitSeat.run` plays whole days over HTTP, and its `SeatBrain` writes gap rows. Two 10-day runs exist (v2, and v3 with the cockpit block). | `agents/cockpit_seat.py` docstring; `docs/playtests/cockpit-ai-seat-v2/`, `-v3/` (`gaps.md`, `run10.txt`) |
| Top 10 #2, "build a v3.11 profile" | to do | Built. `V311_PROFILE` has 60 helpers, plus a 10-day soak. | `docs/plans/v311-profile-v1.md`, `docs/playtests/v311-profile-v1/README.md` |
| STARTING_PACKAGE, CITADEL_DAYS, SHIP_ROSTER, TURN_REGEN, LIVE_PACE, OFFENSIVE_CLASH | hold for Ben | Ruled by NOTE 57 from RULINGS s2-s6; inside the profile | `v311-profile-v1.md` rows 1-7 |
| SCR-a tax | Ben decision | `TAX_RULE_MODE` v311 (10% at 50,000 or more, good alignment only) is in the profile | RULINGS s7; `constants.py` `tax_terms` |
| CMB-h / A1 item 1, "tw2002 path keeps the victim's cash" | to do | Wrong per Addendum A: the victim's cash is destroyed and the pod holds 25 credits. NOTE 59 implements that. | RULINGS Addendum A T1-T6 |
| FIG-d / A2 item 2, offensive 1.25x wave | partial | Coded: `combat._offensive_wave_tw2002`, in the profile | `v311-profile-v1.md` item 5 |
| CIT-b, CITADEL_COST_MODE check | to verify | Checked. `CITADEL_FIDELITY_MODE` tw2002 (the default) already charges class goods, no credits. | `v311-profile-v1.md` row 3 |
| DAY-g "bots stall by day 2" | broken | The day-2 stall is fixed (`_is_day_done` under turn regen). The dead-end trap under `UNIVERSE_TOPOLOGY_MODE` is still open. | `server/runner.py` `_is_day_done`; soak README |
| SD-d roster | partial | The v3.34b 17-hull table loads under the profile (`SHIP_ROSTER_LIVE_TABLE`) | RULINGS s4 |

## 3. Agree / differ

| Topic | MASTER_PLAN | Cursor | Why |
|---|---|---|---|
| Four tracks with disjoint files | Yes | Agree, with more files named (section 6) | Collisions so far came from unowned files |
| Engine changes behind legacy-default flags | Yes | Agree | Pins and digests stay meaningful |
| CV-a, rerun the 135-case suite | Commander, once | Run it twice: profile off and profile on | The profile changes prices, costs and screens; both games must pass |
| v3.11 profile becomes the default for new games | One step: soak, then default | Two steps. (1) Default at the server and lobby layer (`tw2k serve --profile v311`, public lobby default). (2) Flip the stored constant only later, with a re-pin. | Flipping `V311_PROFILE` in `constants.py` changes the bank pin and both digests at once. A server-level default gives players the original rules with no re-pin. |
| Kill credits | Hold; A1 adds "victim keeps cash" | Profile sets `KILL_CASH_MODE` tw2002 and `POD_CASH_MODE` live (NOTE 59); drop A1 item 1 | Addendum A, live v3.34b: killer 0 in normal play, victim's cash gone, pod 25 credits |
| Ship-vs-ship odds (CMB-c) | Top 10 #8, A2 item 1 | Later, after a live test | The exact formula is UNVERIFIED (GAP 5.7). Addendum A shows a live test on Ben's TWGS can settle such numbers in an hour. Propose "Addendum B" (section 5.5) first. |
| Track D first slice | D1: turn loop, brain, gap logger, 3-day run | Mostly done. Re-scope D1 to: the profile, an LLM brain option, and scenarios. | NOTEs 55-56 delivered the loop, the gap logger and two 10-day runs |
| Voice first step | D3.1: bring the `voice/` starter (streaming STT/TTS, Grok) onto the branch | Start with text orders, then browser push-to-talk, reusing the tested `/play` code paths (`web/play.js`, `tests/test_voice_ui_phase_h3..h5.py`). Streaming cloud voice is optional and late. | Browser speech is free and needs no server key. The starter needs paid keys that Ben's public site must not hold. |
| Map | MAP-b as one C1 item | Two slices with a named layer list and a fog rule (section 5.4) | "Layers not audited" is too vague to test |
| DAY-g bot escape | Top 10 #7, no track | Track B (bots live in B's files) | It had no owner |
| Bot brains (`agents/seat_brain.py`, `heuristic.py`, `war_brain.py` ...) | Not assigned | B owns the economy bots, A owns `war_brain.py` | `seat_brain.py` is 5,729 lines; two tracks editing it would collide |
| `server/app.py`, `server/runner.py`, `cli.py` | Not assigned | C until public-web starts, then the public-web stream (P) | The profile CLI flag, public mode and snapshots all land there |
| Commander-side work (CV-a, CV-g, LH-c/d/e, soaks, ACKs) | Commander | Agree, plus "Addendum B" live tests | |
| Port ranges per track | A 9101-9119, B 9121-9139, C 9141-9159, D 9161-9179 | Agree; public-web stream P 9181-9199 | |

## 4. What MASTER_PLAN misses

1. Public web (NOTE 58 part A). Plan in `public-web-v1.md`. It needs things the tracks must not break: one game per process, a switch overlay at worker start, snapshots, public-mode lockdown.
2. Day length. Under the profile one game day is 24 real hours (`TURN_REGEN_DAY_SECONDS`). The soak and the public site need a shorter day. `scripts/v311_soak.py --day-seconds` already does this inside its own process. It should become a supported server option recorded in the save.
3. Switch values are not saved. `meta.json` (`server/runner.py` `_open_save_sink`) stores config and seats, not the switches. A v3.11 save cannot be replayed reliably without them.
4. Wall-clock regen breaks exact replay. `engine/runner.py` refreshes turns from elapsed time, so re-executing `actions.jsonl` can drift under the profile. This affects replays, demos and resume.
5. Profile balance. Under `CLASS_M_FIDELITY_MODE`, a class M L1 citadel needs 1,000,000 colonists, but the free start planet has 191,000. In the soak no bot started a citadel; the bots also have no citadel step (soak README). Class M ratios stay Ben's call (NOTE 41 item 10), but the gap should be on the board.
6. Pod cash in the soak. P3 ended in a pod with 0 credits; Addendum A observed 25. NOTE 59's `POD_CASH_MODE` covers it; the soak should be rerun after NOTE 59.
7. Addendum A data as test vectors. T2 attacker screen: +1 exp for attacking, +20 exp for defeating, alignment -50, victim exp 200 -> 180. Use these for CMB-i (player-kill exp) instead of guessing from cabal formulas alone.
8. Security issues that matter once anything is public:
   - `agents/llm.py` `_mark_fallback` puts provider exception text into the `agent_fallback` event that every spectator receives.
   - `web/redesign.js` `esc()` (line 6) does not escape quotes; 93 `innerHTML` sites.
   - `/control/restart` accepts `custom_api_key` in its body.
   - `/api/*` is open when no spectator token is set.
   - The harness loopback check is void behind a reverse proxy.
9. The `/bot` byte guard. The constraint is stated, but no test proves `/bot` is unchanged after a cockpit slice.
10. Unowned shared files: `engine/legality.py` (legal actions for every kind), `engine/models.py` (fields, `EventKind`), `engine/actions.py` (`ActionKind`).
11. A live-test plan for the rules still UNVERIFIED (ship odds, toll per fighter, pods per day, corp-mate fighters in one sector, player-kill exp). Addendum A proved the method.
12. The AI seat's "explain" line. Voice report-back needs the seat to say in one line why it did each action. Today it writes gaps, not reasons.

## 5. Stage plans

### 5.1 AI cockpit player (Track D)

Now: `agents/cockpit_seat.py` (940 lines) reads five harness routes for its own seat and posts only `COCKPIT_KINDS`. A heuristic `SeatBrain` inside that file decides each turn. `scripts/cockpit_seat_run10.py` drives 10-day runs. In v3 (cockpit block on, 200 sectors, 100 turns a day, legacy rules) it ended at 605,169 net worth with 0 refused posts. The remaining gaps are marked "not in original" (`docs/playtests/cockpit-ai-seat-v3/gaps.md`).

| Stage | Content | Pass bar |
|---|---|---|
| D-1 profile | The seat plays under `V311_PROFILE` with a short day (worker overlay). Its brain reads prices, costs and rules from the reference page, not from constants. | 10-day run, 1,000 sectors, refused 0; gaps file regenerated; profile and legacy runs both recorded |
| D-2 LLM brain option | A second brain behind the same interface: prompt = the cockpit text the seat already reads, output = one `COCKPIT_KINDS` action. Uses the provider clients in `agents/llm.py`; never reads the universe. | 3-day run with each brain; refused under 1%; cost per day logged from `llm_usage` |
| D-3 scenarios | Trade loop; Terra colonists to a planet (1,000 per hold under the profile); citadel L1 start (short day); defend and attack; Ferrengi encounter | Each scenario a test on a scripted seed; no universe read (checked by request log) |
| D-4 versus code bots | AI seat vs N3 SeatBrain and heuristic bots, profile on | 10-day match finishes; standings by experience published; replayable from the redesign cockpit |
| D-5 explain and orders | One-line reason per action (shown in the cockpit log for the owner). The seat reads owner orders from a new per-seat route (C builds the route). | Every action in a 1-day run has a reason line; an order changes the next action in a scripted test |

### 5.2 Voice front end (Track D, after D-5)

| Stage | Content | Pass bar |
|---|---|---|
| V-0 text orders | Orders panel (new `web/voice.js`, `web/voice.css`, mounted by C in `redesign.html`) posts to `/harness/v1/{seat}/orders`. Quick commands parsed in the browser (`status`, `pause AI`, `resume AI`, `hold position`, `go to StarDock`). Free text becomes a directive. Risky verbs (attack, self-destruct, sell ship, transfer) need a confirm. | Scripted test: each quick command, one free-text order, one refused unconfirmed risky order |
| V-1 browser push-to-talk | `SpeechRecognition` push-to-talk and `speechSynthesis` readouts of acknowledgements, combat, docking, day end. Reuse the language and permission handling from `web/play.js`. | Chrome: order to acknowledgement under 3 s in a solo game; Firefox falls back to text with a clear note |
| V-2 game vocabulary | Number and sector parsing ("warp to forty two" -> 42), commodity names, port classes; a confirm prompt read back before risky orders | 50-phrase fixture list parsed correctly offline |
| V-3 one voiced day (VOX-d) | One full game day driven by voice on the profile, solo vs bots | Day finishes; transcript and action log replayable; no audio stored |
| V-4 server speech (optional) | faster-whisper on the server (`docs/LOCAL_STT_PLAN.md`), or streaming cloud STT/TTS with the user's own key (`2026-09-26-voice-layer-architecture.md`) | Only if V-1 support or accuracy is not enough; CPU cost measured |

Files: new `src/tw2k/voice/` (server parts, if any), `web/voice.js`, `web/voice.css`, `tests/test_voice_orders_*.py`. The existing top-level `voice/` starter (main tree only, not on this branch) stays a reference.

### 5.3 v3.11 profile rollout

| Stage | Content | Owner | Pass bar |
|---|---|---|---|
| R-0 built | 60 helpers, soak, rulings s2-s7 | done (NOTE 57) | - |
| R-1 kill cash | `KILL_CASH_MODE`, `POD_CASH_MODE` in the profile | NOTE 59 (in progress) | Profile-set test lists 62 helpers; pod 25 credits after a player kill; legacy pins unchanged |
| R-2 evidence | CV-a suite with profile off and on; 30-day soak with short day; AI seat 10 days on the profile (D-1); soak rerun after NOTE 59 | Commander + D | Suite failures under the profile triaged into A/B/C rows; soak rejected 0, exceptions 0 |
| R-3 server default | `tw2k serve --profile v311 --day-seconds N`, switch values written to `meta.json`, "Rules in force" visible in the cockpit (C1), public lobby default v3.11 | C (later P) | A served game with no flags is still legacy; with `--profile v311` the reference page lists the 62 switches as on |
| R-4 constant flip (Ben) | Set `V311_PROFILE = "v311"` in `constants.py`. Record new pins (bank pin and digests with the profile on), and keep the old pins in a test that sets legacy explicitly. | Ben decides; C implements | Both pin sets pass; release note lists every changed default |
| R-5 clean-up | Retire no-op switches (`TRADE_TURN_MODE`, `WARP_COST_MODE`, `ALIGNMENT_MODE`, `RANK_TITLES_MODE`, `COMBAT_ODDS_MODE`, `CORP_RULES_V2_MODE`, `COCKPIT_PARITY_MODE`). Mark `TW2002_LIVE_PROFILE` dev-only. | C | Tests that named them updated; no behaviour change |

New flags from A and B join the profile only after Ben rules on them (or a source is CONFIRMED). Joining is a C "profile intake" item: add the helper to `V311_PROFILE_HELPERS`, add `or v311_profile()` to the helper, and update `tests/test_v311_rulings_v1.py`, `tests/test_tw2002_live_profile_v1.py` and `docs/plans/v311-profile-v1.md` together.

Open profile items for Ben: class M ratios vs the 191,000-colonist start planet; two pods per day (CMB-g); `EXP_SCORE_MODE` confirm (it changes who wins). GAP 1.5 is closed: `STARDOCK_LOCATION_MODE` row 236, Ben approved the Commander recommendation 2026-10-24. A stored game still keeps StarDock in sector 1.

### 5.4 Richer 2D map (Track C; 3D is out)

Rule: every cockpit layer is built from the seat's own observation only (the fog the engine already applies, including `SCANNER_FOG_MODE` under the profile). Nothing reads the universe. The spectator map (`web/app.js`) may show everything, but only under the spectator rules in `public-web-v1.md` section 7.

| Layer | Data (observation fields named in `cockpit-ai-seat-v1.md`; C1 confirms each) | Slice |
|---|---|---|
| Known sectors and warps | `known_sectors`, `known_warps`, `adjacent` | exists (`web/redesign.js` `map()`) |
| One-way warps | warp lists (one-way lane class) | exists |
| Port class badges (BBS, SBB ...; StarDock Class 9 label per CV-e) | `known_ports` | C1 |
| Own fighters and mines | sector `fighter_group`, `mines` for owned groups | C1 |
| Planets: own / other / unknown owner | `owned_planets`, sector `planets` (owner hidden without scanner under fog) | C1 |
| Avoid list | Computer O data | C1 |
| Plotted course and route cost | `plot_course` result | C1 |
| FedSpace, StarDock, Terra markers | sector `is_fedspace`, ids 1 / StarDock | C1 |
| Last-seen age shading | `known_ports[*].last_seen_day` | C3 |
| Hazards: NavHaz, known enemy fighters, beacons | `nav_hazard_pct`, `fighter_group`, `beacon` | C3 |
| Ether probe path | probe result events | C3 |
| Corp-mates' last known sectors | `corp` block (if the original shows it; check EIS CorporateMenu) | C3 |

UI: a layer menu with toggles saved in `localStorage`; a legend; keyboard toggles; passes at 390, 1366 and 1920 px. Spectator map gets the same toggles in C3.

### 5.5 Live test plan "Addendum B" (Commander, on Ben's TWGS, same method as Addendum A)

1. Ship-vs-ship exchange: attacker in a Missile Frigate (odds 1.3) and in a Merchant Cruiser (1.0) uses 100 fighters against a victim with known fighters and shields. Record losses on both sides to pin CMB-c.
2. Toll: defensive fighters set to toll; record the price per fighter (S2 says 5 credits).
3. Pods per day: die three times in one day; record when the third death locks you out.
4. Corp-mate fighters: two corp members leave fighters in one sector; record whether the second is challenged.
5. Player-kill exp: vary the fighters the victim loses; record the experience (CMB-i formula check).

Results go into RULINGS as Addendum B before A2 starts. Test passwords stay private, as in Addendum A housekeeping.

## 6. Four tracks: file ownership

General rules:
- One worktree per track (`wt_trackA` .. `wt_trackD`, never `wt_wire`).
- Branch from the current tip after NOTE 59 lands.
- Commander reviews and merges.
- A track that needs a change in another track's file files a queue row for that track instead of editing.

### Track A: combat, hazards, Ferrengi, death

| Kind | Files |
|---|---|
| Engine modules | `src/tw2k/engine/combat.py`, `ferrengi.py`, `alien.py`, `fed.py`, `hardware.py`, `scanners.py`, `ship_exit.py`, `capture.py`, `tow.py`, `fleet.py`, `ship_transwarp.py`, `rob_steal.py` |
| `engine/runner.py` functions | `_handle_warp`, `_handle_scan`, `_handle_deploy_fighters`, `_handle_deploy_mines`, `_handle_atomic_detonation`, `_handle_attack`, `_handle_port_attack`, `_handle_photon_missile`, `_handle_query_limpets`, `_handle_probe`, `_handle_deploy_atomic`, `_handle_recall_deployed`, `_handle_surrender`, `_handle_retreat`, `_handle_pay_toll` |
| Bots | `src/tw2k/agents/war_brain.py`, `war_report.py` |
| Scripts | `scripts/war_bots_scenario_lab.py`, `capture_scenario_lab.py`, `alien_traders_scenario_lab.py` |
| Tests | `tests/test_ship_combat_*.py`, `test_combat_*.py`, `test_ferrengi_*.py`, `test_photon_vs_planet_v1.py`, new `test_*hazard*`, `test_*pod*` |

### Track B: planets, citadels, colonists, economy, universe, code bots

| Kind | Files |
|---|---|
| Engine modules | `src/tw2k/engine/planets.py`, `planet_trade.py`, `economy.py`, `port_build.py`, `class0.py`, `universe.py`, `bank.py`, `victory.py`, `corp.py`, `corpships.py`, `tavern.py`, `cineplex.py`, `tricron.py` |
| `engine/runner.py` functions | `_handle_trade`, `_handle_wait`, `_handle_land_planet`, `_handle_liftoff`, `_handle_load_planet_cargo`, `_handle_dump_planet_cargo`, `_handle_assign_colonists`, `_handle_build_citadel`, `_handle_deploy_genesis`, `_handle_claim_planet`, `_handle_buy_ship`, `_handle_buy_equip`, `_handle_corp_*`, `_handle_hail`, `_handle_radio`, `_handle_broadcast`, `_handle_plot_course`, `_handle_avoid`, alliance handlers, `_handle_deposit_treasury`, `_handle_withdraw_treasury`, `_handle_set_military_reaction`, `_handle_set_quasar_*`, `_handle_planet_*`, `_handle_deposit_planet_defense`, `_handle_withdraw_planet_defense`, day tick |
| Bots | `src/tw2k/agents/seat_brain.py`, `heuristic.py`, `bank_brain.py`, `corp_brain.py`, `deploy_brain.py`, `tavern_brain.py`, `route_macro.py`, `stall.py` |
| Scripts | `scripts/seat_brain_v2.py`, `seat_brain_acceptance.py`, `planetary_*.py`, `planet_invariants_fuzz.py`, `port_*`, `bank_tax_scenario_lab.py`, `bots_bank_scenario_lab.py`, `corp_*_lab.py`, `v311_soak.py`, `long_game_pace_*.py`, `economy_scale_report.py` |
| Tests | `tests/test_planet_*.py`, `test_citadel_*.py`, `test_seat_bot_*.py`, `test_seat_brain_*.py`, `test_port_*.py`, `test_bots_*.py`, `test_corp_*.py` |

### Track C: cockpit, rules docs, map, profile steward

| Kind | Files |
|---|---|
| Cockpit and spectator web | `web/redesign.js`, `redesign.css`, `redesign.html`, `web/app.js`, `index.html`, `style.css` |
| Server read surface | `src/tw2k/engine/observation.py`, `src/tw2k/server/harness.py`, `reference.py`, `cockpit_fields.py`, `src/tw2k/agents/rules_text.py` |
| Until public-web starts | `src/tw2k/server/app.py`, `src/tw2k/cli.py`, `src/tw2k/server/runner.py` |
| Profile steward | `constants.py` V311 block (`v311_profile`, `V311_PROFILE_HELPERS`), `tests/test_v311_rulings_v1.py`, `tests/test_tw2002_live_profile_v1.py`, `docs/plans/v311-profile-v1.md` |
| Tests | `tests/test_cockpit_*.py` (not `test_cockpit_ai_seat_*`), `test_spectator_*.py`, `test_dashboard_*.py`, new `/bot` byte-hash test |
| Never edits | `web/bot.html`, `bot.js`, `bot.css`, `bot-parity.js`, `bot2.*` |

### Track D: AI cockpit player, then voice

| Kind | Files |
|---|---|
| AI seat | `src/tw2k/agents/cockpit_seat.py`, new `agents/cockpit_seat_*.py`, `agents/llm.py`, `prompts.py`, `llm_usage.py`, `pathb_client.py` |
| Scripts | `scripts/cockpit_seat_run10.py`, `run_cockpit_seat.py`, new `scripts/cockpit_seat_*.py` |
| Voice | new `src/tw2k/voice/`, new `web/voice.js`, `web/voice.css`, `web/play.js` (voice reference), `src/tw2k/copilot/standing_orders.py`, `safety.py` |
| Tests and docs | `tests/test_cockpit_ai_seat_*.py`, `test_voice_*.py`, `test_copilot_*.py`, `docs/plans/cockpit-ai-seat-*.md`, `docs/playtests/cockpit-ai-seat-*/` |
| Rule | Calls harness routes only; asks C for any new route or mount point |

### Shared hot files

| File | Rule |
|---|---|
| `src/tw2k/engine/constants.py` | A and B append new flags at the end of the file, each in its own block. C owns the V311 block. Rebase right before DELIVERED. |
| `src/tw2k/engine/runner.py` (engine) | Function ownership as listed. New handlers are appended by their owner. |
| `src/tw2k/engine/legality.py` | Same split by action kind: A for combat and hazard kinds, B for the rest. |
| `src/tw2k/engine/models.py`, `engine/actions.py` | Append-only. New fields go at the end of their model, new `EventKind`/`ActionKind` values at the end of the enum, each with a slice tag. Second to deliver rebases. |
| `tests/test_v311_rulings_v1.py`, `tests/test_tw2002_live_profile_v1.py` | C only. A/B file an intake row. |
| Public-web stream P (when it starts) | Takes over `server/app.py`, `server/runner.py`, `cli.py`, `server/seat_links.py`, `spectator_gate.py`, `harness_tokens.py`; owns new `src/tw2k/public/`, `deploy/`, `tests/test_public_*.py`. C keeps `harness.py`. |

## 7. Merged recommended order (NOTE-sized slices)

NOTE numbers are suggestions. Each slice has 5-8 items. Every slice has the standing pass bar, plus its own:
- all tests green;
- legacy pins unchanged;
- new behaviour behind a legacy-default flag;
- v3.11 10-day short-day soak with rejected 0 and exceptions 0;
- for cockpit slices: 390 / 1366 / 1920 px screenshots and the `/bot` byte-hash test.

### Wave 0 (now)

- NOTE 59 (in progress): kill cash and pod cash in the profile. Everyone rebases after it.
- Commander: CV-a with profile off and on; v3.11 soak rerun; Addendum B live tests (5.5).

### Wave 1 (four tracks in parallel)

**NOTE 60, A1 combat-fidelity-a1 (revised)**
1. Test only: after a player kill under the profile the killer gets 0, the victim's cash is gone, and the pod holds 25 credits (Addendum A T1/T6); holds salvage stays.
2. Toll at 5 credits per fighter, new flag (FIG-c; S2).
3. Player-kill exp and alignment using the Addendum A screens as test vectors (+1 attack, +20 defeat, -50 alignment, victim -10% exp), new flag (CMB-i).
4. Armid mines: half detonate on entry, damage per mine a constant, new flag (FIG-e).
5. Photon next door shuts down that sector's mines, fighters and quasar for one wave, new flag (SD-o).
6. Three Ferrengi hulls from the Bible/FERRSPEC table, new flag (FER-a).
7. `war_brain.py` reads the new flags (bots use toll and photon correctly when they are on).
Pass: each flag's on-test cites its source line; the profile does not include any of them until Ben rules.

**NOTE 61, B1 planets-and-bots-b1**
1. Code-bot citadel step under the profile (class goods, build days), in `seat_brain.py` and `heuristic.py` behind a new bots flag.
2. Genesis gives +25 exp and +10 alignment, new flag (PLN-m).
3. Treasury cap 999,999,999,999,999, new flag (PLN-r).
4. Class 0 hold price B*H + 20*H*(H-1)/2, new flag (TRD-i).
5. Big Bang densities: ports 40%, planets up to 20%, no decorative Fed ports in 2-10, new flag (MOV-h, MOV-i).
6. Test only: multi-day citadel climb L1 to L6 with quasar firing under the profile with a short day (CIT-l).
7. Note for Ben in the slice doc: class M L1 needs 1,000,000 colonists vs the 191,000 start planet.
Pass: with the bots flag on, a 10-day short-day soak shows at least one bot citadel started.

**NOTE 62, C1 cockpit-rules-map-c1**
1. "Rules in force" in Z Rules and Help and `GET /harness/v1/{seat}/reference`: profile on or off, each switch and the numbers it uses (DOC-b).
2. Escape quotes in `esc()` in `web/redesign.js` and `web/app.js`; audit every name and message site.
3. Map layers C1 set (5.4): port badges, own fighters and mines, planets, avoid list, plotted course, FedSpace/StarDock/Terra markers, legend and toggles (MAP-b part 1).
4. StarDock label Class 9 under the profile and port screen columns vs the original (CV-d, CV-e).
5. Military reaction % on the planet card and in the result line (CIT-j).
6. `tw2k serve --profile v311 --day-seconds N`, and switch values written to `meta.json` (R-3 start).
7. `/bot` byte-hash test.
Pass: with `--profile v311`, the reference page lists 62 switches on; with no flag, a served game is legacy and the digests match.

**NOTE 63, D1 ai-seat-v311-d1**
1. Cockpit seat runs under the profile with a short day; the brain reads prices and costs from the reference page (D-1).
2. Brain interface split: heuristic brain and an LLM brain behind one interface (D-2).
3. Scenario: trade loop on a scripted seed.
4. Scenario: Terra colonists to a Genesis planet under the profile.
5. 10-day profile run report with regenerated gaps (`docs/playtests/cockpit-ai-seat-v4/`).
6. 3-day LLM-brain run with cost per day.
7. Request-log check: the seat touches only its own five routes.
Pass: 10-day profile run refused 0; LLM run refused under 1%.

### Wave 2

**A2 combat-fidelity-a2** (after Addendum B):
1. Ship odds in the ship-vs-ship exchange (CMB-c).
2. Zyrain FedSpace response (CMB-l).
3. Tholian Sentinel / Interdictor rules (CMB-m).
4. Ferrengi grudges, banding and pace (FER-c, FER-d).
5. Death delay setting (CMB-n).
6. Two pods per day, third death out until midnight (CMB-g, Ben).

**B2 universe-and-days-b2**:
1. One-way share about 3% under `UNIVERSE_TOPOLOGY_MODE` (MOV-f).
2. Bot dead-end escape (DAY-g).
3. Bust record clearing (TRD-k).
4. Nightly Extern jobs: Class 0 price change, tows, timeouts (DAY-b).
5. Corp planet disband rule as a switch (PLN-q).
6. Max course length 45 (MOV-g).
7. Limpet removal service (SD-j).

Pass: a 30-day short-day soak with topology on shows no seat trapped for more than one day.

**C2 cockpit-c2**:
1. Cockpit side of every A1/B1 flag (result lines, cards).
2. Profile intake for flags Ben ruled on.
3. Owner notices on screen (FIG-j).
4. Corp menu assets and positions (CRP-f).
5. V-screen counts (DAY-c).
6. Rank table and experience scoring on screen (SCR-b).
7. Per-seat orders route `POST /harness/v1/{seat}/orders` with an owner token for `llm` seats (for D).

**D2 ai-seat-d2**:
1. AI seat vs N3 and heuristic bots on the profile (D-4).
2. Citadel scenario.
3. Defend/attack scenario.
4. Ferrengi scenario.
5. Explain line per action (D-5).
6. Seat reads owner orders.
7. 1,000-colonist haul driven by the seat (LH-a).

### Wave 3

**A3**:
1. Ether probe shoot-down and owner notice (MOV-c).
2. Bought density and holo scanners (SD-p).
3. Ferrengi rewards and Ferrengal quasar (FER-e, FER-h).
4. Corporate fighters and mines (FIG-l).
5. Port attack beyond class 6 if a source is found (TRD-n).

**B3**:
1. Per-ship item caps from the RULINGS s4 table (SD-e).
2. Other alignment sources (SCR-e).
3. Atomic detonator as the planet killer (SD-l).
4. Underground as the original mafia (SD-m).
5. Economy scale check against the roster prices (TRD-h, Ben).

**C3**:
1. Map layers part 2: age shading, hazards, probe paths, corp-mates; spectator map toggles.
2. Original-game sections in the reference: citadel tables, combat odds, flee rule, haggle bands, exp and alignment formulas, each citing its S-file (DOC-c).
3. Computer menu reports: ship catalog, daily log, planet list, planetary specs, trader ranks, mail (CV-c).
4. 390 px fixes (CV-f).
5. Mount point for `web/voice.js` in `redesign.html`.

**D3 voice-v0-v1**:
1. Orders panel (V-0).
2. Quick commands.
3. Confirm on risky verbs.
4. Browser push-to-talk (V-1).
5. Spoken readouts.
6. Vocabulary fixture list (V-2).

Public-web P0 and P1 start in a fifth worktree (stream P), per `public-web-v1.md` section 13.

### Wave 4

- R-4: Ben decides the constant flip; C re-pins with both pin sets kept.
- D4: one voiced game day (V-3, VOX-d).
- R-5 clean-up of no-op switches.
- Public-web P2-P3.

### Why this order

1. NOTE 59 and the two CV-a runs come first. They tell every track what is broken under the profile before anyone builds on it.
2. Source-backed rules (Addendum A, S1, S2) go before UNVERIFIED ones (ship odds), and a live test goes before code.
3. C1 puts "Rules in force" and the escape fix early. Players, the AI seat and the public site all depend on them, and they are cheap.
4. D builds on what NOTEs 55-56 delivered instead of rebuilding it, and reaches voice only after the seat can explain itself and take orders.
5. Public web waits until the profile is visible, saved and safe to show strangers.

## 8. Decisions for Ben

1. Server-level v3.11 default now, constant flip later (R-3 before R-4): OK?
2. Class M ratios vs the 191,000-colonist start planet (NOTE 41 item 10).
3. Two pods per day (CMB-g) into the profile after A2?
4. `EXP_SCORE_MODE` (experience decides the winner) confirmed for the profile?
5. Addendum B live tests on the TWGS box: OK to run?
6. Default day length for v3.11 games outside tests (24 h original, or shorter)?
