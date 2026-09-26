# Competitive seat bot from fogged observation (2026-09-24)

## Goal
Build a competitive TW2K seat player that decides **only** from the per-seat observation / mailbox feed (legal_actions, cargo, credits, known map, owned_planets, events). **Hard ban:** no god-eye `/state`, no reading other seats, no spectator dumps.

Acceptance: a Path-B / seat brain can complete genesis -> land -> build_citadel -> colonist ferry using observation alone, then hold vs 3xKimi for a full short match without Commander hand-patching mid-match.

## Why (Kimi3 match evidence)
Match `docs/playtests/multibot-2026-09-23-kimi3/` (seed 230923, 3xkimi-k2.6 + Path-B P4):
- Winner P3 KimiC ~427k NW via early genesis + citadel growth
- P4 finished ~99k with 4 planets, one L1 citadel (planet 38) started too late
- Path-B burned days on hand-patched loops (4<->68 plot, 68 fuel dump, assign_colonists missing args, 14<->571, land/liftoff on claimed planet 20, StarDock<->home ferry ping-pong)

Full chronology: `docs/playtests/multibot-2026-09-23-kimi3/FEEDBACK.md`

## Non-goals
- S7 /bot polish/a11y (separate; do later or drop)
- xAI/Grok API seat brains
- Changing match rules / economy balance
- God-state coaching tools

## Slice order (do in order; PR per slice or one PR with clear commits)

### S1 — Observation parity for empire play (engine)
File: `src/tw2k/engine/observation.py` (owned_planets append ~L579-593)

Add to each `owned_planets[]` entry (owner-only, still fogged):
- `colonists` total (and/or per-commodity split if that is how planet stores them)
- `origin`: `"genesis" | "claim" | "other"` so brains do not treat auto-claim landings like genesis seed worlds
- Keep existing: id, sector_id, name, class, citadel_level, citadel_target, citadel_complete_day, fighters, shields

Also:
- Ensure `legal_actions[].reason` for `deploy_genesis`, `build_citadel`, `assign_colonists` stays accurate and is covered by tests
- Align `src/tw2k/agents/prompts.py` (it already claims owned_planets include colonists — make engine match the prompt)

Tests: extend observation / phase tests so owned_planets includes colonists after genesis deploy + assign; claim planet flagged differently from genesis.

### S2 — Stall detector (seat-safe)
Replace "same two plot targets = ping-pong" with **no progress toward declared goal**:
- Progress = sector change toward plot target, credit/cargo change matching intent, citadel_level/target change, genesis count change
- StarDock(1) <-> home ferry alternation is **allowed**
- Same-target replots (e.g. keep plotting StarDock) are **allowed**

Shared helper usable by Path-B and future LLM seats. Unit tests for ferry alternate, same-target replot, true 14<->571 no-progress loop.

### S3 — Goal-driven seat brain (replace brittle Path-B ladder)
New or rewrite `scripts/commander_p4_brain.py` (or `scripts/seat_brain_v2.py` + thin wrapper):
Goal ladder (scratchpad writeback already supported by harness):
1. Explore / map coverage until StarDock known
2. Upgrade to CargoTran when affordable
3. Buy genesis when credits allow and no citadel yet (or below target count)
4. Deploy only in legal sector (read reason); remember deploy sector
5. Land genesis planet -> `build_citadel` with `planet_id`
6. Ferry: StarDock buy colonists -> plot home -> land -> `assign_colonists` with `planet_id` + `qty` -> liftoff -> repeat
7. Prefer upgrading existing citadel over claiming empty neutrals

Hard rules:
- Read **only** mailbox observation
- Always pass required args (`planet_id`, `qty`, plot `target`+`execute`)
- Use `legal_actions.reason` when an action is illegal
- Never call `/state`

### S4 — Seat-only acceptance harness
- Script or pytest that feeds recorded / synthetic observations (no live `/state`) and asserts the brain emits legal genesis/build/ferry sequences
- Optional short live match: 3xKimi + seat brain on VENGEANCE `:8031`, log under `docs/playtests/…`, **Commander does not patch mid-match** unless crash

### S5 — Docs
- Update seat / player guide notes: observation fields, banned god-state, goal ladder
- Point FEEDBACK.md open items to closed slices

## Constraints
- Branch: `feature/grok-bot-harness` (continue) unless conflicted; then `feature/seat-bot-competitive`
- Never commit tokens, `.env`, `.tw2k/*` secrets, live tunnel URLs
- Keep existing mailbox / external harness protocol

## Done when
1. Tests prove owned_planets exposes colonists (+ origin) to the owning seat
2. Stall helper passes ferry / same-target / true-loop cases
3. Seat brain completes one offline genesis->citadel->ferry script without `/state`
4. Optional: one live short match log shows early genesis (by day 3-4), not day 9

## References
- `docs/playtests/multibot-2026-09-23-kimi3/FEEDBACK.md`
- `src/tw2k/engine/observation.py`
- `scripts/commander_p4_brain.py` (+ backups `.bak-0624`, `.bak-1035`)
- Prior parity plans under `docs/plans/2026-09-21-*.md`
