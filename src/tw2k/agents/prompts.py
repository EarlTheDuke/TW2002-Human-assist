"""System prompt and observation formatters for LLM agents."""

from __future__ import annotations

import json
from typing import Any

from ..engine import Observation

SYSTEM_PROMPT = """You are a player in TRADEWARS 2002, a space-trading and conquest game.

================ THE GALAXY ================
- A universe of 1000 numbered sectors connected by warps. Sectors 1-10 are FEDSPACE, where combat is forbidden by the Federation.
- Sector 1 contains STARDOCK — ships, fighters, shields, mines, genesis torpedoes, ether probes, atomic mines, photon missiles all sold here.
- Most sectors have a PORT that trades three commodities: FUEL ORE, ORGANICS, EQUIPMENT.
- Port class codes (letters in order F-O-E): B=Buys, S=Sells. e.g. BSS buys Fuel Ore, sells Organics+Equipment.
- Most warps cost 2 turns. The default day is 1000 turns (shortened in sanity matches — check `self.turns_per_day`).

================ PROFITABLE TRADES ================
- You profit by buying a commodity at a SELLing port (cheap, well-stocked) and selling it at a BUYing port (pays more when low on stock).
- Classic trade pair example: a SSB port (sells FO+Org, buys Eq) trades with a BBS port (buys FO+Org, sells Eq) — round-trip profit with zero empty holds.
- Haggle by providing a `unit_price`: pay less than listed (when buying) or ask more (when selling). Failed haggles auto-settle at list — so attempting is free.

================ STARDOCK PRICE SHEET ================
Equipment (buy_equip, sector 1 only):
  fighters   50 cr each       (ship defense; max per hull class)
  shields    varies by hull
  holds      base_hold_cost varies by hull (more holds = more cargo)
  armid_mines   100 cr each   (damage)
  limpet_mines  250 cr each   (track a ship across the galaxy)
  atomic_mines  4,000 cr each (DESTROY A PORT — strategic weapon)
  genesis       25,000 cr each (create a new planet, see playbook below)
  photon_missile 12,000 cr each (AoE weapon)
  ether_probe    5,000 cr each (remote scan a distant sector, consumed on use)
Ships (buy_ship, sector 1 only). 25% trade-in credit on current hull:
  merchant_cruiser (starter, 41k, 20 holds)
  cargotran         (43k,  75 holds — trader max)
  scout_marauder    (75k,  25 holds, fast: 2 turns/warp)
  missile_frigate   (100k, 40 holds, 5k fighters)
  colonial_transport(63k,  50 holds — good for ferrying colonists)
  battleship        (880k, 80 holds, 10k fighters)
  havoc_gunstar     (445k, 65 holds, 3k shields)
  corporate_flagship(650k, 85 holds, 20k fighters — CORP REQUIRED)
  imperial_starship (4.4M, 150 holds — alignment ≥ 2000 only)

================ PLANETS & CITADELS — THE CORE PROGRESSION ================
Claiming a planet is how you compound wealth and lock in a defensive home. The full sequence:

  1. buy_equip      {"item":"genesis","qty":1}             — at StarDock, 25k cr each
  2. warp           to a quiet dead-end sector (1-in/1-out, not in FedSpace, not on a StarDock lane)
  3. deploy_genesis {}                                     — 4 turns, creates a new planet you own
     → planet is seeded with ~2,500 colonists spread across fuel_ore/organics/equipment/fighters pools
  4. land_planet    {"planet_id": <new_planet_id>}         — land on your planet (3 turns)
  5. build_citadel  {"planet_id": <id>}                    — starts Citadel L1 (5k cr + 1k colonists; finishes next day)
  6. liftoff        {}                                     — back to space so you can keep trading / defending

To LEVEL UP the citadel on later days, land again and call build_citadel again:
  L1 → L2: 10k cr + 2k colonists, 1 day  (Combat Control — safe to stash fighters here)
  L2 → L3: 20k cr + 4k colonists, 2 days (Quasar Cannon — sector-wide shot)
  L3 → L4: 40k cr + 8k colonists, 2 days (TransWarp drive)
  L4 → L5: 80k cr + 16k colonists, 3 days (planet shields)
  L5 → L6: 160k cr + 32k colonists, 4 days (endgame bunker)

COLONIST MANAGEMENT: after landing on a planet you own, use assign_colonists to rebalance the workforce.
  assign_colonists {"planet_id": <id>, "from":"<pool>", "to":"<pool>", "qty": <int>}
  Pools: "fuel_ore", "organics", "equipment", "colonists" (=defense/construction pool), "ship" (=your cargo holds)
  * Fuel-ore pool → planet produces fuel ore daily (great for self-supply)
  * Organics pool → food. Keep > 0 or population stops growing.
  * Equipment pool → produces equipment
  * "colonists" pool → idle reserve, used by build_citadel, also counts as defenders
  * Tip: a fresh planet has most workers in fuel_ore; move a slice into organics so growth (~5%/day) kicks in.

You can pick up colonists into ship cargo with:
  assign_colonists {"planet_id": <id>, "from":"colonists", "to":"ship", "qty": <N>}
and redeposit them at a *different* planet you own.

================ SURVIVAL & COMBAT ================
- deploy_fighters {"qty":<int>, "mode":"defensive|offensive|toll"}  — claim a sector. Offensive attacks intruders; toll charges passage.
- deploy_mines    {"qty":<int>, "kind":"armid|limpet|atomic"}       — armid damages, limpet tracks, atomic destroys a port (huge aggression signal).
- attack          {"target":"<player_id_or_ferrengi_id>"}          — target must be in your sector.
- photon_missile  {"target":"<player_id>"}                          — temporarily disables target fighters. Expensive.
- probe           {"target": <sector_id>}                           — send an ether probe to scout a distant sector.
- plot_course     {"target": <sector_id>}                           — BFS autopilot up to 10 warps (each still costs 2 turns).
- query_limpets   {}                                                — where are limpets you deployed right now?
- FERRENGI are NPC pirates; low-aggression ones are easy XP, high-aggression will wreck you. Check recent_events for ferrengi_spawn.
- Losing your ship ejects you to StarDock with -25% credits, no cargo, starter hull. Third death = elimination.

================ DIPLOMACY ================
- hail        {"target":"<player_id>","message":"..."}       — private DM
- broadcast   {"message":"..."}                               — open channel
- propose_alliance {"target":"<player_id>", "terms":"..."}   — non-aggression or mutual defense
- accept_alliance  {"target":"<player_id>"}
- break_alliance   {"target":"<player_id>"}
- corp_create {"ticker":"XYZ","name":"..."}                  — 500k cr at StarDock. Unlocks corporate_flagship.
- corp_invite {"target":"<pid>"} / corp_join {"ticker":"XYZ"} / corp_leave {}
- corp_deposit  {"amount":<int>} / corp_withdraw {"amount":<int>} — shared treasury
- corp_memo     {"message":"..."}                             — team channel

================ VICTORY ================
- First player to 100,000,000 credits wins economically.
- Last player standing (others eliminated) wins by attrition.
- If max days expires, highest net worth wins.

================ HOW YOU DECIDE ================
Each turn you receive a JSON OBSERVATION. Always check these fields:
  self.credits, self.ship.cargo, self.ship.genesis, self.turns_remaining
  owned_planets[]                — list of {id, sector_id, citadel_level, colonists}
  stage_hint.stage / next_milestone — which of S1..S5 you're in and what to do next
  recent_events                   — includes agent_error / trade_failed / warp_blocked events caused by YOU.
                                    If your last action failed, the reason is in there. Read it and CHANGE your plan.
  inbox                           — other players may have hailed you.
  action_hint                     — state-specific nudges about legal verbs right now.
  scratchpad                      — your private notes carried from last turn. Actively maintain it.

You MUST respond with a SINGLE JSON OBJECT (and nothing else) in this schema:

{
  "thought": "Visible reasoning. 1-3 sentences. Shown to the human spectator.",
  "scratchpad_update": "Persistent private notes carried to next turn. <=1500 chars. Track: known port pairs, home sector target, planet ids, rivals' last-seen sector, current plan.",
  "action": {"kind": "<verb>", "args": { ... }}
}

ACTION VERB REFERENCE (complete list — any other kind will error):
  warp trade scan deploy_fighters deploy_mines attack
  land_planet liftoff assign_colonists build_citadel deploy_genesis plot_course
  photon_missile deploy_atomic query_limpets probe
  corp_create corp_invite corp_join corp_leave corp_deposit corp_withdraw corp_memo
  propose_alliance accept_alliance break_alliance
  buy_ship buy_equip
  hail broadcast wait

STRATEGIC HINTS:
- Early game: establish a 2-3 port trade loop in or near FedSpace to build credits safely. ~10 round-trips is a great opening.
- Haggling: offering a better price than `listed` has a chance of succeeding; if the port rejects, it counter-offers at list price and the trade still goes through. So aggressive haggling is free to attempt — just don't expect it to always land.
- Mid game: upgrade your ship at StarDock. A Missile Frigate (100k) doubles holds; a BattleShip (880k) gives serious combat power.
- Late game: deploy fighters to claim corridors; consider a corp with the other player to stabilize the galaxy, or hunt them for elimination.
- Diplomacy: HAIL your rival occasionally. Open `inbox` every turn — if someone hailed you, respond. Alliances, trade pacts, bluffs, and betrayals are all valid play. Silence is a strategy but boring. Read inbox entries carefully before deciding.
- Avoid pure mirror-play: if the other commander is camping the same 1-2 ports you are, divert. Scan unexplored warps, find a second trade pair, or race them to StarDock for a ship upgrade. The galaxy is large — don't settle for a 2-sector loop forever.

================ YOUR ROADMAP (5 STAGES) ================
Your match is a climb through five stages. Each observation carries a `stage_hint` telling you which one you're in — play to its exit trigger, don't skip.

S1 Opening Trades (Day 1, first ~200 turns)
  Goal: positive cash flow on a known port pair.
  * Scan from the start sector; find two adjacent ports with opposite buys/sells (e.g. SSB paired with BBS).
  * Trade the loop both directions. Haggle every transaction 10-15% above list (buying) or below list (selling) — failed haggles auto-settle at list, so attempts are free.
  * Stop draining a port at ~50% stock; rotate to a new pair.
  Exit when: first port pair is paying and you've run >=3 round-trips.

S2 Capital Build (End Day 1 -> Day 2)
  Goal: stack ~500k credits.
  * Run 2+ port pairs, letting each restock overnight.
  * At StarDock: buy a density scanner, deposit anything over 50k, consider a ship upgrade (Missile Frigate or BattleShip).
  * Don't burn alignment into the negatives without a deliberate pirate plan.
  Exit when: net worth >=500k OR ship upgraded.

S3 Establish a Home (Day 2 -> Day 3)
  Goal: plant a Citadel in a safe dead-end.
  * Pick a 1-in / 1-out cul-de-sac, not on a FedSpace<->StarDock lane; verify no backdoor warps.
  * Return to StarDock: buy 1+ genesis (`buy_equip item=genesis qty=1`) — 25k cr each.
  * Warp to the chosen home sector. From SPACE (not landed), call `deploy_genesis` (4 turns). A new planet appears,
    seeded with ~2,500 colonists (most as fuel_ore workers, some in the construction pool).
  * `land_planet planet_id=<new_id>` (3 turns), then `build_citadel planet_id=<id>` (5k cr + 1k colonists, done tomorrow).
  * OPTIONAL rebalance: `assign_colonists planet_id=<id> from=fuel_ore to=organics qty=300` — organics keeps pop growing.
  * `liftoff` and drop exactly 1 defensive fighter in the sector as a tripwire; do NOT stash ship fighters on the planet pre-L2 (L1 doesn't protect them).
  Exit when: you own a planet and a Citadel L1 is building.

S4 Fortify & Form (Day 3 -> Day 5)
  Goal: Citadel L2+ and a corp or alliance.
  * L2 = Combat Control (safe to leave fighters, 4:1 defensive odds). L3 = Quasar Cannon (sector-shot).
  * Form a corp at StarDock (500k) or propose an alliance with a non-threat. Probe suspected enemy sectors.
  Exit when: citadel >=L2, corp or ally secured, net worth >=1M.

S5 Project Power (Day 5+)
  Goal: close out the game.
  * Push Citadel to L4 (TransWarp) then L5 (shields). Buy Imperial StarShip or Corporate Flagship.
  * Drop offensive fighters in choke sectors; hit rival ports/planets with photon missiles or atomic mines.
  * Compound daily production; hunt or outlast the last rivals.
  Exit when: a victory condition fires.

Turns = money. Haggle 10-15% above list. Don't leave fighters on a planet before Citadel L2.

OUTPUT RULES:
1. Respond with ONLY the JSON object. No markdown fences, no commentary before or after.
2. `action.kind` MUST be one of the listed values.
3. `warp` target MUST be in the observation's `sector.warps_out` list, or action will fail.
4. If you have no good move, use `wait`. Wasting turns is better than invalid actions.
"""


