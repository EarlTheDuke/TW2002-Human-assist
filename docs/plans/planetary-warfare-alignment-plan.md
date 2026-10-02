# Planetary warfare alignment plan (draft v1, Commander, 2026-10-01 PT)

Source: `planetary-warfare-comparison.md` (original TW2002 vs our engine). Ben's order (2026-10-01 20:50 PT): make our planetary warfare like the original, work through the weekend, and test the mechanics with creative games. Ben is mostly AFK, so Commander decides defaults below; Ben can veto any of them.

## Principles
1. One small slice at a time, each with tests, ruff, whole-diff read, and a live check. Cur's full suite is the gate.
2. Rules changes land behind named constants in `constants.py` so balance can be tuned without code edits.
3. Fog stays safe: a player sees defenses of a planet only the way the original allows (owner and corp see everything; others see only what a scan shows).
4. Bots must keep working: every new action gets a `legal_actions` entry with a reason, a prompt line, and an observation field before it is switched on.
5. Match length is 30 days by default, so the original's 34 to 52 day citadel build times are scaled down by a constant (default x0.25) rather than copied.

## Defaults Commander is taking (Ben can veto)
- Keep credits plus colonists as the citadel cost for now. Class-specific commodity costs come last (P11), behind a switch.
- Use the MBBS atmospheric quasar formula (damage = fuel x pct x 2, fuel used = fuel x pct), because both sources agree on it. The TWGS value is unresolved.
- Offensive wave size 1.25 x the attacker's ship capacity, odds 2:1 offensive and 3:1 defensive, shields at 20:1 and 10 ship shields to 1 planet shield, as the report states.
- Planet fighter cap 1,000,000, as in the original.
- Level order follows the original: L1 treasury, L2 combat control, L3 quasar, L4 planet transwarp, L5 planet shields, L6 interdictor.

## Roadmap (each item is one slice unless noted)
Phase A, what is already in flight
- A0 `siege-path-tests-v1`: done, ACK'd (ed5c119). Pins today's behavior.
- A1 `spectator-siege-planet-patch-v1`: spectator planet table updates on a siege capture.
- A2 `siege-gap-fixes-v1`: a repelled landing charges turns; a capture also lowers `citadel_target`.

Phase B, give planets real defenses
- B1 `planet-defense-stocking-v1`: `deposit_planet_defense` and `withdraw_planet_defense` (landed, owner or corp, 1 turn). 10 ship shields become 1 planet shield. Fighter cap constant. Action, legal_actions, prompt and observation entries. Needs no fog change.
- B2 `planet-treasury-actions-v1`: `deposit_treasury` and `withdraw_treasury` at L1 and up, optional daily interest constant (default 2%). Show treasury in the owner's planet rows.
- B3 `citadel-level-table-v1`: one level to perk table in `constants.py`, used by prompts, web CITADEL_TIERS, DESIGN.md and the planets comment. Moves shields to L5 and combat control to L2. Removes or rescales the free 1000xL fighter and 250xL shield gift once B1 exists (decision point; see risks).
- B4 `planet-fighter-production-v1`: a fraction of daily colonist output makes fighters, using the per-class ratios from the report. Respects the cap.

Phase C, a siege that matches the original
- C1 `siege-shield-gate-v1`: shields are fought first at the 20:1 rule; planet fighters only fight once shields are down. A planet with fighters 0 and shields above 0 can no longer be taken free.
- C2 `siege-odds-and-reaction-v1`: offensive wave 1.25x capacity at 2:1, remainder defends at 3:1, plus a military reaction percentage setting on the planet (new action `set_military_reaction`).
- C3 `siege-sector-phase-v1`: sector mines and sector fighters fire before the landing, as in the original order of events.
- C4 `siege-events-and-cockpit-v1`: events carry the phase label; the spectator volley log and cockpit siege preview show them. Preview shows planet fighters, shields, own forces, and the rounds note.

Phase D, the late-game weapons
- D1 `quasar-sector-shot-v1`: planet setting `quasar_sector_pct`; a hostile ship entering the sector takes fuel x pct / 3 damage and the planet burns fuel x pct. `QUASAR_FIRE` event. Photon missile effect comes with D3.
- D2 `quasar-atmospheric-shot-v1`: the second cannon fires during a landing (before shields and again after they fall).
- D3 `photon-vs-planet-v1`: a photon disables the quasar when the planet is below L5 or has under 200 shields, and the other listed defenses per the original.
- D4 `interdictor-v1`: L6, blocks leaving a sector, 500 fuel per attempt, quasar re-fires.
- D5 `planet-transwarp-and-transporter-v1`: L4 planet jump (400 fuel per sector, needs a fighter lock) and the planetary transporter (50,000 first hop, 25,000 each extra, 10 fuel per sector). Biggest rules slice; split further if needed.

Phase E, polish and long tail
- E1 `class-citadel-tables-v1`: per-class commodity costs and times, scaled by the build-time constant, behind a switch.
- E2 `planet-destruction-v1`: atomic path, colonists must be killed first.
- E3 `corp-planet-edge-cases-v1`: leave and disband rules, ally siege.
- E4 `planet-scanner-fog-v1`: non-owners see defenses only through a scan; decide if shielded planets hide owner and fighters.

## Test-game track (runs in parallel with every slice)
The goal is to prove each mechanic works in a real game, not only in unit tests.
1. Scenario lab (headless, no paid calls): a script builds a seeded universe, places planets with set defenses, then runs scripted attackers. It prints a table of outcomes over many seeds, for example win rate against fighters x shields grids, to check the odds feel like the original (2:1, 3:1, 20:1). Run after C1, C2, D1.
2. Scripted bot matches on scratch port :8036: a short match with scripted bots whose only plan is the new mechanic (stock a planet, siege a planet, moth a quasar). Check the spectator view shows every event. Never on :8031, :8032 or :8035.
3. Mixed LLM-bot smoke match on :8036 only when a phase finishes (B, C, D), to see whether the bots understand the new actions from the prompt alone. Uses existing free or already-approved bots only; no new paid calls.
4. Regression guard: each phase ends with the full suite plus a recorded outcome table kept in `docs/playtests/planetary-warfare/`.
5. Findings from every test game become either a fix slice or a note in this file.

## Risks and decision points
- Removing the free citadel garrison (B3) would make existing defenders much weaker at once. Plan: keep the gift until B1 and B4 exist, then reduce it by a constant in a separate tuning slice.
- Bots may not learn the new actions. Every slice must add a prompt line and be checked in a test game before the next phase.
- The TWGS atmospheric factor and the meaning of "20:1" for shields are unresolved. Defaults are in the section above; keep them constants.
- Balance can drift. The scenario lab outcome tables are the check, and a tuning slice follows each phase.