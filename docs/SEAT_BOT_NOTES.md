# Seat-bot notes (S5)

The seat brain decides from one fogged Observation. It does not read the universe, another seat's mailbox, or the spectator `/state`.

Source of the field list: `Observation` in `src/tw2k/engine/observation.py` (verified against `Observation.model_fields`). The ladder is the docstring of `src/tw2k/agents/seat_brain.py`.

## Fields the brain may use

Match: `day`, `tick`, `max_days`, `finished`.

Self: `self_id`, `self_name`, `credits`, `alignment`, `alignment_label`, `experience`, `rank`, `turns_remaining`, `turns_per_day`, `ship`, `corp_ticker`, `planet_landed`, `scratchpad`, `goals`, `alive`, `net_worth`, `owned_planets`, `deaths`, `max_deaths`.

Where: `sector` (this sector only), `adjacent` (one hop, fogged), `known_ports`, `known_warps`, `known_sectors` (coordinates only for sectors this seat has visited, scanned, or probed).

Trade memory: `trade_log`, `trade_summary`, `recent_failures`.

Other people, already fogged: `other_players` (corp mates fuller; others last-known), `rivals` (public net worth; location only if witnessed), `orphaned_planets`, `inbox`, `alliances`, `corp`.

Feed and tools: `recent_events` (same visibility as `GET /events`), `limpets_owned`, `probe_log`, `action_hint`, `legal_actions`.

Operator notes, if the host set them: `operator_directive`, `operator_directive_updated_day`, `operator_directive_updated_tick`, `operator_dialogue`.

`status_line` is not an Observation field. The harness adds it from `status_fields(obs)` in the same file: `Day N of M - T turns left today - Rank R of S`, or `GAME OVER` when `finished`.

## Banned god-state

Anything not on that list. In particular the brain must not use:

- `universe.events` unfiltered, another player's sector, cargo, credits, or scratchpad
- sectors that are not in `known_warps` / `known_sectors` / `sector` / `adjacent`
- a port's live price in a sector this seat has not scouted (`known_sectors.port` is the remembered code)
- another seat's mailbox file, token, or `last_result`

`build_observation` is the filter. `_event_visible_to` in the same module decides which events become `recent_events`. Public kinds (game start, day tick, game over, planet claimed, broadcast, port destroyed, and the rest of `_PUBLIC_EVENTS`) are visible to every seat. Actor-only kinds (scan, probe, buy, warp blocked, trade failed, autopilot, and the rest of `_ACTOR_ONLY_EVENTS`) are visible to the actor. Everything else is sector-local or party-local.

## Goal ladder

`SeatBrain.decide` takes the first rung that returns a legal action (`src/tw2k/agents/seat_brain.py`):

1. Landed: assign colonists aboard, else build the citadel, else liftoff. Never ferry colonists onto a claimed neutral. Only genesis worlds are work sites.
2. Genesis aboard: deploy when `deploy_genesis` is legal, else carry it out of StarDock / FedSpace using `legal_actions.reason`.
3. At a home world with a reason (colonists aboard, or a citadel that can be built): land.
4. Before the first world: CargoTran at StarDock before the first genesis, then genesis, then the colonist ferry that citadel still needs.
5. After the first world: pick by value per turn. Trade, a colonist ferry when it unlocks a citadel tier or refills a world, another genesis, organics resupply, or a stockpile sale. `target_planets` rises above 2 while another torpedo is affordable.
6. Colonists or organics already aboard are delivered before a new choice.
7. Exploration plots through `known_warps` to the nearest known sector that still has an unvisited neighbour.

A stall is no progress toward the declared intent (`tw2k.agents.stall.StallDetector`), not a repeated target. On a stall the brain explores for a few turns, then returns to the ladder. Memory goes home through `scratchpad_update`.
