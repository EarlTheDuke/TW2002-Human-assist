# Planetary warfare plan review (Cursor, 2026-10-01)

Read: `planetary-warfare-alignment-plan.md`, `planetary-warfare-comparison.md`, and the handlers they cite. No rules were changed. A1 in the roadmap is already finished as a stop, not as a table update: `spectator-siege-planet-patch-v1` @ `501fbe1` ACK'd. The public landing event does not carry corp or citadel, so the client was not patched.

## 1. Each slice

Sizes are Cur's: XS under an hour, S one sitting, M a day, L more than a day.

### A2 `siege-gap-fixes-v1` (XS, do this first)

In `_handle_land_planet`, on a capture set `citadel_target = citadel_level` and `citadel_complete_day = None` after the level drop. On a repel, keep `ok=False` only if turns must stay uncharged; to charge turns, return `ok=True` with a distinct result flag, or teach `apply_action` to honor `turns_spent` when the error is `planetary defenses repelled landing`. Prefer the second so a failed landing stays `ok=False` for callers that treat `ok` as "you landed". Files: `src/tw2k/engine/runner.py`, `tests/test_siege_path_v1.py` (the two `KNOWN GAP` asserts flip). No new fields.

### A1 follow-up, not the client patch (XS)

Add `EventKind.LAND_PLANET` and planet `COMBAT` to the `planet_events` set in `MatchRunner._state_patch_for`. The patch already copies `owner_id`, `corp_ticker`, and `citadel_level` from the live planet. No new event field. Files: `src/tw2k/server/runner.py`, `tests/test_spectator_siege_planet_patch_v1.py`, `tests/test_phase_abc.py` (`TestPhaseKPlanetPatch`). The roadmap line that says the spectator table "updates on a siege capture" is not done.

### B1 `planet-defense-stocking-v1` (S)

New actions `deposit_planet_defense` and `withdraw_planet_defense`. Args: `planet_id`, `kind` (`fighters` or `shields`), `qty`. Preconditions: landed, owner or same `corp_ticker`, 1 turn (`TURN_COST` entries). Fighters move 1:1, cap `PLANET_FIGHTER_CAP = 1_000_000`. Shields move 10 ship shields to 1 planet shield, both ways, integer division. Gate with `PLANET_DEFENSE_MIN_LEVEL` defaulting to 2, not a hardcoded "L2 means combat control", so B3 can rename levels without a second rules change. Events: `PLANET_DEFENSE_TRANSFER` with `planet_id`, `kind`, `qty`, `direction`. `legal_actions`, one prompt line, and the existing sector planet brief already shows fighters and shields. Files: `actions.py`, `runner.py`, `legality.py`, `constants.py`, `observation.py` `EVENT_FACTS`, `prompts.py`, `web/bot.js` verb group, one engine test.

### B2 `planet-treasury-actions-v1` (S)

`deposit_treasury` and `withdraw_treasury`, args `planet_id`, `amount`, landed, owner or corp, citadel level >= 1, 1 turn. Credits move between the player and `planet.treasury`. Interest: on day tick, if level >= 1, `treasury += treasury * PLANET_TREASURY_INTEREST_PCT // 100` with the constant default 2, capped by `PLANET_TREASURY_CAP`. Event `PLANET_TREASURY` is optional; a day-tick summary is enough for interest. Show `treasury` on the cockpit owned-planet rows (the spectator block already has it). Files: `actions.py`, `runner.py`, `planets.py` (`_advance_planets` or the day tick), `constants.py`, `legality.py`, `prompts.py`, `web/bot.js`, one engine test.

### B3 `citadel-level-table-v1` (S, split)

The prompt in `prompts.py` already says L2 combat control, L3 quasar, L4 transwarp, L5 shields, L6 bunker. `web/app.js` `CITADEL_TIERS` says something else (L2 quasar, L5 interdictor, L4 genesis). `planets.py` `_complete_citadels` comments "L2 = Quasar" and, at level >= 2, raises fighters to `1000 * level` and shields to `250 * level`.

B3a, labels only: one tuple list in `constants.py` (`CITADEL_PERK`: level, name, one-line perk). Prompts, `CITADEL_TIERS`, and the planets.py comment read that list. No combat change.

