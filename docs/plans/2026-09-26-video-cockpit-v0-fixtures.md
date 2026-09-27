# Video cockpit V0 - trigger resolver spec and event fixtures (for Ben's review)

**Phase:** V0 (spec lock, no runtime / UI change). **Source plans:** `2026-09-26-video-cockpit-phase-plan.md` sections 4.1-4.3, `2026-09-26-video-cockpit-production-plan.md`.
**Fixtures:** `tests/fixtures/media_events/*.json`, recorded by `python scripts/media_record_fixtures.py` from the real engine on seed 250925 (200 sectors, the CU pilot galaxy). Each batch is exactly what `/harness/v1/{seat}/events` returns to the viewing seat: `event_view()` rows filtered by `_event_visible_to()`.

## Resolver contract (implemented in V2, specified here)

```
resolve(batch, obs, state) -> [{clip_key, priority}, ...]   # ordered, highest priority (lowest number) first
```

- **batch:** new `/events` rows for this seat, ascending `seq` (fields: `seq, day, tick, kind, actor_id, sector_id, summary, facts`).
- **obs:** the seat's own observation after the batch; only `self_id`, `sector.id`, `sector.port.class_id`, `ship.class` are used.
- **state:** client memory: `visit_sector` (where the seat last arrived) and `docked_in_visit` (a dock clip already fired this visit). The resolver updates it (a self `warp`/`autopilot` arrival resets both).
- **Priorities:** P0 threat to self, P1 your combat result, P2 your movement / docking, P3 witnessed in your sector, P4 ambient change. Public events elsewhere never enter the output.
- **Coalescing inside one batch:** all self hops + `autopilot` -> one `warp.out`; several trades at one port -> one `dock.port`; several combat rows -> the worst outcome for self (incoming > miss > hit); `ferrengi_attack` + its `combat` row -> one `combat.incoming`.
- **Predicates** (the only names a manifest `rule` may use; the validator rejects others): `self`, `self_attacker`, `self_defender`, `self_victim`, `first_in_visit`, `outcome_hit`, `witnessed_in_my_sector`.
- **Pure and fog-safe:** input is fogged rows + the seat's own observation; no DOM, no `/state`, no clock. Queue, preemption and staleness act on the resolver's output in the renderer (V2).

## Expected outcomes (V2 trigger set: `dock.port`, `warp.out`, `combat.hit|miss|incoming|witnessed`)

| Fixture | Viewer state before | Batch the seat receives | Expected output | Why |
|---|---|---|---|---|
| `single_warp` | in s11, not docked | `warp` (self, 11 -> 148) | `warp.out` P2 | Own movement. Arrival resets the visit to s148. |
| `autopilot_burst` | in s11 | 6 x `warp` (self) + `autopilot` (self), ends s12 | `warp.out` P2 (once) | Coalesce the burst into one clip; the last hop sets the arrival ambient. |
| `trade_burst` | at port s19, not docked | 3 x `trade` (self, s19) | `dock.port` P2 (once) | First trade of the visit = docking; later trades in the batch coalesce. |
| `trade_same_visit` | at s19, already docked | `trade` (self, s19) | none | `first_in_visit` false. The log and toast still update. |
| `trade_failed` | at port s19, not docked | `trade_failed` (self, s19) | `dock.port` P2 | A rejected trade still means the ship pulled up to the port. |
| `self_attack_win` | in s14 | `combat` (self attacker, defender P2 left with 0 fighters) + `ship_destroyed` (victim P2) | `combat.hit` P1 | `outcome_hit`. The rival's destruction is not a first-person clip in the V2 set. |
| `self_attack_lose` | in s14 | `combat` (self attacker, own fighters 0, defender 2,966 left) | `combat.miss` P1 | Needs the V2 `outcome` / losses fact (pre-V2 fallback: `combat.hit`). See finding 1: the viewer was destroyed but got no `ship_destroyed` row. |
| `ferrengi_attack` | in s16 | `ferrengi_attack` (victim self) + `combat` (ferrengi_vs_ship, defender self) | `combat.incoming` P0 (once) | Threat to self; both rows coalesce. See finding 1 (the viewer was destroyed too). |
| `witnessed_combat` | in s14 | `combat` (P2 attacks P3 in s14) + `ship_destroyed` (victim P3) | `combat.witnessed` P3 | Not self, same sector as the viewer. |
| `far_port_destroyed` | in s11 | `port_destroyed` + `atomic_detonation` (P2, s16, public) | none | Public events far away never get a first-person clip (ticker caption only). |
| `other_trade_in_sector` | at s19 | `trade` (P2, s19, witnessed) | none | Someone else's trade: no dock clip. |

### Sequence cases (built from the fixtures above; renderer behaviour, V2)

| Case | Input | Expected |
|---|---|---|
| Incoming preempts dock | `trade_burst` then, while `dock.port` plays, `ferrengi_attack` | `combat.incoming` (P0) preempts with a 150 ms crossfade; `dock.port` is not resumed. |
| Equal priority waits | `single_warp` then `trade_burst` in the next poll | `dock.port` replaces the waiting slot; it does not interrupt the playing `warp.out`. |
| Stale drop | a waiting item older than `stale_ms` (4 s), or a newer self action already posted | Dropped. Clips never lag the game. |
| Cooldown | `witnessed_combat` twice within 10 s | Second one suppressed (`combat.witnessed` cooldown 10 s in the v2 example). |
| Tab hidden | any batch while `document.hidden` | No clip; only `lastSeq` advances. |

## Findings from recording (for Commander / Ben)

1. **Engine fog bug: a destroyed seat never sees its own `ship_destroyed` event.** `engine/combat.py::_destroy_ship()` moves the victim to StarDock *before* emitting `ship_destroyed` with `sector_id=death_sector`, and `Universe.emit` captures `_witnesses` from that sector's occupants at emit time. The killer is the actor, so the victim is in neither set. This hides deaths from the victim's `/events` stream and from LLM seats' `recent_events` too, not just from the future viewport P0 key `self.ship_destroyed`. Suggested one-line fix (a runtime change, so not in V0): pass `_witnesses` = the death sector's occupants before the move plus the victim. `tests/test_video_cockpit_v0.py` holds a strict `xfail` that flips when it's fixed.
2. **`outcome` is needed to tell hit from miss** (as the phase plan says): ship-vs-ship `combat` rows carry post-fight fighters/shields but no losses. `self_attack_lose` shows the attacker at 0 fighters, which a client could read as a miss, but a real `outcome` fact (V2 engine micro-change) is the reliable signal.

## Manifest v2 schema + validator

- `web/media/manifest.schema.json` (JSON Schema 2020-12): v1 (`kinds`, `groups`) unchanged and still valid. v2 adds `ambient`, `clips` (priority, caption, fallback still, variants with tags / weight / webm / mp4 / poster / duration / bytes / provenance) and `triggers` (`kind`, `rule`, `clip`, `coalesce`).
- `scripts/media_validate_manifest.py` (extended, not forked): schema, files exist, known predicates only, trigger -> clip references, real `EventKind` names, public-only kinds need a local predicate, `bytes` match + size budget (600 KB per event clip, 900 KB per ambient loop), `--probe` checks durations with ffprobe.
- `web/media/examples/manifest.v2.example.json`: a valid v2 manifest wired with placeholder poster-only variants (the existing stills), exactly the V2 placeholder plan. `web/media/manifest.json` stays v1, so nothing changes at runtime.