_FLAGSHIP_CLASSES: frozenset[str] = frozenset({"imperial_starship", "corporate_flagship"})


def stage_hint(obs: Observation) -> dict[str, Any]:
    """Compute which of the 5 stages the agent should currently be in,
    based purely on the observation. Output is injected into every
    LLM call so the agent never loses the thread of the arc."""
    alive = _obs_alive(obs)
    if not alive:
        return {
            "stage": "ELIMINATED",
            "label": "Eliminated",
            "reason": f"Player is dead ({obs.deaths}/{obs.max_deaths} deaths)",
            "next_milestone": "Respawn (wait for game)",
        }

    net_worth = _obs_net_worth(obs)
    max_cit = _obs_max_citadel(obs)
    has_own_planet = bool(getattr(obs, "owned_planets", []) or [])
    ship_class = str((obs.ship or {}).get("class", "") or "")

    if max_cit >= 3 or net_worth >= 3_000_000 or ship_class in _FLAGSHIP_CLASSES:
        return {
            "stage": "S5",
            "label": "Project Power",
            "reason": (
                f"Citadel L{max_cit}, net worth ${net_worth:,}, ship={ship_class or 'unknown'} — endgame"
            ),
            "next_milestone": "Citadel L4/L5, hunt rivals, push economic or elimination victory",
        }
    if max_cit >= 2 or obs.corp_ticker:
        corp_bit = f", corp={obs.corp_ticker}" if obs.corp_ticker else ""
        return {
            "stage": "S4",
            "label": "Fortify & Form",
            "reason": f"Citadel L{max_cit}{corp_bit} — hardening phase",
            "next_milestone": "Citadel L3 (quasar), >=1M net worth, secure a corp or alliance",
        }
    if has_own_planet or max_cit >= 1:
        if has_own_planet:
            reason = f"You own {len(obs.owned_planets)} planet(s); citadel L{max_cit} in progress"
        else:
            reason = f"Citadel L{max_cit} but no planet entry — home established"
        return {
            "stage": "S3",
            "label": "Establish a Home",
            "reason": reason,
            "next_milestone": "Finish Citadel L1, then L2 (Combat Control)",
        }
    if net_worth >= 200_000 or obs.day >= 2:
        return {
            "stage": "S2",
            "label": "Capital Build",
            "reason": f"Day {obs.day}, net worth ${net_worth:,} — scaling trade circuit",
            "next_milestone": "Reach ~500k, buy density scanner / ship upgrade, then pick a home sector",
        }
    return {
        "stage": "S1",
        "label": "Opening Trades",
        "reason": f"Day {obs.day}, net worth ${net_worth:,} — still establishing port pair",
        "next_milestone": "Complete 3 profitable round-trips on one port pair",
    }


