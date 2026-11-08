# TW2K-AI — Working Agreement for Claude Code (read first)

This file auto-loads every Claude Code session in this repo. It is the operating
manual; the *direction* lives in the docs it points to. Keep it short — link, don't
duplicate. Note the folder is `Projects in prgress` (sic) — that typo is the real path.

## Read before planning work
1. **[STATUS.md](STATUS.md)** — the ONE living status page: trunk, rule set, known red,
   recent changes. Update it (a dated line under "Recent changes") when project state
   changes. Do not create new "readiness"/handoff/status docs.
2. **[docs/NORTH_STAR.md](docs/NORTH_STAR.md)** — direction: keep hardening the cockpit →
   an AI player that plays *only* from what the cockpit shows → a voice front end on it.
   The core question: is the cockpit enough for an AI to make every decision a human would?
   Every gap is a cockpit bug.
3. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**, **[docs/DESIGN.md](docs/DESIGN.md)**,
   **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** — core references. `docs/plans/` = plans
   still referenced by code/tests; `docs/archive/` = read-only history (don't revive it).
4. **[docs/reference/](docs/reference/)** — original TW2002 source material; the fidelity
   yardstick.

## Standing rules (from NORTH_STAR)
- **Fidelity to the original game first** (TW2002 v3.x / TWGS, v3.11 rules). Showing more
  data than the original did is fine where it helps.
- **v3.11 is the stored default rule set** (`V311_PROFILE = "v311"`). Phase 2 retires the
  legacy switches in batches.
- **Cockpit changes go behind `COCKPIT_LAYOUT=redesign`**; `/bot` (legacy layout) stays unchanged.
- **Engine changes go behind flags that default to legacy.**
- **Batch O stays on hold.** The separate 3D map prototype stays out.

## The game you actually run
- The current game is the **Galaxy War Command lobby**, not `tw2k serve` / `/play`
  (that is the super-old dashboard, even though README still leads with it):
  `python -m tw2k.cli lobby --port 8099 --game-ports 8100-8109 --root <scratch-dir>`
  then create games via `POST /api/accept` + `POST /api/games`
  (`name, humans, bots, universe_size>=200, visibility`). Hand the user the
  `cockpit_links` URL (`/g/<id>/bot?seat=P1&token=…&layout=redesign`); the user clicks
  "I understand" on the notice themselves.
- Keep lobby roots in a scratch dir, not the repo.

## Verify pipeline (PowerShell, from the repo root)
```powershell
$env:PYTHONPATH = "src"; $env:PYTHONIOENCODING = "utf-8"
python scripts/run_quick.py            # quick tier — run on every change (minutes)
ruff check src tests scripts           # lint (CI runs this)
python -m pytest -q                    # full suite = what CI runs (~1 hour; run in background)
```
- CI: `.github/workflows/ci.yml` (pytest on 3.11 + 3.12, plus ruff). Full suite is slow —
  run it in the background, or run only the touched test files plus the quick tier.
- **Known red (pre-existing on main as of 2026-11-07):**
  `test_note173_manual_v1.py::test_v311_mode_lists_every_switch` and two tests in
  `test_v311_exp_alignment_trade_gaps_v1.py` (haggle experience gap); also
  `test_v311_daylen_and_yard_v1.py::test_item2_…` is timing-flaky on CI. Don't mistake
  these for your regression; fixing them is welcome.
- Don't add tests that only check doc wording (the 7c cleanup removed those).
- Throwaway/debug harnesses get deleted before commit.

## Windows gotchas (each has burned a session)
- `PYTHONPATH` separator is `;` on Windows. `src:.` is ONE bogus path, so `tw2k` silently
  imports from the editable install (the MAIN checkout), not your worktree. Use `src`.
- Set `PYTHONIOENCODING=utf-8` — the CLI banner crashes on cp1252.
- New worktrees: `git -c core.longpaths=true worktree add …`, then
  `git config core.longpaths true` inside it (docs/reference paths are too long otherwise).
- `git stash` is shared across worktrees and holds Commander stashes — only pop a stash
  you just pushed; check `git stash list` after.
- **`git worktree remove` deletes gitignored data (saves/, .tw2k/, .env) without warning.**
  Before removing a worktree: check for processes using it and archive its ignored files.

## Git and secrets
- Trunk is `main`. Branch from `main`, merge back to `main`, delete the branch once merged.
- Never commit `.env`, `.tw2k/` (seat tokens), `*external_tokens*.json`,
  `docs/MIXED_LLM_ACCESS.md`, `saves/`, or screenshots under `docs/` (they belong in
  `artifacts/`, which is ignored). Stage files by name; don't `git add -A` / `git add .`.
- Remote: `https://github.com/EarlTheDuke/TW2002-Human-assist`. Push at good stopping points.
- Don't run Cursor's agent and Claude Code on the same files at the same time.

## Working style
Ben (the user) gives direction and wants it carried out end to end: make the reasonable
default call, note it, keep going. Explain game-design choices in plain language. Stop to
ask only for a direction fork with no clear default, an irreversible/external action, or
tests that can't go green after a real attempt.
