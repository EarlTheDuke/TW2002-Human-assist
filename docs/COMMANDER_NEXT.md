# COMMANDER_NEXT - Complete cockpit + multi-bot parity planning

## State
- **machine_state:** `WAITING_COMMANDER`
- **phase:** `parity-e0`
- **updated_at:** `2026-09-21T18:41:00-07:00`
- **updated_by:** `Fable`

## Active task
**id:** `parity-e0-fable-plan`
**title:** Independent Fable plan — complete human cockpit + competitive multi-Grok-Bot parity
**instructions:**
(idle - waiting on Commander)

Plan written: `docs/plans/2026-09-21-fable-parity-plan.md`. Read §0 (code findings F1-F11) and §H (13 explicit disagreements + proposed merged outline) first. Recommended first slice after merge: **S1 - server data + fog fixes** (observation peek, fogged event stream with `facts` whitelist, spectator token gate, webhook deadline fix, remove/gate the xAI seat script). Two fog leaks found in code (spectator routes on a hosted URL; `copilot/dashboards.build_route_table`). Changelog 18:40 PT has the summary.

Note: the localhost.run tunnel is down (cloudflared still up); re-expose before the next CU session.

## Queue
_Commander merges both plans into `docs/plans/2026-09-21-bot-human-parity.md` and queues the first build slice._

## Ben messages (rare)
_Nothing needed from Ben._