B3b, later, after B1 and B4: stop applying the free garrison, behind `CITADEL_GIFT_FIGHTERS_PER_LEVEL` and `CITADEL_GIFT_SHIELDS_PER_LEVEL` defaulting to today's 1000 and 250, then a tuning slice sets them to 0. Do not zero them in B3a.

### B4 `planet-fighter-production-v1` (S)

On day tick, after colonist production, add fighters by class. New constant `PLANET_FIGHTER_FACTOR` keyed by `PlanetClass`, values taken from the report's per-class ratios once those ratios are copied into the constant (the comparison points at section 1.1; the factor numbers need to be written down in `constants.py`, not left in prose). Respect `PLANET_FIGHTER_CAP`. No new action. Files: `planets.py`, `constants.py`, one day-tick test. Ships nothing until the factors are numeric.

### C1 `siege-shield-gate-v1` (S)

Inside the hostile branch of `_handle_land_planet`, if `planet.shields > 0`, the planet's volley is shield soak at `PLANET_SHIELD_ODDS = 20` (attacker damage must exceed shields * 20 before a shield is lost; the exact arithmetic is a named constant because the report says "20:1" is unclear). Planet fighters do not fire while shields remain. Fighters 0 and shields > 0 is no longer a free capture. Keep the 3-round cap for this slice. `rounds[]` gains `phase: "shields"` or `"fighters"`. Update `test_siege_path_v1.py` case 5. Files: `runner.py`, `constants.py`, `combat.py` if soak moves next to `_apply_volley`, the siege tests.

### C2 `siege-odds-and-reaction-v1` (M)

Replace the symmetric `U(0.8, 1.2)` exchange for planet fights. Offensive wave size `int(1.25 * (fighter_cap + shield_cap))` of that ship class, odds `PLANET_OFFENSE_ODDS = 2` and `PLANET_DEFENSE_ODDS = 3`. New planet field `military_reaction_pct` (0-100, default 0). New action `set_military_reaction` (`planet_id`, `pct`), landed, owner or corp, 0 or 1 turn. Reaction fighters attack at 2:1 only after shields are down; the rest defend at 3:1. Files: `models.py` Planet, `actions.py`, `runner.py`, `legality.py`, `constants.py`, `prompts.py`, observation planet brief, siege tests. This retires the 3-round dice path for planets. Ship-vs-ship combat stays as it is.

### C3 `siege-sector-phase-v1` (M)

Before the landing fight, resolve sector armids and sector fighters that already exist on the sector. Do not invent new mine math in this slice: call the same detonation the warp path uses, in the order the report gives (mines, then sector fighters, then the landing). A dead ship returns the existing destroy path and does not capture. Files: `runner.py` (`_handle_land_planet` and whatever `_handle_warp` uses for mines), mine tests, siege tests. Quasar is not in this slice.

### C4 `siege-events-and-cockpit-v1` (S, after C1)

Spectator volley log labels `rounds[].phase`. Cockpit `land_planet` form, when `contested`, shows planet fighters, shields, own fighters, own shields, and the round note. Those numbers are already on the sector brief. No fog change. Files: `web/app.js`, `web/bot.js`, one cockpit test. Map layout numbers stay put.

### D1 `quasar-sector-shot-v1` (M)

Planet fields `quasar_sector_pct` (0-100, default 0). Action `set_quasar_sector` once, or fold settings into one `set_planet_defense` later if the settings list grows. On a hostile warp into the sector, if citadel >= 3 and fuel stockpile > 0: damage = fuel * pct / 3, fuel burned = fuel * pct. Event `QUASAR_FIRE` with `planet_id`, `mode: "sector"`, `damage`, `fuel_used`. Lowest planet id fires first; stop if the ship is dead. Files: Planet model, `runner.py` warp path, `constants.py` (`QUASAR_MIN_LEVEL = 3`), `actions.py`, `legality.py`, `prompts.py`, `EVENT_FACTS`, one warp test.

### D2 `quasar-atmospheric-shot-v1` (M)

Field `quasar_atm_pct`. Formula constant `QUASAR_ATM_FACTOR` default 2 (MBBS: damage = fuel * pct * factor, fuel used = fuel * pct). Fire once before the shield gate and once after shields hit 0, inside `_handle_land_planet`. Same `QUASAR_FIRE` event with `mode: "atmosphere"`. Files: Planet, `runner.py`, `constants.py`, siege tests.

