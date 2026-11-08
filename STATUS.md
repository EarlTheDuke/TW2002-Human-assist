# Project Status

The one living status page for TW2K-AI. Update this file when the state of the
project changes. Do not add new per-slice "readiness onto tip" or handoff docs;
put a dated line under "Recent changes" here instead.

_Last updated: 2026-11-07_

## Where things stand

- **Trunk:** `main`. `feature/grokbot-player` was the working trunk through
  October 2026; it was fast-forwarded into `main` on 2026-11-02 and both point
  at the same commit. New work branches from `main` and merges back to `main`.
- **Rule set:** v3.11 is the stored default (`V311_PROFILE = "v311"`). Phase 2
  is retiring the legacy switches in batches (batch 1: four switches, batch 2:
  ten more).
- **Known red:** none. The bot day-1 banking loop (#436) was fixed by #438
  (c23ef387); confirmed 2026-11-07 (see Recent changes).
- **Direction:** see `docs/NORTH_STAR.md` (cockpit-only AI player, then voice).

## Run the tests

```powershell
pip install -e ".[dev]"
python -m pytest -q                         # full suite (what CI runs)
$env:PYTHONPATH = "src"; python scripts/run_quick.py   # quick set
```

CI: `.github/workflows/ci.yml` (pytest on 3.11 and 3.12, plus ruff).

## Where things live

| Path | What |
|---|---|
| `src/tw2k/engine/` | Game engine |
| `src/tw2k/agents/` | AI seats (LLM, heuristic, seat brain, cockpit seat) |
| `src/tw2k/server/`, `src/tw2k/public/` | FastAPI server, harness, lobby |
| `web/` | Spectator UI and cockpits (`/`, `/play`, `/bot`, `/bot2`) |
| `docs/DESIGN.md`, `docs/ARCHITECTURE.md`, `docs/USER_GUIDE.md` | Core docs |
| `docs/plans/` | Plans still referenced by code or tests |
| `docs/archive/` | Finished plans and old process docs (read-only history) |
| `docs/reference/` | Original TW2002 source material |

## Housekeeping rules

- One status page (this file). No "readiness", "fleet order", or "stills
  inbound" refresh commits.
- Secrets stay out of git: `.env`, `.tw2k/`, and `docs/MIXED_LLM_ACCESS.md`
  are ignored.
- Delete a work branch once it is merged.

## Recent changes

- 2026-11-08: Claude seat session 3 (`docs/playtests/claude-seat-v1/session3-log.md`):
  bots now arm (630 fighters, from 30); ether probes show a per-sector report; the attack
  result names a kill; TransWarp form shows turns saved; port-upgrade wording. Still open:
  a fight with an armed bot (scanner-equipped bots avoid sectors holding your fighters).

- 2026-11-08: Claude seat session 2 (`docs/playtests/claude-seat-v1/session2-log.md`).
  Fixed: haggle counters were dropped (cockpit matched "counter 22", engine says
  "countered at 22"); comms box kept focus after Send; Deployed Fighters ignored
  detonations; **heuristic bots never outfitted under v3.11** (checked `sector == 1`
  for StarDock) — v3.11 pins re-pinned on purpose. Open for Ben: citadels are
  unreachable under v3.11 (Terra's 30,000 stored as people, not thousands — see the log
  for evidence and a one-line recommendation); a mine kill passes no killer, so the mine
  owner is never told.

- 2026-11-08: Claude seat pilot (Claude playing the redesign cockpit in a browser,
  1,000,000 cr, `docs/playtests/claude-seat-v1/pilot-log.md`). Fixed: the manual said
  StarDock is sector 1 (v3.11 draws it per game; now names this game's sector); the
  ship panel counted colonists as holds; the planet panel names the type ("Class U
  (Gaseous)"); form labels were raw parameter names. Rule fix: under v3.11 turn regen a
  WAIT the server inserts for a slow seat no longer counts toward the four-WAIT
  stand-down, which threw away a seat's banked turns (`wait_counts_toward_standdown`).

- 2026-11-07: North Star run (cockpit-only AI seat, kimi-k2.6, v3.11, 3 x 1h days):
  the trade loop runs fully from the cockpit, but the AI looped one route and finished
  3rd of 4. Findings in `docs/playtests/cockpit-ai-seat-v4/gaps.md`. Top one is a
  server rule: four timeout auto-WAITs in a row throw away a seat's saved turns. The
  xAI and Anthropic keys in `.env` are invalid. The player now retries a slow model reply.

- 2026-11-07: Retired `scripts/smoke_phase_abc.py` from CI and the repo. It was
  unchanged since the first commit, failed under both rule sets, and duplicated
  `tests/test_phase_abc.py`. CI had never passed before: pytest failing first hid it.
- 2026-11-07: Closed the bot banking loop (#436). It was already fixed by #438:
  traces on five seeds (days 1-3, v3.11, 100k credits) show one deposit and then
  trading, and `test_two_humans_play_two_days_through_the_proxy` (the playtest that
  was red, incl. the day-2 fight) passes locally in 2m50s.
- 2026-11-07: Main is green again. Fixed the three red tests left by Phase 2
  batch 2 (they still expected the retired capped-gap haggle rule and a switch list
  without the retired switches); removed the dead `PORT_HAGGLE_XP_CAP`; the in-game
  manual now states the +1/+2 haggle experience rule instead of "up to 10"; the
  day-roll timing test stamps rolls at the runner instead of polling (CI flake).
- 2026-11-07: Merged the 7c test cleanup (#443) into `main`. Added `CLAUDE.md`
  (working agreement for Claude Code sessions). Known red on `main`: three v3.11
  switch tests (`test_note173_manual_v1`, `test_v311_exp_alignment_trade_gaps_v1`);
  the 7c branch did not cause them. Pruned stale worktrees after archiving their
  saves and uncommitted work (see `TW2002-worktree-archive-2026-11-07` next to this repo).

- 2026-11-02: Repo cleanup. Landed the v3.11 default and Phase 2 batches 1-2
  on `main`; moved 515 unreferenced plan and process docs to `docs/archive/`;
  fixed garbled characters in README and `agents/external.py`; pruned merged
  branches.
