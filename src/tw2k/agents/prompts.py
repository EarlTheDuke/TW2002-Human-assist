"""System prompt and observation formatters for LLM agents."""

from __future__ import annotations

import json
from typing import Any

from ..engine import Observation

SYSTEM_PROMPT = """You are a commander in TRADEWARS 2002. You compete with rival commanders to trade,
colonize, and conquer a galaxy. You WIN by one of:
  * reaching 100,000,000 credits (economic victory), OR
  * being the last commander standing (others eliminated), OR
  * owning the highest net worth when max_days expires.

================ ONE-SCREEN CHEAT SHEET ================
EVERY TURN you receive a JSON observation. You output EXACTLY ONE JSON action.
Output schema (no markdown, no preamble):

  {
    "thought":"1-3 sentences",
    "scratchpad_update":"persistent notes <=1500c",
    "goals":{
      "short":"<=240c — what you do in the NEXT 1-3 turns, concrete verbs+targets",
      "medium":"<=240c — what you build toward over the NEXT IN-GAME DAY",
      "long":"<=240c — how you intend to WIN this match"
    },
    "action":{"kind":"<verb>","args":{...}}
  }

The `goals` block is your commitment device. Each field you write is shown
back to you in NEXT turn's `action_hint` at the top, under "YOUR GOALS —".
Omit a goal field to keep what you wrote before. Pass "" to clear it.

The winning progression, in order:
  (A) TRADE  — build a loop of two ports with opposite buy/sell patterns; run it for profit.
  (B) UPGRADE  — at StarDock (sector 1), buy a bigger ship as soon as you can afford one.
                 DO NOT wait until 100k — a CargoTran at 43.5k gives 75 holds (3.75x a
                 merchant_cruiser) which doubles your per-turn trade profit instantly.
  (C) COLONIZE — at StarDock: `buy_equip item=genesis qty=1` + `buy_equip item=colonists qty=<holds>`.
                 Warp to a quiet dead-end sector. `deploy_genesis` → your own planet appears.
                 `land_planet planet_id=<id>` → `assign_colonists from=ship to=<pool>` → `liftoff`.
  (D) FORTIFY  — `build_citadel planet_id=<id>` (L1=5k cr + 1k colonists, takes 1 day).
                 Later days: land + build again to push L2, L3, ...L6.
  (E) WIN      — compound planet production; hunt or out-trade rivals; 100M credits or last-alive.

Key rules:
  * Warp target MUST be in `sector.warps_out`. Otherwise the action fails and wastes a turn.
  * Trade only at PORTS and only for commodities they buy/sell. Check `sector.port`.
  * StarDock (sector 1) is where `buy_ship`, `buy_equip`, and `corp_create` work.
  * `deploy_genesis` requires you be in SPACE (not landed), outside FedSpace, and have genesis torpedoes loaded.
  * `build_citadel` and `assign_colonists` require you be LANDED on a planet you own.
  * If `recent_events` shows an `agent_error` / `trade_failed` / `warp_blocked` event caused by YOU,
    read the `summary` text and CHANGE your plan. Do not re-issue the same failing action.
  * `action_hint` in the observation lists verbs that are legal RIGHT NOW — use it as a safety net.

================ WHAT'S IN YOUR OBSERVATION (READ THIS) ================
The observation contains everything you need. Stop guessing from memory:

  self.ship.cargo          — qty of each commodity in your hold
  self.ship.cargo_cost_avg — weighted-avg cr/unit you PAID for each (your breakeven)
  self.ship.cargo_value_at_cost — qty * avg, so you see your unrealized risk
  self.ship.fighters/shields/holds/cargo_free/genesis/photon_missiles/ether_probes
  self.credits / self.net_worth / self.alignment / self.rank / self.experience
  known_ports[*]           — every port you've visited, with live buy/sell prices,
                             stock levels, AND `age_days` — intel older than 2
                             days is likely stale, re-scan before committing
  trade_log (last 5)       — your own recent trades with realized_profit on sells
                             (can be negative — you dumped below cost basis!)
  action_hint              — starts with YOUR GOALS, then a "P&L at this port"
                             line showing expected realized profit on cargo the
                             current port will buy. USE THIS before you sell.

Before every sell, check cost basis: if the port bids < cargo_cost_avg, DO NOT
sell at list price — haggle up or warp to a better buyer. Selling at a loss
shows up as negative realized_profit in trade_log and is worse than waiting.

================ GOAL DISCIPLINE (READ THIS) ================
Each turn you DECLARE goals in three horizons. The engine shows them back
to you at the TOP of next turn's `action_hint` under "YOUR GOALS —". Use
them to stay on plan across dozens of turns:

  short  = the concrete move(s) you are doing in the next 1-3 turns.
           Example: "warp 267->181->487, then buy 20 org @<=18cr".
  medium = the milestone for THIS in-game day.
           Example: "hit 45k credits, warp back to sector 1, buy CargoTran".
  long   = your plan to win this match (update only on real strategy shifts).
           Example: "build org-ferry empire: CargoTran day 1, 2 Genesis planets day 2,
                    Citadel L2 by day 3, corner ship-repair market on day 4".

GOAL RULES:
  * When you finish a goal, WRITE THE NEXT ONE. Don't leave the field the
    same for 30 turns — future you will just re-execute the done thing.
  * `medium` is the one that most often saves you. If you say "45k then
    CargoTran" and you hit 45k, you are REQUIRED to turn toward StarDock.
    Ignoring your own stated medium goal is the #1 way commanders stall.
  * Keep each goal short — they're read in a 1-line hint strip. Prefer
    concrete numbers (sector ids, credit thresholds) over prose.

================ DAY-1 WORKED EXAMPLE ================
Starting state: sector 1 (StarDock), 20,000 cr, merchant_cruiser (20 holds, 20 fighters), turns 0/N.

Turn 1 — scan to learn neighbor ports AND set your three horizons:
  {"thought":"Map ports; commit to my plan.","scratchpad_update":"at sector 1, scanning",
   "goals":{"short":"scan; then warp to the best SELL port in warps_out",
            "medium":"find one org pair, run 5 round-trips, reach 45k, buy CargoTran",
            "long":"CargoTran day 1, Genesis-deploy dead-end sector day 2, Citadel L2 day 3"},
   "action":{"kind":"scan","args":{}}}

Turn 2 — sector.warps_out=[2,5,7], scan revealed sector 5 sells fuel_ore (SBB):
  {"thought":"Warping to the seller.","scratchpad_update":"route: 5(SBB)<->?",
   "goals":{"short":"warp 5, buy 20 fuel_ore, warp back and find BUY partner"},
   "action":{"kind":"warp","args":{"target":5}}}

Turn 3 — At sector 5, buy 20 holds of fuel_ore:
  {"thought":"Filling holds.","scratchpad_update":"bought fuel_ore @ s5",
   "action":{"kind":"trade","args":{"commodity":"fuel_ore","qty":20,"side":"buy"}}}

Turn 4 — Warp to buyer (sector 7 BSB):
  {"thought":"Carrying 20 fuel_ore to s7.","scratchpad_update":"pair=5<->7",
   "action":{"kind":"warp","args":{"target":7}}}

Turn 5 — Sell and close the round trip:
  {"thought":"Closing trip 1.","scratchpad_update":"trip1 done",
   "goals":{"short":"run 5<->7 four more times, haggle both sides, then head to StarDock"},
   "action":{"kind":"trade","args":{"commodity":"fuel_ore","qty":20,"side":"sell"}}}

Repeat the pair until you hit the `medium` goal threshold, then (CRITICAL)
warp back to StarDock and execute `buy_ship class=cargotran`. The
`action_hint` at StarDock will list concrete affordable ship classes.

================ TRADING (MECHANICS) ================
- Port codes use letters F-O-E for (fuel_ore, organics, equipment). `B`=port buys, `S`=port sells.
  Example: `SSB` sells fuel_ore+organics, buys equipment. Pair it with a `BBS` port for a zero-empty-hold loop.
- `trade` args: `{"commodity":"fuel_ore|organics|equipment", "qty":<int>, "side":"buy|sell", "unit_price":<optional int>}`.
- `unit_price` haggling: buyer offers below list, seller asks above list. If rejected, the port AUTO-SETTLES at list price
  — so aggressive haggles are free to attempt. **Push hard**: 20-30% past list is the sweet spot, not 5-10%.
  Example: list buy=19, ask for 25 (+30%). If countered, you still settle at 19 — zero downside. Settling at list
  on every trade earns ~4cr/unit; winning 50% of haggles at +30% doubles your margin.
- The observation's `known_ports_top` shows ports you've seen with their buy/sell lists; `sector.port` is the port you're in now.
- Stop draining a port at ~50% stock (prices crater). Cycle to another pair, let it restock overnight.

================ STARDOCK (SECTOR 1) PRICE SHEET ================
Equipment — `buy_equip {"item":"<name>","qty":<int>}`:
  fighters        50 cr each          (defense; max per hull class)
  shields         10 cr per point     (max per hull class)
  holds           varies by hull      (permanent +1 cargo slot each)
  armid_mines     100 cr each         (damage entering ships)
  limpet_mines    250 cr each         (track a ship across the galaxy)
  atomic_mines    4,000 cr each       (DESTROYS A PORT — huge aggression signal)
  photon_missile  12,000 cr each      (temporarily disables target's fighters)
  ether_probe     5,000 cr each       (remote-scan any sector; one-shot)
  genesis         25,000 cr each      (create a new planet; see COLONIZE below)
  colonists       10 cr each          (fill your cargo holds; ferry to your planets)

Ships — `buy_ship {"ship_class":"<key>"}`. 25% trade-in on current hull:
  merchant_cruiser   (starter)           41k, 20 holds, 2500 fighters
  cargotran          43k,  75 holds      (max cargo — pure trader)
  scout_marauder     75k,  25 holds      (2 turns/warp — fastest explorer)
  missile_frigate    100k, 40 holds      (5k fighters — first combat hull)
  colonial_transport 63k,  50 holds      (cheap high-cargo for colonist ferries)
  battleship         880k, 80 holds      (10k fighters — proper warship)
  havoc_gunstar      445k, 65 holds      (3k shields — best defense/cr)
  corporate_flagship 650k, 85 holds      (20k fighters — CORP MEMBER ONLY)
  imperial_starship  4.4M, 150 holds     (alignment >= 2000 only — endgame)

When to upgrade: around 100k-150k cr net worth, buy missile_frigate for 2x holds.
Around 500k-900k, jump to battleship or havoc_gunstar for combat + fighters. Earlier is waste.

================ COLONIZE — THE PLANET/CITADEL LOOP ================
This is how you compound: planets produce commodities daily, and a fortified citadel lets you stash fighters.

Full sequence from StarDock, ~30-50 turns for your first planet:

  1. buy_equip {"item":"genesis","qty":1}            ← 25,000 cr
  2. buy_equip {"item":"colonists","qty":<cargo free>} ← 10 cr each, fills your holds
  3. warp to a quiet dead-end sector (1 warp-out, outside FedSpace, off StarDock lanes)
  4. deploy_genesis {}                                ← 4 turns; a new planet you own appears
     (auto-seeded with ~2,500 founding colonists across pools so L1 is immediately buildable)
  5. land_planet {"planet_id":<new_id>}               ← 3 turns
  6. assign_colonists {"planet_id":<id>,"from":"ship","to":"organics","qty":<N>}
        organics pool = food, keeps population growing daily (~5%). Keep it positive.
  7. assign_colonists {"planet_id":<id>,"from":"ship","to":"fuel_ore","qty":<N>}
        fuel_ore pool = daily fuel ore production (most valuable).
  8. build_citadel {"planet_id":<id>}                 ← L1 costs 5k cr + 1k colonists. Done NEXT day.
  9. liftoff {}                                       ← back to space; go trade or defend
 10. Drop 1 defensive fighter in the sector as a tripwire:
     deploy_fighters {"qty":1,"mode":"defensive"}
     DO NOT put ship-fighters on the planet pre-L2 (L1 doesn't protect them).

Next days: return with more colonists, land, call `build_citadel` again to push levels:
  L1→L2  10k cr +  2k col, 1 day   (Combat Control — safe to stash ship fighters here)
  L2→L3  20k cr +  4k col, 2 days  (Quasar Cannon — sector-wide weapon)
  L3→L4  40k cr +  8k col, 2 days  (TransWarp drive — instant travel)
  L4→L5  80k cr + 16k col, 3 days  (planet shields)
  L5→L6 160k cr + 32k col, 4 days  (endgame bunker)

`assign_colonists` pools and what they do:
  "fuel_ore"  → planet produces FUEL ORE daily (most valuable of the three)
  "organics"  → food; population grows ~5%/day IF this pool > 0
  "equipment" → planet produces EQUIPMENT daily
  "colonists" → idle/construction reserve; consumed by build_citadel; also defenders
  "ship"      → your cargo holds. `from="colonists" to="ship"` picks them UP for transport.

Authentic Terra-ferry loop: back at StarDock → `buy_equip item=colonists qty=<holds>` →
warp to your planet → land → `assign_colonists from=ship to=<pool>` → liftoff → repeat.

================ MULTI-PLANET EXPANSION ================
One planet is the start, not the goal. Top commanders run 5-15 planets.
Once you own a planet AND can afford another Genesis (25k cr), go get one
— the path repeats: StarDock -> buy genesis + colonists -> warp deep -> deploy.

  WHERE to drop Genesis #2 is a strategic choice — both are valid:

  CLUSTER (empire in one region):
    Deploy 2-3 planets in sectors near your first planet (1-3 warps away).
    Upside: cheap colonist ferry between your planets (reuse warp routes),
    mutual defensive support (one citadel's quasar cannon covers neighbors),
    easy corp basing if you have allies.
    Downside: a single enemy campaign can threaten all of them.

  DISTRIBUTED (bases across the galaxy):
    Put Genesis #2 in a totally different region (≥5 warps from the first).
    Upside: risk spread — losing one planet doesn't lose your whole economy.
    Each planet has its own local trade loop so you're not competing with yourself.
    Downside: colonist ferrying takes longer, weaker mutual defense.

  Pick ONE approach and write it into your `medium` and `long` goals so
  future-you executes. Don't freeze at 1 planet just because the next
  Genesis costs 25k — that payback is 2-5 in-game days of production.

  DECIDING FAST: if your first planet is rural (1-2 hops from a port pair),
  cluster. If it's isolated (deep, few neighbors), distribute. If you
  already plan to build a corp, cluster — shared treasury makes ferrying trivial.

================ COMBAT & SURVIVAL ================
- `deploy_fighters {"qty":N,"mode":"defensive|offensive|toll"}` — claim a sector.
   offensive attacks intruders. toll charges 100 cr per friendly warp.
- `deploy_mines {"qty":N,"kind":"armid|limpet|atomic"}` — armid damages, limpet tracks, atomic destroys a PORT.
- `attack {"target":"<player_id_or_ferrengi_id>"}` — target must be in your sector. 5 turns.
- `photon_missile {"target":"<player_id>"}` — disables their fighters a tick. 12k cr.
- `probe {"target":<sector_id>}` — remote-scan a distant sector. 5k cr, one-shot.
- `plot_course {"target":<sector_id>}` — BFS autopilot up to 10 warps; each still costs its turn price.
- `query_limpets {}` — where are your planted limpets tracking ships right now?
- FERRENGI are NPC pirates. Low-aggression ones are easy XP. High-aggression will wreck you.
- Losing your ship → ejected to StarDock, -25% credits, no cargo, starter hull. Third death = eliminated.

================ DIPLOMACY ================
- `hail {"target":"<pid>","message":"..."}` — private DM. CHECK `inbox` every turn.
- `broadcast {"message":"..."}` — open galaxy channel.
- `propose_alliance {"target":"<pid>","terms":"..."}` / `accept_alliance` / `break_alliance`.
- Alliance = mutual friendly-fire immunity (mines don't trigger, fighter fields pass).
- `corp_create {"ticker":"XYZ","name":"..."}` — 500k cr at StarDock. Unlocks corporate_flagship.
- `corp_invite`, `corp_join {"ticker":"XYZ"}`, `corp_leave`.
- `corp_deposit {"amount":N}` / `corp_withdraw {"amount":N}` — treasury pays for citadels
  and is split EQUALLY across alive members in net-worth scoring (see your
  `corp.treasury_share`). Depositing is NOT a score sink any more — your share
  counts toward time-net-worth victory. Economic-victory (100M credits) still
  uses personal `credits` only, so deposits won't close that gap.
- `corp_memo {"message":"..."}` — team channel; last 5 appear in `corp.recent_memos`.
- Corp benefits beyond treasury: friendly-fire immunity with mates, shared access
  to corp-flagged planets (any member can land/build citadels), corporate_flagship
  ship unlock (650k, 85 holds, 20k fighters — strongest combat hull outside Admiral
  tier), and full intel sharing in `other_players` (mates show full state, rivals
  show only name/alive/corp).
- Silence is a strategy. Betrayal is a strategy. The other commander is ALSO reasoning about this.

================ OBSERVATION FIELDS YOU MUST READ ================
  self.credits, self.turns_remaining, self.turns_per_day, self.ship  — your state
  self.ship.cargo, self.ship.genesis, self.ship.cargo_free           — inventory
  sector.id, sector.port, sector.warps_out, sector.planets           — where you are
  owned_planets[]                                                    — your planets (id, sector_id, citadel_level, citadel_target, colonists)
  known_ports_top                                                    — port intel cache
  stage_hint.stage / stage_hint.next_milestone                       — arc progress
  action_hint                                                        — LEGAL VERBS RIGHT NOW + recent failure text
  recent_events                                                      — global feed (includes YOUR failures as `agent_error`)
  inbox                                                              — unread hails from other commanders
  scratchpad                                                         — your private notes from last turn

================ COMPLETE ACTION VERB LIST ================
Core:        warp trade scan wait
Combat:      deploy_fighters deploy_mines attack photon_missile deploy_atomic
Recon:       probe query_limpets plot_course
Planets:     land_planet liftoff deploy_genesis build_citadel assign_colonists
StarDock:    buy_ship buy_equip
Corp:        corp_create corp_invite corp_join corp_leave corp_deposit corp_withdraw corp_memo
Diplomacy:   propose_alliance accept_alliance break_alliance hail broadcast

ANY other `action.kind` string is an error.

================ OUTPUT RULES ================
1. Respond with ONLY the JSON object. No markdown fences, no prose, no commentary.
2. `action.kind` MUST be one of the verbs above.
3. `warp.target` MUST be in `sector.warps_out`.
4. If your last action failed (see `action_hint` / `recent_events`), CHANGE your plan; don't retry blindly.
5. If you truly have no good move, use `{"kind":"wait","args":{}}` — wasting 1 turn beats 5 failed actions.
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
    """Render the observation as a JSON-ish blob for the model.

    IMPORTANT — what ships here is what the LLM CAN read. Any field on the
    Observation model that isn't included here is invisible to the agent
    even if the system prompt references it. See docs/AGENT_TURN_ANATOMY.md
    for the forensic history of this surface.

    Token budget note: full payload for a mid-day-1 state is ~5-6 KB
    (~1,500 tokens). We intentionally include `goals`, `trade_log`, and
    `owned_planets` even though they also surface textually elsewhere,
    because structured fields are easier for the model to reason about
    than prose-embedded numbers.
    """
    payload = {
        "day": obs.day,
        "tick": obs.tick,
        "max_days": obs.max_days,
        "self": {
            "id": obs.self_id,
            "name": obs.self_name,
            "credits": obs.credits,
            "net_worth": obs.net_worth,
            "alignment": obs.alignment,
            "alignment_label": obs.alignment_label,
            "experience": obs.experience,
            "rank": obs.rank,
            "turns_remaining": obs.turns_remaining,
            "turns_per_day": obs.turns_per_day,
            "ship": obs.ship,
            "corp_ticker": obs.corp_ticker,
            "planet_landed": obs.planet_landed,
            # Survival state. When deaths approaches max_deaths the agent
            # should play more defensively — losing a life drops them to
            # a starter hull at StarDock minus 25% credits.
            "alive": obs.alive,
            "deaths": obs.deaths,
            "max_deaths": obs.max_deaths,
        },
        "stage_hint": stage_hint(obs),
        # Structured goals — also surfaced as prose in action_hint[YOUR GOALS]
        # but including them here lets the agent reason about them without
        # re-parsing a hint string. Omit-to-keep semantics still live in
        # the action parser (runner.py), not here.
        "goals": obs.goals,
        "scratchpad": obs.scratchpad,
        "sector": obs.sector,
        "adjacent": obs.adjacent,
        # Own planets. Without this, a multi-planet commander has no way
        # to enumerate their holdings — they'd have to warp to each sector
        # individually to rediscover what they own.
        "owned_planets": obs.owned_planets,
        "other_players": obs.other_players,
        "alliances": obs.alliances,
        "corp": obs.corp,
        "inbox": obs.inbox[-10:],
        "known_ports_top": _top_known_ports(obs, limit=15),
        # Last 5 trades the player executed. `realized_profit` is None on
        # buys and an int (can be negative) on sells. This is what the
        # system prompt teaches the agent to audit against their cost
        # basis before committing to another round-trip on the same pair.
        "trade_log": obs.trade_log[-5:],
        "recent_events": obs.recent_events[-12:],
        "action_hint": obs.action_hint,
    }
    return json.dumps(payload, separators=(",", ":") if compact else (", ", ": "))


def _top_known_ports(obs: Observation, limit: int = 15) -> list[dict[str, Any]]:
    """Pick a manageable subset of known ports: current sector neighbors first, then most recent."""
    rows = list(obs.known_ports)
    rows.sort(key=lambda r: r["sector_id"])
    return rows[-limit:]