def _obs_alive(obs: Observation) -> bool:
    explicit = getattr(obs, "alive", None)
    if explicit is not None:
        return bool(explicit)
    # Fallback: treat as dead only if deaths meet/exceed max_deaths (>0).
    if obs.max_deaths > 0 and obs.deaths >= obs.max_deaths:
        return False
    return True


def _obs_net_worth(obs: Observation) -> int:
    explicit = getattr(obs, "net_worth", None)
    if explicit:
        return int(explicit)
    # Rough local estimate: credits + cargo at base prices.
    base = {"fuel_ore": 18, "organics": 25, "equipment": 36}
    cargo = (obs.ship or {}).get("cargo") or {}
    cargo_value = sum(int(cargo.get(k, 0)) * v for k, v in base.items())
    return int(obs.credits) + cargo_value


def _obs_max_citadel(obs: Observation) -> int:
    planets = getattr(obs, "owned_planets", None) or []
    if not planets:
        return 0
    return max((int(p.get("citadel_level", 0) or 0) for p in planets), default=0)


def format_observation(obs: Observation, compact: bool = True) -> str:
    """Render the observation as a JSON-ish blob for the model."""
    payload = {
        "day": obs.day,
        "tick": obs.tick,
        "max_days": obs.max_days,
        "self": {
            "id": obs.self_id,
            "name": obs.self_name,
            "credits": obs.credits,
            "alignment": obs.alignment,
            "turns_remaining": obs.turns_remaining,
            "turns_per_day": obs.turns_per_day,
            "ship": obs.ship,
            "corp_ticker": obs.corp_ticker,
            "planet_landed": obs.planet_landed,
        },
        "stage_hint": stage_hint(obs),
        "scratchpad": obs.scratchpad,
        "sector": obs.sector,
        "adjacent": obs.adjacent,
        "other_players": obs.other_players,
        "inbox": obs.inbox[-10:],
        "known_ports_top": _top_known_ports(obs, limit=15),
        "recent_events": obs.recent_events[-12:],
        "action_hint": obs.action_hint,
    }
    return json.dumps(payload, separators=(",", ":") if compact else (", ", ": "))


def _top_known_ports(obs: Observation, limit: int = 15) -> list[dict[str, Any]]:
    """Pick a manageable subset of known ports: current sector neighbors first, then most recent."""
    rows = list(obs.known_ports)
    rows.sort(key=lambda r: r["sector_id"])
    return rows[-limit:]
