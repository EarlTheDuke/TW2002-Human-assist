# TW2K-AI — Game Design Specification

This document is the authoritative spec for the game engine. It reflects the mechanics of the original **TradeWars 2002 v3.x** as closely as practical for an AI-driven match. Values are tunable via `config.py` but defaults match the classic game.

---

## 1. The Universe

| Property | Default |
|---|---|
| Sectors | 1000 |
| Warps per sector | 1–6 (avg ~2.5) |
| Warps are directed? | Yes (most are two-way, ~15% are one-way) |
| Deterministic generation | Yes, from a seed |

### 1.1 Sector IDs
Sectors are numbered 1..1000. Sector 1 is the **Federation Command Center**; sector 1–10 is **FedSpace** (no PvP combat allowed; Federation police will destroy aggressors).

### 1.2 Fixed landmarks
- **Sector 1** — The Federation HQ (StarDock's location in classic TW; we keep StarDock here for reachability).
- **StarDock** — Sits in sector 1. Sells ship upgrades, ships, equipment, and genesis torpedoes.
- **Class 0 (Federal) ports** appear in FedSpace and sell basic gear at fixed prices.

### 1.3 Universe generation algorithm
1. Seed RNG with `seed`.
2. Create 1000 sector records.
3. Build a connected graph: start with a spanning tree guaranteeing all sectors reachable from 1. Then add extra edges to hit target average warps/sector.
4. Randomly convert ~15% of edges to one-way.
5. Place ports in ~65% of sectors, with class distribution:
   - Class 1 (BBS) — Sells Organics & Equipment, Buys Fuel Ore — ~8%
   - Class 2 (BSB) — Sells Fuel Ore & Equipment, Buys Organics — ~8%
   - Class 3 (SBB) — Sells Fuel Ore & Organics, Buys Equipment — ~8%
   - Class 4 (SSB) — Sells Equipment, Buys Fuel Ore & Organics — ~8%
   - Class 5 (SBS) — Sells Organics, Buys Fuel Ore & Equipment — ~8%
   - Class 6 (BSS) — Sells Fuel Ore, Buys Organics & Equipment — ~8%
   - Class 7 (BBB) — Buys all three (rare, high-value evacuation point) — ~2%
   - Class 8 (Special) — StarDock — fixed in sector 1
   - Class 0 (Federal) — in FedSpace only — limited
6. Optionally scatter Ferrengi home sectors deep in the universe.

> **Port code mnemonic:** letters are in order **Fuel Ore, Organics, Equipment**. `B` = Buys, `S` = Sells. So **BSS** Buys Fuel Ore, Sells Organics, Sells Equipment.

---

## 2. Commodities & Economy

Three commodities:

| Commodity | Symbol | Base Price | Hold size |
|---|---|---|---|
| Fuel Ore | F | 18 cr | 1 per hold |
| Organics | O | 25 cr | 1 per hold |
| Equipment | E | 36 cr | 1 per hold |

Every hold carries 1 unit of one commodity (or 1 colonist, or empty).

### 2.1 Port dynamics
Each port has, per commodity it deals in:
- `max_product` — how many units at full stock.
- `current_product` — current inventory (0..max).
- `regeneration_rate` — % per game day the stock refills (default 5%/day toward max).

Prices float based on stock level:
- **Selling to player (port has this product):** price = `base * (0.90 + 0.20 * (current / max))`. Low stock = cheap for port, so it discounts; high stock = it asks closer to base. (Classic TW inverts this subtly; we use the "players profit more when port is well-stocked of what it sells" rule.)
- **Buying from player (port wants this product):** price = `base * (1.20 - 0.30 * (current / max))`. Low inventory = port desperate = pays more.

### 2.2 Haggling
Each trade involves negotiation over 1–5 rounds:
- Port opens with its computed price.
- Player counter-offers. Each offer further than `~5%` from port's price reduces success probability.
- Accepted offer executes; rejected trade wastes a turn but no penalty.
- Agents get a simplified "one-shot haggle": propose a fraction `k ∈ [0.85, 1.15]` of the listed price; success probability = `clamp(1 - 2*|k - fair_k|, 0, 1)` where `fair_k` drifts slightly per port based on its `experience` toward that player.

### 2.3 Port classes quick reference

| Class | Code | Fuel Ore | Organics | Equipment |
|---|---|---|---|---|
| 1 | BSS | Buys | Sells | Sells |
| 2 | BSB | Buys | Sells | Buys |
| 3 | SBB | Sells | Buys | Buys |
| 4 | SSB | Sells | Sells | Buys |
| 5 | SBS | Sells | Buys | Sells |
| 6 | BBS | Buys | Buys | Sells |
| 7 | BBB | Buys | Buys | Buys |
| 8 | SSS | StarDock (services) |
| 0 | ... | Federal (fixed price, limited stock) |

> Naming note: we use the classic 3-letter code in order F-O-E. The original game also uses class numbers (1..8) as shorthand in prompts.

---

## 3. Turns & Time

- Each player has a daily **turn allowance** (default **20,000** for a long campaign; we use **1,000 turns/day** and compress "days" by 30× for AI matches).
- Each action spends turns:

| Action | Turn cost |
|---|---|
| Warp move | 2 |
| Trade at port (per transaction) | 3 |
| Attack another ship | 5 |
| Deploy fighters / mines | 1 |
| Land on planet | 3 |
| Liftoff | 1 |
| Scan sector | 1 |
| Transmit message | 0 |
| Hyperwarp (Imperial StarShip) | 5 per jump |

- A **game day** ticks when all active agents consume their daily allowance OR a configurable wall-clock interval passes (default: 30 seconds per day in AI matches).
- Port stocks regenerate on day-tick.
- Ferrengi may spawn on day-tick.

---

## 4. Ships

| Class | Cost | Holds | Fighters | Shields | Turns/warp | MaxFreq | Notes |
|---|---|---|---|---|---|---|---|
| Merchant Cruiser | start | 20 | 2,500 | 400 | 3 | 1× | Starter ship |
| Scout Marauder | 75k | 25 | 250 | 100 | 2 | 1.25× | Fast, fragile |
| Missile Frigate | 100k | 40 | 5,000 | 400 | 3 | 1× | Balanced |
| BattleShip | 880k | 80 | 10,000 | 400 | 3 | 1× | Heavy hitter |
| Corporate Flagship | 650k | 85 | 20,000 | 1,500 | 3 | 1× | Corp-only |
| Colonial Transport | 63k | 50 | 200 | 100 | 3 | 1× | Carries 2,500 colonists |
| CargoTran | 43k | 75 | 400 | 100 | 3 | 1× | Big cargo |
| Merchant Freighter | 350k | 65 | 2,500 | 750 | 3 | 1× | Trader upgrade |
| Imperial StarShip | 4.4M | 150 | 50,000 | 5,000 | 3 | 2× | Hyperdrive, rare, requires Alignment ≥ 2000 |
| Havoc Gunstar | 445k | 65 | 10,000 | 3,000 | 3 | 1× | Aggressive |

- Each ship has: `holds`, `fighters`, `shields`, `mines_onboard`, `genesis_torpedoes`, `turns_per_warp`, `ported` (special sensor systems), `ship_class`.
- Players own exactly one ship at a time; switching sells the old at 25% price.
- Only one **Imperial StarShip** may exist in the universe at once.

---

## 5. Combat

### 5.1 Ship vs Ship
When attacker chooses to engage defender in the same sector (or defender fleeing):
1. Attacker allocates `F_a` fighters + `S_a` shields; defender does likewise (or auto-defends with all).
2. Damage roll: each fighter does `damage = uniform(0.8, 1.2)` vs opposing fighters; shields absorb 1:1 up to their current level.
3. Resolution is simultaneous per "exchange" round; ~3 exchanges until one side flees or is destroyed.
4. Destroyed ship: pilot ejected (survives with penalty), ship lost, 25% of cargo jettisoned into sector.
5. Attacker gains **experience** based on difficulty; loser loses **alignment** if unjustified attack (attacking in FedSpace = −200 alignment & Federal response).

### 5.2 Fighters
- Deployed to a sector to claim it.
- **Defensive** — only fire if sector owner is attacked there.
- **Offensive** — fire at any non-ally entering the sector.
- **Toll** — charge 10 cr per ship passing through.
- Ownership markers: sectors show fighter count + owner in scanners.

### 5.3 Mines
- **Armid Mines** — trigger on enemy entry, 100 damage each, 1–10 can hit per move.
- **Limpet Mines** — attach silently; reveal target location to owner for 7 days.
- Detonated mines are consumed.

### 5.4 Genesis Torpedoes
Convert an empty sector into a **new planet** of a chosen class (M, K, L, O, H, U, C). 25,000 cr each from StarDock.

### 5.5 Ferrengi (NPC pirates)
- Spawn in random deep sectors (outside FedSpace) on day-tick; population scales with universe age.
- Aggression 1–10 (rookies to veterans).
- If a Ferrengi is in your sector, it attacks on its turn with probability `aggression/10`.
- Destroying a Ferrengi: bounty = `1000 * aggression` cr, +10 alignment.
- Ferrengi have Merchant Cruiser up to BattleShip class depending on aggression.

---

## 6. Planets

Created by Genesis Torpedoes or pre-existing in ~3% of sectors.

### 6.1 Planet classes
| Class | Name | FO prod | Org prod | Eq prod | Citadel max |
|---|---|---|---|---|---|
| M | Earth-type | moderate | high | moderate | 6 |
| K | Desert | high | low | low | 5 |
| L | Mountainous | high | moderate | low | 5 |
| O | Oceanic | low | high | moderate | 5 |
| H | Volcanic | very high | none | low | 4 |
| U | Gaseous | low | low | high | 4 |
| C | Glacial/Crystal | low | moderate | high | 5 |

### 6.2 Colonists
- Each colonist produces 1 "population-hour" of labor per game day.
- Citizens are assigned to one of three work types: **Fuel Ore**, **Organics**, **Equipment**.
- Output per day = `colonists_on_job * class_coefficient * citadel_bonus`.
- Population growth: `+5%/day` if enough food (Organics) in stockpile, else stagnation or decline.

### 6.3 Citadels
Constructed in stages 1–6; each stage costs cumulative resources and unlocks:
- Level 1: planetary treasury
- Level 2: military command — defensive fighters
- Level 3: quasar cannon — sector defense
- Level 4: planetary shields
- Level 5: transwarp drive — jump your ship to the planet from anywhere
- Level 6: interdictor generator — prevent enemy warp-out

### 6.4 Planet ownership
- Owner is the player who lands first on an unowned planet.
- Owner may designate allies (corp members) with access.
- Capturing: assault an enemy citadel; requires ground forces (not modeled in Phase 1 — treat as fighter siege).

---

## 7. Corporations & Alliances

Two or more players may form a **corporation** (max 8 members classic; we default max **2** for a 2-agent match, configurable).

### 7.1 Effects
- Corp members can't attack each other.
- Shared planet access & shared fighter ownership (optional per-sector).
- Shared corporate bank account.
- Shared intel: all corp members see each other's last known sector and ship.
- Corporate flagship ownership allowed.

### 7.2 Formation / dissolution
- Player creates corp at StarDock, pays 500k cr, picks a 3-letter **corp ticker**.
- Invites other players; they accept via StarDock.
- Members may defect with 1 game day of notice; 50% of their corp-assets forfeited.
- Corp may be **dissolved** by CEO; assets split 50/50 by contribution.

### 7.3 Diplomacy / messaging
- Global **subspace radio** — broadcast to all.
- Private **hail** — direct message to specific player.
- **Federation comm channel** — always in-FedSpace.
- Messages logged and visible in spectator UI.

Agents use this for negotiation: alliance proposals, trade deals, threats, bluffs.

---

## 8. Winning

A match ends when **any** of the following triggers:

1. **Domination** — one player/corp owns ≥ 50% of populated sectors (sectors with fighters or planets under their control).
2. **Economic victory** — one player/corp accumulates 100M cr liquid + assets.
3. **Elimination** — only one non-bankrupt player remains active.
4. **Turn limit** — after N game days (default 30), highest net worth wins.

Net worth = liquid cr + ship value + cargo value + deployed fighters (50 cr each) + planet valuations.

---

## 9. Agent interface (contract with engine)

See `ARCHITECTURE.md` for the action schema. Summary of allowed actions:

- `WARP <sector>` — move
- `TRADE <commodity> <qty> <price>` — trade at current port
- `DEPLOY_FIGHTERS <qty> <mode>` — in current sector
- `DEPLOY_MINES <type> <qty>`
- `ATTACK <player_id>` — if same sector
- `LAND_PLANET <id>` / `LIFTOFF`
- `ASSIGN_COLONISTS <job> <qty>`
- `BUILD_CITADEL <level>`
- `BUY_SHIP <class>` / `BUY_EQUIP <item> <qty>`
- `CORP_CREATE <ticker>` / `CORP_INVITE <player>` / `CORP_JOIN <ticker>` / `CORP_LEAVE`
- `HAIL <player> <message>` / `BROADCAST <message>`
- `SCAN` / `WAIT`

The engine validates every action and returns a state diff + new observation.