### D3 `photon-vs-planet-v1` (M)

When a photon hits and the planet is below L5 or has under `QUASAR_PHOTON_SHIELD_MIN = 200` shields, skip sector quasar, atmospheric quasar, and offensive planet fighters for that approach. Shields and defensive fighters still apply. Needs a flag on the ship or the sector for "quasar damped this tick", not a silent combat change. Files: photon handler in `runner.py`, `constants.py`, siege or photon tests. Do not build this before D1.

### D4 `interdictor-v1` (M)

At citadel >= 6, a hostile warp out of the sector fails while planet fuel >= `INTERDICTOR_FUEL = 500`. Burn 500 fuel, fire the sector quasar again, leave the ship in the sector. Below 500 fuel the warp succeeds. Event `INTERDICT`. Files: warp handler, `constants.py`, one warp test.

### D5 split (L if kept together)

D5a `planet-transwarp-v1` (M): action `planet_transwarp` at level >= 4, dest sector, 400 fuel per sector of distance, requires a fighter of the owner already in the dest (`PLANET_TRANSWARP_FUEL_PER_SECTOR`). Moves `planet.sector_id` and the sector `planet_ids` lists. Event `PLANET_TRANSWARP`.

D5b `planet-transporter-v1` (M): action `planet_transport` at level >= 1 and a bought flag `has_transporter`. Costs 50_000 credits for the first hop and 25_000 per extra hop from the player, 10 planet fuel per sector, 1 turn, dest must contain an owner fighter. Moves the player. Event `PLANET_TRANSPORT`.

### E1 `class-citadel-tables-v1` (M, last)

Behind `CITADEL_COST_MODE` default `"credits"`. `"commodities"` reads a per-class table (colonists, fuel, organics, equipment, days) scaled by `CITADEL_BUILD_TIME_SCALE` default `0.25`. `build_citadel` pays from planet stockpile plus colonists. Files: `constants.py`, `runner.py`, `legality.py`, `observation.py` `citadel_next_build`, prompt cost lines. Do not flip the default in the same slice as the table.

### E2 `planet-destruction-v1` (M)

