# COMMANDER_NEXT - competitive seat bot (fogged observation)

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `seat-bot-competitive`
- **updated_at:** `2026-09-25T22:45:00-07:00`
- **updated_by:** `Fable`
- **blocker:** none

## Active task
**id:** `seat-bot-competitive-s6`
**title:** SeatBrain mid-game pivots from rivals / events / orphans
**instructions:**
(idle - S6 delivered, waiting on Commander review)

## Delivered (S6)
- **Commit:** `e8c2f18`. Pushed to `feature/seat-bot-competitive` (continues PR #1: https://github.com/EarlTheDuke/TW2002-Human-assist/pull/1) and `feature/grok-bot-harness`. Built on the branch only; nothing was patched on the live `:8031` match.
- **Files:**
  - `src/tw2k/agents/seat_brain.py`: S6 logic (below).
  - `src/tw2k/engine/observation.py`: one-line observation fix. `recent_failures` grouped every rejected action as "unknown rejected", because the scheduler stores the verb under `payload.action.kind`. It now reads that, so seats see e.g. "land_planet rejected ×2". This is fog-safe: `agent_error` is actor-only.
  - `tests/test_seat_bot_s6.py` (new, 16 tests).
  - `docs/plans/2026-09-25-seat-bot-s6-rivals-events.md` (committed with its implementation).
- **Tests:** 16 new; all seat-bot tests 53 passed (S1 9, S2 11, S3 8, S4 9, S6 16); full suite **597 passed** (was 581); ruff clean.

### What the brain now does
1. **Rival pressure.** It reads `rivals[].net_worth` (a rival counts as ahead at ≥1.15× our net worth and ≥ +10k) and empire events it actually witnessed from other seats (genesis / citadel / planet-claim, counted only while we have no world yet). Under pressure it:
   - starts a buildable citadel on another world using working capital;
   - autopilots to StarDock with genesis money at a lower bar;
   - wants orphan inheritance even if genesis is affordable;
   - records "trailing P2 (NW)" in `goal_medium`.

   Legality and credits still gate everything (tested).
2. **Failure replanning.** New `agent_error` / `warp_blocked` / `trade_failed` events for **this seat** since the last decision are attributed to the brain's own last action:
   - That exact action is banned for 12 decisions. Facts-based bans cover a blocked warp target and a failed commodity/side.
   - The same verb failing twice in a day shelves it until the next day.
   - The engine's `recent_failures` (count ≥ 2) feeds the same bans.
   - Old events are never recounted (the event cursor is persisted in the scratchpad), and other seats' failures are ignored.
   - Banned options fall through to the next choice. When landed, lift-off stays the fallback. Exploration skips banned warp targets.
3. **Orphans.** `claim_planet` is used only when landed on a planet listed in `orphaned_planets` **and** `claim_planet` is legal. It never claims an unlisted planet, even if the verb reports legal. The brain lands on or plots to a listed orphan (≤8 known hops, not contested) when it has no world and genesis is unaffordable or it is trailing, or when the orphan carries a citadel. An inherited world with a citadel or ≥1,000 colonists becomes a work site and home; empty neutral claims still don't (the Kimi3 planet-20 trap stays closed).

### Evidence behind one design choice
I first had pressure buy genesis before the CargoTran and fund a second genesis from working capital. Offline 6-day sweeps against a far richer rival showed that lost 5–140k net worth on every seed tried; ablation pinned it on the hull deferral. Both were removed. Pressure now never trades the hull or the citadel reserve away, and there is a test pinning this with that reason. With the final code, the rich-rival runs match the calm runs on all 5 seeds, with 0 engine rejections. Caveat: the sim rival is idle, so these sweeps measure absolute economy, not racing.

## How to run
```powershell
$env:PYTHONUTF8="1"
python -m pytest tests/test_seat_bot_s6.py -q            # 16 passed
python -m pytest tests/test_seat_bot_s1.py tests/test_seat_bot_s2.py tests/test_seat_bot_s3.py tests/test_seat_bot_s4.py tests/test_seat_bot_s6.py -q   # 53 passed
python scripts/seat_brain_acceptance.py synthetic        # S4 storyboards still PASS
```
S6 test groups:
- **Rival pressure:** a citadel build pulled forward, credits/legality respected, the hull is never sacrificed, and a witnessed rival genesis counts as pressure while our own doesn't. The StarDock autopilot threshold was tested for poor, rich, pressured and broke seats.
- **Failures:** no identical retry, old events not recounted, other seats ignored, the verb shelved for the day and reset next day, a blocked warp target avoided even in exploration, engine `recent_failures` honoured, and the engine groups rejections by verb.
- **Orphans:** claims only a listed orphan while landed and legal; not unlisted; not illegal. It lands on an orphan only when that beats genesis, and an offline engine run goes land → claim → inherited world becomes home.

## ACK (prior)
- S1–S2 @ `557b780`; S3 @ `205bb10`; S4 @ `7a9813d`

## Open Cursor options
1. ~~S1~~ ACK
2. ~~S2~~ ACK
3. ~~S3~~ ACK
4. ~~S4~~ ACK
5. S5 docs (optional / may still be pending)
6. ~~S6 rivals/events/orphans pivots~~ (`e8c2f18`, awaiting review)
