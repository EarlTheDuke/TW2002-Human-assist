# profile-off-digest-bisect-v1

The written goldens are the action digest from `scripts/run_scripted_match.py --days 10 --action-digest`: `zlib.crc32` of the action rows, printed as `ACTION_DIGEST`. Seed 250925 is `24863a3d`. Seed 4242 is `98a47c8a`. Both rejected 0/0.

`f772752b403d2cd51c19e4da` and `1030418c32c76637db7eed97` are not action digests. They are `tests/fed_legacy_digest.py` `legacy_run_digest(root, "N3,N2,N1,H", 10, seed)`, the first 24 hex characters of a sha256 over observations, prompts, actions, results and state. That call also forces every `*_MODE` whose value is `"tw2002"` to `"legacy"`.

Both strings were measured on `717bbf2929d3609b3a95e0b60869a1dc5f1d0bcb`, profile unset, before `ab858ab5` existed (that commit is 01:19 UTC; the logs are 01:10 and 01:13 UTC on 19 Oct 2026):

- `/tmp/note89-digest.log` from `/tmp/note89_digests.py`, `root = Path("/workspace")`. `track-d-note89` was still `717bbf29` (created from `origin/feature/grokbot-player` at that sha).
- `/tmp/note89-tip.log` and `/tmp/note89-tip4242.log` from a clean worktree `/tmp/note89-before`. The log prints `code /tmp/note89-before/src/tw2k/engine/constants.py` and `colonist_units_live` absent.

The same sha's action digest, measured later with `--action-digest`, is `24863a3d`. The merge queue's reading of tip `c05f7bea` matches that command. The other checksum was the wrong instrument on `717bbf29`.

Bisect of `feature/grokbot-player` first-parent, `fb04cf58` through tip `c05f7bea`. Profile unset (`V311_PROFILE` and `TW2002_LIVE_PROFILE` absent). Command:

```
python3 -u scripts/run_scripted_match.py --seed 250925 --days 10 --action-digest
```

The whole report, not only the crc, matches `fb04cf58` at every commit. Citadel `{"P1": [2, 2, 2, 0], "P2": [0], "P3": [1]}`. Rejected 0/0. Exceptions 0.

| Commit | What landed | Action digest |
|---|---|---|
| `fb04cf58` | baseline | `24863a3d` |
| `607c9b44` | merge NOTE 76, creator end game | `24863a3d` |
| `717bbf29` | free start colonists out of net worth; scripted regen clock held still | `24863a3d` |
| `a5b9eeb3` | merge NOTE 82, extern gaps | `24863a3d` |
| `cb593247` | dawn-tax sentence | `24863a3d` |
| `c56704a4` | merge NOTE 79, combat gaps | `24863a3d` |
| `55fba9ad` | merge NOTE 84, player manual | `24863a3d` |
| `c05f7bea` | merge NOTE 78, universe and planet gaps (tip) | `24863a3d` |

No merge in that range is the first one that changes the profile-off digest. Seed 4242 on `fb04cf58` and on `c05f7bea` is `98a47c8a` both, reports identical, citadel `{"P1": [2, 0], "P2": [0], "P3": [2]}`, rejected 0/0.

Nothing in the range flips a stored `*_MODE` off `legacy`. New helpers (`start_colonist_nw_live`, `bust_record_clear_live`, `ship_chart_cap_live`, `corp_planet_disband_v306`, `photon_follow_damp_live`, `death_delay_live`, `treasury_cap_live`, `course_max_live`, `big_bang_density_live`, `one_way_share_live`, `atomic_detonator_live`) stay false with the profile unset. Paths that run either way keep the old result: busts still clear every extern, the treasury cap stays `PLANET_TREASURY_CAP`, a plotted course still searches `PLOT_COURSE_MAX_DEPTH * 6` hops, and `death_delay_days` returns 0 so the pod lock never starts. The creator end screen runs only when the creator ends the match. Free-start colonist accounting is a no-op while that count stays 0.

No engine change. The goldens were already on the tip.