Atomic detonation in a sector with a planet does not destroy it until colonists are 0. Add an explicit destroy path: colonist pools hit 0, then a second atomic removes the planet, emits `PLANET_DESTROYED`, and clears `sector.planet_ids`. Alignment cost stays a constant (today's atomic penalty vs the report's -50 or -1 conflict: keep today's number until Ben picks). Files: mine/atomic handler, `models.py` EventKind, one test.

### E3 `corp-planet-edge-cases-v1` (S)

On corp disband: planets in the CEO's sector keep `owner_id` of the CEO; others get `owner_id = None`, `corp_ticker = None`, and the existing orphan event. On leave: the leaver loses manage rights (already true if checks use `corp_ticker`) and does not take planets with them. Ally siege: a planet is not hostile when an active alliance contains both the owner and the attacker. Confirm the alliance helper that already exists for ship combat and use it in `_handle_land_planet`. Files: corp disband handler, `runner.py`, one corp test, one alliance landing test.

### E4 `planet-scanner-fog-v1` (S, earlier than the roadmap if test games must not leak)

`_planet_brief` is what every ship in the sector receives, including `fighters`, `shields`, `treasury`, and `stockpile` (observation.py around the sector planet list). That is a current leak, not a future one. For non-owners, drop fighters, shields, treasury, and stockpile unless the viewer owns, shares corp, or has a scan event for that planet. Shielded planets (shields > 0 and level >= 5) also hide `owner_id` from non-owners. Files: `observation.py`, fog tests. B1 does not create this leak. B1 does make the leaked numbers matter.

## 2. Order changes

- Do A2 before any new siege rule. The siege tests currently lock the two bugs in place.
- Replace roadmap A1 with the server patch-list slice above. The client cannot invent citadel level. That slice is XS and can sit right after A2.
- Split B3. Labels first, gift removal only after B1 and B4, as the roadmap risks section already says. Do not ship B3 as one slice.
- Move a thin E4 (hide treasury and stockpile from non-owners) ahead of the first scripted test game. Full scanner rules can stay late. Leaving the full brief in place teaches every bot the garrison.
- Keep C1 before C2. C2 deletes the dice exchange; doing odds first and then the shield gate double-writes the same function.
- Keep D3 after D1. A photon disable with no quasar is untestable.
- Split D5 into transwarp and transporter.
- Hold E1 until Ben accepts or vetoes the credits default. The switch can be written dark; do not turn it on in the same slice.
- Drop nothing else. C4's cockpit preview is the right place; a preview of today's 3-round dice fight would be thrown away in C2.

## 3. Conflicts

- `tests/test_siege_path_v1.py` asserts both known gaps and the free capture of a shielded planet with 0 fighters. A2 and C1 must edit those tests in the same commit as the rule.
- `tests/test_phase_abc.py` and `tests/test_history_buffer.py` know the `1000 * level` / `250 * level` gift. B3b breaks them on purpose.
- `tests/test_prompts.py` and the seat-bot tests quote citadel costs and the words "Combat Control" / "Quasar". B3a must keep the prompt's level order. Changing costs in E1 breaks the prompt strings and `citadel_next_build`.
- `web/app.js` `CITADEL_TIERS` is a second perk table. B3a is the fix. A spectator test that reads tier titles will need new expected strings.
- `test_replay_roundtrip.py` replays actions. A siege whose fighter math changes will not replay to the same owner. There is no separate golden json of sieges in `tests/` that this review found. Old saves under a live `saves/` directory were not checked.
- New event kinds need `EVENT_FACTS` rows or the seat feed drops the payload. Spectator `app.js` needs a category entry or the feed files them as system. Video clip map in `web/media-player.js` can stay on a still; do not add a clip in the same slice.
- `legal_actions` and the prompt verb list must gain each action in the same slice that enables it, or the seat bot calls an unknown kind and the cockpit has no form.
- Mode=cu and the map tops (714 at 1440x900, 927 at 1920x1080) stay put. C4's preview has to live inside the existing land form.

## 4. Not judged from the report

- The numeric per-class fighter factors in comparison section 1.1. B4 cannot start until those numbers are in `constants.py`.
- How "20:1" spends shields: one shield absorbs 20 damage, or the attacker needs 20 fighters per shield. C1 should pin one reading in the constant's comment and test that reading only.
- Whether `military_reaction_pct` default 0 matches "no reaction" or whether the original sends everyone. Default 0 is the safe reading; a test game can raise it.
- TWGS atmospheric factor. Leave it as `QUASAR_ATM_FACTOR = 2` until Ben says otherwise. Do not average the two sources.
- Per-mine damage in current TWGS, planet cap per sector, and any daily attack limit. Do not invent them in C3.
- Whether a saved match in the live saves directory contains `land_planet`. Not opened here.
- Corp leave today: the report says leave does nothing to planets. Confirm the leave handler before E3 so the slice does not "fix" a path that already clears `corp_ticker` on the player only.
- Alignment for destruction: -50 in one source, -1 in another. Keep the current atomic penalty.

## 5. Test games

### Scenario lab

`scripts/planetary_scenario_lab.py`, headless, no server, no paid call. It builds a universe with `_make_universe` or `generate_universe`, plants one planet, sets fighters, shields, fuel, citadel level, and reaction percent, sets the attacker's ship, and calls `apply_action` land. A grid such as fighters in {0, 100, 1000, 10000} and shields in {0, 10, 50, 200}, 20 seeds each because the dice path is random until C2. Prints a table: wins, repels, attacker deaths. After C2 the dice shrink and the table should move to the 2:1 and 3:1 lines; the script should print the expected wave size next to the measured win rate so a bad constant is obvious. Write the table to `docs/playtests/planetary-warfare/` only when a slice asks for a recorded run. The script stays out of pytest.

### Scripted matches on port 8036

A scratch script, not `run_cu_pilot.ps1`, binds `127.0.0.1:8036` only. It refuses to start if 8036 is taken rather than hopping to 8031, 8032, or 8035. Two external seats with fixed action lists: one deposits fighters and shields, the other lands. The script then reads `/events` and checks that `LAND_PLANET` or `PLANET_DEFENSE_TRANSFER` arrived, and that a spectator snapshot's planet owner matches. One scripted match per finished slice, not a LLM match. LLM smoke stays on 8036 and only at the end of phase B, C, and D, using bots that are already approved. No new paid call.

## What this review did not do

No change under `src/`, `web/`, or `tests/`. The two source docs and this file are the whole slice.
