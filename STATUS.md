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
- **Known red:** a bot banking loop is still open (see commit 9dfe6487, #436).
  The test suite itself is green as of 2026-11-07.
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
