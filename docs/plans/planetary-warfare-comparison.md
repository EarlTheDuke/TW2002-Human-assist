# Planetary Defense and Late-Game Planetary Warfare: Original Trade Wars 2002 vs TW2K (our engine)

Date: 2026-10-01 (PT). Prepared for Ben.
Part 2 was read-only. Branch `feature/grokbot-player`, HEAD `c31e1f9`. Nothing was run, edited or committed in the worktree.

## 0. How to read this report

Confidence tags used throughout:

- **[CONFIRMED]** Stated in a fetched source I read, or read directly in our code.
- **[SOURCE-CONFLICT]** Fetched sources disagree with each other.
- **[UNVERIFIED]** Recollection, inference, or something I could not find a source for.
- **[CODE-READ ONLY]** I read the code but did not run it, so runtime behavior is not confirmed.

The original game is known to be hard to pin down because several variants exist:

- **v1.x (1991)**, with early guides such as "The TradeWars 2002 Bible" (1993, for v1).
- **v2 betas (1993-96)** and the MBBS ports (HVS, 1994-97).
- **v3.x** (DOS multi-player; TWGS 2.x and 3.x servers from EIS/John Pritchett, 1998 on).

The best modern references (Planet Handbook v1.01, Cabal "Formulas") describe **TWGS 3.11.x**, "Gold ON/OFF", and the **MBBS** modes. They flag where TWGS and MBBS differ. The Break Into Chat wiki says the latest TWGS is v2.20b (2012). The Planet Handbook calls the latest "3.11.55, Feb 14 2002". These version numbers do not line up cleanly and I did not resolve that.

Note: the brief says "EIS / John Morris". The sources I read credit **Gary Martin (Martech)** as the author and **John Pritchett (EIS)** for TWGS. I am using those names.

### Source list (all fetched during this job)

- [S1] Planet Handbook v1.01 by Paladyne, mirrored at https://www.thestardock.com/files/Site%20Caps/TWCabal/planets.html (also http://www.swath.net/?page=planethandbook%2Fchapter5, chapter7).
- [S2] Cabal "Formulas" page: https://www.thestardock.com/files/Site%20Caps/TWCabal/formulas.html (also https://tw-cabal.navhaz.com/formulas.html; the navhaz URL timed out when I fetched it directly, but search snippets match).
- [S3] "TradeWars 2002 Bible" by Psycho, 1993, v1: https://www.thestardock.com/files/manuals/Trade_Wars_2002_Bible.htm (updated 2007 by Clme, with bracketed commentary). I downloaded and read it.
- [S4] Break Into Chat wiki: https://www.breakintochat.com/wiki/TradeWars_2002
- [S5] ATTAC "TW2002 revision" notes: http://www.tw-attac.com/tw2002revision.html (a snippet only, with an unclear version; treat as TWGS-era).
- [S6] Wikipedia 2007 mirror: https://wikipedia2007.classicistranieri.com/en/t/r/a/TradeWars_2002_540a.html
- [S7] SOFTDOCS text file (original docs excerpt, via search snippet): https://textfiles.pc-freak.net/piracy/SOFTDOCS/slice-10.txt

I did not find the official EIS manual or TWGS doc text itself. The "official" position below rests on S1 and S2, which are community write-ups from the TWGS era.

---

## PART 1: The original game

### 1.1 Planet types and production [CONFIRMED, S1/S2]

Seven classes: M (Earth), K (Desert), O (Oceanic), L (Mountain), C (Glacial), H (Volcanic), U (Gas). Class U produces nothing. Class C is described as not recommended for colonization.

Optimal population and caps, from S2 "Optimal Population and Production" and S1:

| Class | Optimal pop (per product) | Max fuel on planet | Colonists to make 1 fighter (fuel / org / equip) |
|---|---|---|---|
| M | 15,000 | 100,000 | 30 / 70 / 130 |
| K | 20,000 | 200,000 | 30 / 1,500 / 7,500 |
| O | 100,000 | 100,000 | 300 / 30 / 1,500 |
| L | 20,000 | 200,000 | 24 / 60 / 240 |
| C | 50,000 | 20,000 | 1,250 / 2,500 / 12,500 |
| H | 50,000 (no organics) | 1,000,000 | 50 / n/a / 25,000 |
| U | 1,500 | 10,000 | no production |

Further confirmed facts:

- A planet holds at most 2x the optimal population (S2).
- Daily production follows a bell curve that peaks at 50% of maximum population (S1). Below 50% colonists multiply; above it they die off.
- S1 ratios per product ("FOE ratio", colonists per unit): M 3/7/13, K 2/100/500, O 20/2/100, L 2/5/20, C 50/100/500, H 1/-/500.
- Maximum fighters on a planet is 1,000,000 for every class (S1).
- **Fighters cannot be assigned directly.** They are a fraction of total daily FOE output (S1). Example in S1: 1,500 colonists on fuel on a Class M planet gives 500 fuel and 50 fighters per day. Adding 700 colonists on organics gives 500 fuel, 100 organics and 60 fighters per day.
- Class H planets are used for tunnel defense because they hold up to 1,000,000 fuel for the Quasar cannon (S1, S4).
- Genesis torpedoes create a new Level 0 planet with no defenses and usually no colonists or FOE (a Gold-edition setting) (S1).
- S4 and S1 say the GameOp can edit almost everything (citadel costs, times, maximums) with Gold extensions.

### 1.2 Citadel levels (cumulative)

Order and unlocks [CONFIRMED, S1; S4/S6 agree]:

| Level | Name / unlock |
|---|---|
| 0 | No defenses |
| 1 | Treasury (stores credits; 2% daily interest; max about 999,999,999,999,999; you can also park your ship in the citadel) |
| 2 | Combat Control Computer (planet fighters get offensive 2:1 / defensive 3:1 odds; "Military Reaction" percentage) |
| 3 | Quasar cannon (fuel ore powered; sector shot and atmospheric shot) |
| 4 | Planetary thrusters / TransWarp: moves the planet. Needs a fighter in the destination sector as a lock target. Costs 400 fuel ore per sector jumped. No blind warp. (S1) |
| 5 | Planetary shielding |
| 6 | Interdictor generator (blocks leaving the sector; 500 fuel ore per attempt) |

A GameOp cannot change the order (S1). The wiki (S6) labels L4 "TransWarp drive (moves planet)", consistent with S1.

**Planetary Transporter** [CONFIRMED, S1 section VI]. This is a separate purchase available once a citadel exists, not a numbered level.

- Cost: 50,000 credits for the first hop and 25,000 per additional hop, paid from the player, not the planet treasury.
- It carries the player and ship to any in-range sector where the player has a fighter to lock onto.
- Fuel: 10 ore per sector of the jump, charged from the planet. Turn cost: 1 turn regardless of distance.

**Construction cost** [CONFIRMED, three sources agree: S1 sec. VII, S2, S7]. Citadels are built from colonists plus fuel ore, organics and equipment. They cost no credits in the original. Per-level columns are L1..L6.

| Class | Colonists | Fuel ore | Organics | Equipment | Days | Total days |
|---|---|---|---|---|---|---|
| M | 1000, 2000, 4000, 6000, 6000, 6000 | 300, 200, 500, 1000, 300, 1000 | 200, 50, 250, 1200, 400, 1200 | 250, 250, 500, 1000, 1000, 2000 | 4, 4, 5, 10, 5, 15 | 43 |
| K | 1000, 2400, 4400, 7000, 8000, 7000 | 400, 300, 600, 700, 800, 700 | 300, 80, 400, 900, 400, 900 | 600, 400, 650, 800, 1000, 1600 | 6, 5, 8, 5, 4, 8 | 36 |
| O | 1400, 2400, 4400, 7000, 8000, 7000 | 500, 200, 600, 700, 300, 700 | 200, 50, 400, 900, 400, 900 | 400, 300, 650, 800, 1000, 1600 | 6, 5, 8, 5, 4, 8 | 36 |
| L | 400, 1400, 3600, 5600, 7000, 5600 | 150, 200, 600, 1000, 300, 1000 | 100, 50, 250, 1200, 400, 1200 | 150, 250, 700, 1000, 1000, 2000 | 2, 5, 5, 8, 5, 12 | 37 |
| C | 1000, 2400, 4400, 6600, 9000, 6600 | 400, 300, 600, 700, 300, 700 | 300, 80, 400, 900, 400, 900 | 600, 400, 650, 700, 1000, 1400 | 5, 5, 7, 5, 4, 8 | 34 |
| H | 800, 1600, 4400, 7000, 10000, 7000 | 500, 300, 1200, 2000, 3000, 2000 | 300, 100, 400, 2000, 1200, 2000 | 600, 400, 1500, 2500, 2000, 5000 | 4, 5, 8, 12, 5, 18 | 52 |
| U | 3000, 3000, 5000, 6000, 8000, 6000 | 1200, 300, 500, 500, 200, 500 | 400, 100, 500, 200, 200, 200 | 2500, 400, 2000, 600, 600, 1200 | 8, 4, 5, 5, 4, 8 | 34 |

Notes:

- The totals in S1 (for example M: 6,000 colonists, 3,300 fuel, 3,300 organics, 5,000 equipment) are what S1 labels "Totals". Some of those S1 totals, such as the K colonist total, do not match the sum of the per-level colonist figures, so I used the per-level rows.
- These tables are for Gold extensions OFF or unmodified (S1). The "Subzero" edit cited in S4 reaches L4 in a single day.

### 1.3 Planetary shields [CONFIRMED, S1; S2 for odds]

- 10 ship shields convert to 1 planetary shield. Removal is also in units of 10.
- The invader must defeat planetary shields at about **20:1 odds against him**, per S1, which describes this as "doubling the value placed in the generator". That wording is unclear. S2's MBBS odds table gives "Planet Shield Odds 20:1".
- 200 planetary shields protect the Quasar cannon from being dampened by a photon missile. They also save the ship's turns if you are on the planet (S1).
- Per S3 (v1 Bible), shields can be loaded before L5 but only become active when L5 completes.
- A shielded planet looks different to a holoscan. A planet scanner reveals owner and fighters only if the planet is **not** shielded (S3).

### 1.4 Planetary fighters [CONFIRMED, S1/S2/S3]

- Produced as a fraction of daily output (see 1.1). They are not purchased.
- **Odds:** 2:1 offensive and 3:1 defensive (S1, S2).
- **Military Reaction %** sets what share of planet fighters attack the arriving invader at 2:1 odds. The rest stay and defend at 3:1 odds (S1).
- In S2's order of events, offensive planet fighters **only attack when there are no shields left**.
- S2 says each offensive wave sends **1.25x the combined shields + fighters your ship can carry** (your maximum, not your current load) at 2:1. Example in S2: ship max 10,000 fighters and 1,000 shields gives 13,750 attackers. Leftover fighters stay on the planet.
- Remaining planet fighters defend at **3:1 odds, even if a Military Reaction was set** (S2).
- Per S3 (v1 Bible), do not leave fighters on a planet below L2, because anyone can land and take them.
- The planet scanner (S3) is an item that shows a non-shielded planet's owner and fighters.

### 1.5 Quasar cannons [CONFIRMED formulas; version differences flagged]

There are two cannons on a planet: a sector cannon and an atmospheric cannon. Each has a percentage setting of the planet's fuel ore.

- **Sector shot** [CONFIRMED, S1 and S2, same in TWGS and MBBS]: damage = fuel_on_planet x SectorPct / 3. Fuel used = fuel x SectorPct.
  - Example: 10,000 fuel at 10% uses 1,000 fuel and does 333 damage. A second shot uses 900 fuel and does 300 damage.
- **Atmospheric shot, MBBS** [CONFIRMED, S1 and S2 agree]: damage = fuel x AtmPct x 2, using fuel x AtmPct.
  - Example: 9,000 fuel at 10% uses 900 fuel and does 1,800 damage.
- **Atmospheric shot, TWGS** [SOURCE-CONFLICT]:
  - S1: 9,000 fuel at 10% does 900 damage and uses 450 fuel (damage = fuel x AtmPct, fuel used = half of that).
  - S2: damage = fuel x AtmPct x 0.5; the worked example gives 18,000 for 180,000 fuel at 20%. By S1 the same case would be 36,000.
  - The two sources differ by a factor of 2 in the TWGS atmospheric formula. I cannot tell which is right from the sources I read.
  - S1 adds that atmospheric can simply be set to twice the sector setting to get equivalent effect. Mode differences stem from keeping TWGS "true to the original" (S1).
- **Ammunition** is the planet's fuel ore. Class H planets hold up to 1,000,000 fuel.
- **Order of fire:** with several planets in a sector, the lowest planet number fires first; if the ship dies, the later cannons do not fire (S2).
- **Photon missile** dampens the Quasar so it does not fire (sector or atmospheric shots) when the planet is below L5 or has fewer than 200 shields (S1). Photon usage limits (Imperial StarShip or Missile Frigate; fired from an adjacent sector; "Photon Wave Duration" setting) are in the v1 Bible (S3).
- Quasar damage is independent of the target ship's size (S1: "fires based on the fuel available, not the size of your ship").
- The original has **no separate beam weapon** on planets in any source I read. I found no "planetary beam". Treat that as absent.

### 1.6 Interdictor and "moth" tactics [CONFIRMED, S1]

- The L6 interdictor stops the ship leaving; each attempt costs 500 planet fuel and the Quasar fires again at sector level.
- Below 500 fuel the interdiction fails and the ship escapes.
- Players "moth" a planet by entering and leaving repeatedly to drain its fuel (big moths with lots of shields/fighters, little moths cheap and disposable).
- S1 says "you can get podded twice per day and survive, but the third podding will destroy your ship and leave you out for the rest of the day".

### 1.7 How a hostile approach and landing resolve

From S1 ("Order of Events") and S2. Sector events first:

1. Nav hazards.
2. One limpet mine attaches (a previous one falls off).
3. Armid mines check for detonation. S2 (TWGS-era): when triggered, 50% of the mines detonate. S3 (v1): "half of them" blow up, 20 damage per mine. [Per-mine damage in later versions: UNVERIFIED.]
4. Sector Quasar fires (planet number order).
5. Sector fighters: offensive fighters attack at 1:1 (sending 1.25x your max ships' shields+fighters); defensive fighters challenge; tolled fighters demand 5 credits per fighter (S2).

Then atmospheric events:

6. Atmospheric Quasar fires.
7. Planet shields must be defeated at 20:1. After the last shield falls, the atmospheric Quasar fires again.
8. Military-reaction (offensive) fighters attack at 2:1.
9. Remaining fighters defend at 3:1.
10. You land. The ship takes ownership with "O" at the planet prompt (S2).

Photons can skip several steps (S1). With a photon and the planet under L5 or under 200 shields, armid mines, sector Quasar, sector fighters, the atmospheric Quasar and offensive planet fighters are all disabled. Shields and defensive planet fighters still apply. With L5 and 200+ shields only armid mines and sector fighters are skipped.

### 1.8 Ship loss, pods, and what you win

- A ship destroyed in combat sends the pilot to an escape pod (details differ by version; podding costs 10% of experience, a self-destruct costs 50% of experience and alignment) (S2). I did not find a hard cap of three deaths with permanent elimination in the original. Our engine has one (see Part 2).
- Capturing a planet means taking its colonists and products; the Bible calls the planet a prize and a target for theft (S3).
- **Planet destruction:**
  - Atomic Detonator (v1, S3): destroys a planet, costs 50 alignment points, max 5 carried, and you must first kill all colonists or the device destroys you.
  - S2 (TWGS-era table): destroying a planet is -1 alignment and +50 experience. [SOURCE-CONFLICT with S3 on alignment cost; different versions.]
  - Killing a trader sitting on a planet and blowing it up gives experience (enemy exp x 0.1666 + 50) (S2).
- **Genesis-overload trick (v1, S3):** fill an enemy sector with Genesis planets up to the limit (S3 says "usually 5 per sector"), then TransWarp an L4+ planet in. External maintenance can collide and destroy planets. [UNVERIFIED for TWGS 3.x.]
- No separate "planet attack limit per day" turned up in the sources. I did not find one. [UNVERIFIED]
- The only per-wave limit I found is the 1.25x ship-capacity cap on offensive waves (S2).

### 1.9 Ownership, corporations, and transfer

- A planet is taken after killing shields and fighters, then pressing "O" at the planet prompt (S2).
- Corporations share planets and citadels (S3, S4). A ship in a citadel can be left there overnight.
- When a corporation disbands, planets in the CEO's current sector become the CEO's; planets elsewhere become **Rogue** (S5 snippet, TWGS-era notes). [Version: uncertain.]
- Corp ships cannot be exchanged at a citadel in standard Trade Wars; Gold allows exchange between members (S5).
- The v1 Bible gives guild/corp advice about backstabbing CEOs and "bait" planets that you take back at key build points. [CONFIRMED text, strategic not mechanical.]
- Planet treasury: see 1.2 (L1).
- Alignment: S2 gives "Creating a Planet" +10/0/-10 alignment (good/neutral/evil) and +25 exp.

### 1.10 What I could not confirm for the original

- Exact TWGS atmospheric cannon constant (S1 vs S2 conflict).
- Exact odds arithmetic for the "20:1" shield rule (how shields convert into damage absorbed).
- Whether Military Reaction % is a free player setting or varies by version beyond what S1 says.
- Daily planet-attack limits and the exact number of planets allowed per sector (S3 says "usually 5", a v1-era statement).
- Per-mine damage in TWGS 3.x.
- Official EIS manual wording (I only read community write-ups).

---

## PART 2: Our engine (TW2K) as of branch `feature/grokbot-player`

All paths are under `src/tw2k/` unless noted. "L" = line number from my read.

### 2.1 Planets and ownership

- **Model:** `engine/models.py` class `Planet` (L310-339) has `id, sector_id, name, class_id, owner_id, corp_ticker, citadel_level, citadel_target, citadel_complete_day, colonists{fuel_ore,organics,equipment,colonists}, stockpile{fuel_ore,organics,equipment}, fighters, shields, treasury, last_tax_value, origin`.
- **Classes:** `PlanetClass` M, K, L, O, H, U, C (models.py L148-155).
- **Map-start planets:** `engine/universe.py::_seed_planets` (L374-389). Sectors above FedSpace (11+) each get a planet with probability `GameConfig.planet_spawn_probability = 0.03` (models.py L693). The class is uniform over the 7 (`rng.choice(list(PlanetClass))`). No colonists, no defenses.
- **Genesis:** `runner.py::_handle_deploy_genesis` (L1218-1297).
  - Needs `ship.genesis > 0`, not in FedSpace (`K.FEDSPACE_SECTORS` = sectors 1-10), at least `K.GENESIS_MIN_HOPS_FROM_STARDOCK = 3` hops from sector 1, and not landed.
  - Costs `K.GENESIS_DEPLOY_TURN_COST = 4` turns. The torpedo costs `K.GENESIS_TORPEDO_COST = 25_000` credits at StarDock.
  - Class is drawn with `K.PLANET_CLASS_WEIGHTS` (M .32, K .14, L .14, O .14, H .10, U .10, C .06).
  - The new planet is owned by the deployer and seeded with `K.GENESIS_SEED_COLONISTS = 2_500` (40% fuel, 25% organics, 15% equipment, rest idle) plus 25 organics. This differs from the original, where Genesis planets start empty.
  - No per-sector planet cap check was found. [CODE-READ ONLY]
- **Ownership by landing:** `_handle_land_planet` (L730-864). Landing on an unowned map-start planet claims it (`origin="claim"`). Landing on an orphan (former-player planet) does not; `claim_planet` is required (`_handle_claim_planet` L1300-1362, 2 turns, `PLANET_CLAIMED` event, +75 XP). Orphans come from player elimination (combat.py `_destroy_ship` L448-481, `PLANET_ORPHANED` event; only solo-owned, non-corp planets).
- **Corporations:** `Corporation` model (models.py L585-593). `CORP_FORMATION_COST = 500_000`, `CORP_MAX_MEMBERS_DEFAULT = 2`. Corp mates are allied for IFF (combat.py `_are_allied`). Corp-owned planets can be built and managed by any member (`_require_landed_owned_planet`, `_handle_build_citadel`, which can pay from the corp treasury). A corp planet cannot be claimed as an orphan (`_handle_claim_planet`). Leaving a corp (`_handle_corp_leave` L1591) does not touch planets. The planet keeps its `corp_ticker`, so after leaving, the player no longer matches it and loses management access, while the planet stays with the corp. [CODE-READ ONLY; untested.]

### 2.2 Citadels

Constants (`engine/constants.py` L204-213):

```
CITADEL_LEVELS = 6
CITADEL_TIER_COST (credits, colonists, days) =
 L1  5,000     1,000   1
 L2  10,000    2,000   1
 L3  20,000    4,000   2
 L4  40,000    8,000   2
 L5  80,000   16,000   3
 L6  160,000  32,000   4
```

Totals: 315,000 credits, 63,000 colonists, 13 days. This is the same for every planet class. It uses credits and colonists only; fuel, organics and equipment are not spent.

- **Build:** `_handle_build_citadel` (runner.py L1133-1215). Owner or corp member, landed, no build already pending, pay credits from the corp treasury if it has enough, else personal; drain colonists across all four pools in order; set `citadel_target` and `citadel_complete_day = day + days`. Emits `BUILD_CITADEL`. Turn cost is `TURN_COST["land_planet"]` (3), but it is waived if the player lacks turns.
- **Completion:** `planets.py::_complete_citadels` (L127-150) runs in `tick_day` (runner.py L158-182). It sets `citadel_level = citadel_target`, emits `CITADEL_COMPLETE`, awards XP (`XP_AWARDS["build_citadel_lvl"] = 50` x level).
- **Defense gift at completion (the only source of planet fighters/shields):**
  ```python
  if planet.citadel_level >= 2:
      planet.fighters = max(planet.fighters, 1000 * planet.citadel_level)
      planet.shields  = max(planet.shields,  250  * planet.citadel_level)
  ```
  So the garrison floor by level is:

  | Level | Fighters | Shields |
  |---|---|---|
  | L2 | 2,000 | 500 |
  | L3 | 3,000 | 750 |
  | L4 | 4,000 | 1,000 |
  | L5 | 5,000 | 1,250 |
  | L6 | 6,000 | 1,500 |

  Because of `max(...)`, a planet that was damaged and then completes a new level gets topped back up to the floor.
- **What each level does in the engine:** The only level-dependent behavior I found is the level >= 2 garrison gift above, plus net worth (see 2.7), XP, and atomic-mine reduction. I found **no** engine code for treasury deposit/withdraw, military reaction, quasar cannon, planet TransWarp, planetary transporter, shield generator control, or interdictor. Grepping `src/` for quasar, beam, interdict and transwarp finds only prompt/UI text. L1 gives no effect.
- **Docs disagree about what each level is** [CONFIRMED text]:
  - `agents/prompts.py` L231-236: L1-2 "Combat Control", L2-3 "Quasar Cannon - sector-wide weapon", L3-4 "TransWarp drive - instant travel", L4-5 "planet shields", L5-6 "endgame bunker". (These are labeled by the transition, so the level they refer to is ambiguous.)
  - `engine/planets.py` L138 comment: "L2 = Quasar Cannons -> big planet fighter boost".
  - `docs/DESIGN.md` L193-198: L1 treasury, L2 military command, L3 quasar, L4 planetary shields, L5 transwarp, L6 interdictor.
  - `web/app.js` L2076-2083 `CITADEL_TIERS` perks: L1 "Basic fortifications", L2 "Quasar Cannons - free planet fighters + shields", L3 "Transwarp emissions damping", L4 "Genesis torpedoes manufactured on-site", L5 "Planetary Interdictor - blocks hostile warps", L6 "MAX - full fortress".
  - `docs/FEATURE_COMPARISON.md` L175-179 uses yet another mapping and is stale: it says build/assign have no handler, and lines 30 and 304 claim quasar/interdictor hooks exist in ship-vs-planet resolution. The code shows they do not.
  - Only the app.js tooltip and the prompt text are visible to players or bots. None of them match the original order.

### 2.3 Planet fighters and shields

- Planet fighters and shields are plain integers on `Planet`. They are set **only** by the citadel-completion floor above. There is no production from colonists, no purchase, no transfer from ship to planet, no shield deposit, no regeneration after damage except the next citadel completion, and no cap constant. [CODE-READ ONLY]
- Prompt guidance (`prompts.py` L229, L232) tells bots: "DO NOT put ship-fighters on the planet pre-L2". But there is no action that puts ship fighters on a planet. [CONFIRMED by grep: no handler writes `planet.fighters` except `_complete_citadels`, siege resolution, and atomic.]
- Net worth counts planet defense: `victory.py::_planet_asset_value` (L56-97) adds `fighters * K.FIGHTER_COST (50) + shields * 10`, plus citadel sunk cost (credits + colonists x `COLONIST_PRICE` 10), colonists, stockpile at base prices, and treasury.

### 2.4 Mines and sector fighters

- Warp-in (`runner.py::_handle_warp` L248-363): mines are checked on the destination first. Armid mines: `hits = min(count, randint(1, MINE_MAX_HITS_PER_MOVE=10))`, each `ARMID_DAMAGE = 100`; damage hits shields then fighters; limpets attach silently; allied mines are ignored. Then sector fighters: offensive mode auto-attacks via `_resolve_fighter_sector_combat`, toll mode charges `min(credits, max(10, min(10000, count)))`. If damage zeroes your fighters, the ship is destroyed.
- `combat.py::_resolve_fighter_sector_combat` (L84-138): each side loses roughly the other's count times `uniform(0.8, 1.1)`, in one exchange. A winner can seize the sector.
- `deploy_fighters` (runner.py L551-588): up to `ship.fighters`, modes from `FighterMode`, not in FedSpace, 1 turn. If another player's group is already there, a clash resolves and the incoming group is consumed.
- `deploy_mines` (L591-626): armid, limpet, atomic; atomic detonates at once.
- **Interaction with planets:** none. Sector fighters and mines never fire when a player lands on a planet, and planets never join sector fights. The planet fight is a separate step inside `land_planet`. There is also no event order like the original (mines, then sector cannon, then sector fighters, then planet).

### 2.5 How a planet attack resolves (`runner.py::_handle_land_planet`, L730-864)

Trigger: landing on a planet that has an owner who is not you and not a corp mate (`hostile`), and `planet.fighters > 0`. Alliances are **not** checked here (only corp ticker), so you can siege an ally's planet. [CODE-READ ONLY]

1. Costs 3 turns (`TURN_COST["land_planet"]`); needs turns left.
2. Three rounds. Each round: attacker damage = `int(attacker_fighters * U(0.8, 1.2))`; defender damage = `int(planet_fighters * U(0.8, 1.2))`. Both sides apply damage via `_apply_volley`: shields absorb first, remaining damage kills fighters. The round loop ends early if either side reaches 0 fighters.
3. Results are written back to the ship and the planet. A `COMBAT` event is emitted with `exchange_kind="planet_siege"`, the planet id, `citadel_level`, the full `rounds[]` list, and final attacker/defender F and S.
4. If the attacker has 0 fighters: `_destroy_ship(reason="planet_defense", killer_id=owner)` (eject to StarDock, lose 25% credits, reset ship to a Merchant Cruiser with 20 fighters, deaths +1, elimination at 3).
5. Else if the planet still has fighters: `ActionResult(ok=False, "planetary defenses repelled landing", turns_spent=cost)`.
6. Else (planet fighters = 0): the attacker takes the planet. `owner_id = attacker`, `corp_ticker = attacker's corp`, `origin="other"`, `citadel_level = max(0, level - 1)`, `treasury *= 0.5`. The attacker lands. A `LAND_PLANET` event carries `seized=True`.

If the planet has 0 fighters the siege is skipped and the planet is taken for free, whatever its citadel level or shield count. [CODE-READ ONLY]

Differences to flag, all from reading code:

- Shields are not a separate gate. They are only damage soak in the same three-round exchange (via `_apply_volley`), so a planet with 0 fighters and 1,500 shields is taken without a fight. They do not use the 10:1 or 20:1 rules.
- Planet fighters are not split into offense (2:1) and defense (3:1). One flat pool fights at 1:1 symmetric dice.
- There is no quasar, interdictor, or photon interaction. `photon_missile` (`runner.py` L1767-1801) only targets a player (`target_id in universe.players`), setting that ship's `photon_disabled_ticks`. It does nothing to planets, mines or sector fighters in the sector.
- `ok=False` results do not charge turns: `apply_action` (runner.py L148-150) only adds turns when `result.ok`. A repelled siege returns `ok=False` with `turns_spent=cost`, so a failed siege appears to cost **no turns**, letting an attacker repeat. [CODE-READ ONLY; I did not run it.]
- After capture, `citadel_level` drops by 1 but `citadel_target` is not lowered. `_handle_build_citadel` blocks with "already under construction" when `citadel_target > citadel_level` (L1148-1152), and `observation._planet_brief` omits `next_build` in that state. So a captured planet with a completed target may be unable to build further. [CODE-READ ONLY; looks like a bug, needs a test to confirm.]
- Capture keeps the remaining shields, stockpile and colonists, and the planet keeps `last_tax_value` reset to its new value.

### 2.6 Other planet-attack tools

- **Atomic mines** (`_handle_atomic_detonation`, runner.py L629-687, `ATOMIC_MINE_COST = 4_000`): detonate at once (not placed). The attacker takes `-50 * qty` alignment. For each planet in the sector: treasury loses `ATOMIC_PLANET_DAMAGE (0.5) * qty` (capped at 1.0), fighters lose the same fraction, and if `qty >= 2` the citadel level drops by `max(1, qty // 2)`. It also nukes the port stock, and with `qty >= 3` can destroy the port, and wipes foreign sector fighters. It does not destroy the planet. This is closer to the original Atomic Detonator in name only.
- **Genesis** is only used for creation; no destructive use exists.
- **Limpets** (`MineType.LIMPET`, `LimpetTrack`, `_attach_limpet`, `query_limpets` runner.py L1804): tracker only; no tie to planets.
- **Ether probe / scan:** observations of planet fighters come from the sector view (see 2.8).
- No planet-destruction action, no corp planet transfer rules, and no maximum number of siege attempts per day.

### 2.7 Colonists and production (`engine/planets.py`)

- Production per 100 colonists, `PLANET_PROD_COEFF` (L26-34), units per day per 100 colonists in that pool:

  | Class | Fuel ore | Organics | Equipment |
  |---|---|---|---|
  | M | 3 | 5 | 3 |
  | K | 6 | 1 | 1 |
  | L | 5 | 3 | 1 |
  | O | 1 | 6 | 3 |
  | H | 8 | 0 | 1 |
  | U | 1 | 1 | 6 |
  | C | 1 | 3 | 5 |

- Daily (`_advance_planets` L153-171): each pool adds `int(colonists * coeff / 100)` to its stockpile. If the organics stockpile is positive, total colonists grow by `int(total * 0.05)` (5% per day, shared across pools) and organics fall by `max(1, total // 100)`.
- No population cap, no bell curve, no max stockpile. These are simplifications; the original has optimal-population curves and per-class caps. [CODE-READ ONLY]
- **Planet value tax:** `_pay_planet_value_tax` pays the owner `PLANET_VALUE_TAX_RATE = 0.30` of each day's rise in planet asset value (our invention; the original pays 2% treasury interest at L1 instead). Min payout `PLANET_VALUE_TAX_MIN_PAYOUT = 1`.
- **Colonist handling:** `assign_colonists` (runner.py L1048-1130), `load_planet_cargo` and `dump_planet_cargo` (L940-1045, 1 turn each, move commodities and colonist pools between ship and planet). Colonists cost `COLONIST_PRICE = 10` at StarDock (the original uses Terra).
- **Treasury:** the field exists but is only changed by siege (halved) and atomic (reduced). There is no deposit/withdraw action for planets, and no 2% interest. The `corp_deposit` and `corp_withdraw` actions touch only the corp treasury. [CONFIRMED by grep: `.treasury` is assigned at runner.py L652, L832 and the corp lines only.]

### 2.8 Visibility: what bots and spectators see

**Action surface.** `ActionKind` (`engine/actions.py` L11-45) has 34 verbs. Planet-related ones: `land_planet`, `liftoff`, `claim_planet`, `assign_colonists`, `load_planet_cargo`, `dump_planet_cargo`, `build_citadel`, `deploy_genesis`, plus `deploy_atomic`, `photon_missile`, `attack`. Missing: any planet-fighter, shield, military reaction, cannon, treasury, transporter, thruster, or planet-destroy verb.

**Observation (fog).** `engine/observation.py`:
- `owned_planets` (L585-615): owner-only, including `colonists`, `stockpile`, `production`, `organics_days_left`, `growth_active`, `fighters`, `shields`, `origin`, `citadel_target`.
- `orphaned_planets` (L617-651): up to 5, sorted by level then fighters, only after a `PLANET_ORPHANED` event; includes `citadel_level`, `fighters`, `shields`.
- `sector.planets[]` uses `_planet_brief` (L937-985) for **any** planet in your current sector, owner or not. It exposes `owner_id`, `corp_ticker`, `citadel_level`, `citadel_target`, `fighters`, `shields`, `treasury`, `stockpile`, `colonists`, and `citadel_next_build`. That is richer than the original (no planet scanner, and shielded planets are not hidden). The comment at L585-586 says sector briefs "must not publish another owner's runway", but `_planet_brief` includes stockpile and colonists. It is fog-safe only in the sense that you must be in the sector. [CODE-READ ONLY]
- `legal_actions` (`engine/legality.py` L333-345): `land_planet.planet_id.contested` lists planets that are hostile with fighters > 0.
- `adjacent[]` gives `has_planets` only (L444).

**Cockpit** (`web/bot.js`, `web/bot-parity.js`):
- Here panel (bot.js L443-446) lists name, class, id, owner or unowned, `citadel L#`, fighters, colonists total.
- Empire panel `renderPlanets` (L809-820) uses `P.planetRow` (bot-parity.js): `id, sector, origin, citadel L and target day, colonists by pool, stockpile, makes/day, eats organics/day, growing or not, organics days left, N fighters, N shields`.
- Orphans use `P.orphanRow`.
- Action form (bot.js L1066, 1125-1131, 1183-1185): `land_planet`, `build_citadel` with next-tier cost preview, and a warning "defended hostile planet - landing means citadel combat" when the target is in `contested`.
- No siege preview, no odds, no "you will lose X" estimate.

**Spectator** (`web/app.js`):
- Planet block per commander `renderPlanetsBlock` (L2038 onward): citadel ladder L1-L6 with the `CITADEL_TIERS` tooltips, idle and pooled colonists, stockpile, fighters, shields, treasury, population.
- Leaderboard sums owned planets and citadel levels (L1779-1808). Corp panel counts corp planets. Victory bar uses highest citadel level out of 6 (L1909-1931).
- Combat feed: `formatCombatRoundsHtml` (L2225-2247) renders each round of a `planet_siege` with "Attacker ship" vs "Citadel defense", shield absorption and fighters lost.
- Live planet patches (`server/runner.py` L1469-1495) only fire on `GENESIS_DEPLOYED, ASSIGN_COLONISTS, BUILD_CITADEL, CITADEL_COMPLETE, PLANET_ORPHANED`. A siege capture (`LAND_PLANET` with `seized`, plus the combat that changed fighters/shields) is not in that set, so the spectator's planet table may show the old owner and defense numbers until the next full `/state` snapshot. [CODE-READ ONLY; not run.]
- `server/spectator_gate.py` gates `/`, `/state`, `/events` and `/ws` behind `TW2K_SPECTATOR_TOKEN` if set; `/bot` and `/harness/v1/*` stay per-seat.

**Events.** Planet-related `EventKind`s used: `GENESIS_DEPLOYED, ASSIGN_COLONISTS, PLANET_CARGO_TRANSFER, BUILD_CITADEL, CITADEL_COMPLETE, LAND_PLANET, LIFTOFF, PLANET_CLAIMED, PLANET_ORPHANED, PLANET_TAX_PAYOUT, COMBAT (planet_siege), ATOMIC_DETONATION, SHIP_DESTROYED, PLAYER_ELIMINATED`. There are no events for cannon fire, shield loss, interdiction, or planet destruction.

**Bots.** `agents/seat_brain.py` lands only on its own or uncontested planets (L685-711, uses the `contested` list) and loads cargo. I found no siege, defend, or planet-garrison behavior. Heuristic and LLM prompts talk about planets as an economy tool (`prompts.py` L208-260), not a war tool. The word "siege" appears in prompts only as "no siege needed" for orphans (L305).

**Tests.** `tests/test_seat_bot_s1.py::test_siege_seizure_is_other_origin` covers seizure of an undefended planet. I found no test of the full three-round siege, repel, ship-loss-on-siege, post-capture build, or defensive numbers. [CODE-READ ONLY; I only grepped tests.]

**Planning docs.** `docs/ROADMAP.md` L44: "[ ] Planet siege / capture (stretch)". `docs/FEATURE_COMPARISON.md` is stale. `docs/DESIGN.md` L200-203 says capturing "requires ground forces (not modeled in Phase 1 - treat as fighter siege)". I found no recent plan under `docs/plans/` for planetary warfare.

---

## PART 3: Mechanic-by-mechanic comparison

Legend: **Match** same idea and similar numbers; **Partial** some of it; **Missing** not present; **Different** present but works another way; **Better** arguably improved for this game.

| # | Mechanic | Original (source) | Ours (file) | Status |
|---|---|---|---|---|
| 1 | Planet classes M/K/L/O/H/U/C | 7 classes with distinct production/caps (S1) | Same 7; class affects production coefficients only (planets.py) | Partial |
| 2 | Class-specific citadel cost and time | Per class table (S1/S2) | One table for all classes (constants.py L206) | Different |
| 3 | Citadel build inputs | Colonists + fuel, organics, equipment, no credits | Credits + colonists, no commodities | Different |
| 4 | Citadel build times | 34-52 days total by class | 13 days total | Different (much faster) |
| 5 | Colonist cost per level | 6k-10k at L4-L6 | 8k/16k/32k at L4-L6 | Different (our L5/L6 are larger) |
| 6 | L1 Treasury (interest, deposit) | Yes, 2% daily | Field only; no deposit action, no interest | Missing |
| 7 | L2 Combat Control / Military Reaction | 2:1 attack / 3:1 defend split by % | Gives a garrison floor of 1000xL fighters and 250xL shields; flat 1:1 dice | Different |
| 8 | L3 Quasar cannon (sector shot) | fuel x pct / 3, uses fuel | None | Missing |
| 9 | Atmospheric Quasar | fuel x pct x2 (MBBS), TWGS differs (conflict) | None | Missing |
| 10 | L4 planet TransWarp | 400 fuel per jump, needs fighter lock | None | Missing |
| 11 | Planetary transporter | 50k + 25k/hop, 10 fuel/sector, 1 turn | None | Missing |
| 12 | L5 planetary shields | 10 ship shields = 1 planet shield; 20:1 odds; protects Quasar from photon | Shields are a number granted free at L2+ (250xL); used as damage soak only | Different |
| 13 | L6 interdictor | Blocks exit, 500 fuel/attempt, triggers Quasar | None | Missing |
| 14 | Planet fighter production | From colonists output, class "fig factor" | None (only citadel floor) | Missing |
| 15 | Fighter transfer ship<->planet | Yes (players stock planets) | No action | Missing |
| 16 | Max planet fighters | 1,000,000 | No cap constant | Partial |
| 17 | Planet attack odds | Offensive 2:1 wave sized 1.25x ship capacity; defensive 3:1 | One exchange, 3 rounds, `U(0.8,1.2)`, symmetric | Different |
| 18 | Shield gate before fighters | Offensive fighters wait until shields down | No gate; fighters can be zero while shields remain, then free capture | Different |
| 19 | Sector fighters/mines vs planet attack | Fire first (step 3-5) | Not part of landing | Missing |
| 20 | Armid mines | 50% detonate; 20 dmg/mine (v1) | Up to 10 mines, 100 dmg each | Different |
| 21 | Limpet mines | Attach on entry | Same idea, tracker + query | Match |
| 22 | Photon missile vs planet | Disables Quasar, mines, sector fighters, offensive planet fighters (shield/L5 rules) | Disables a ship's fighters 1 tick; no planet effect | Different |
| 23 | Ship loss in planet fight | Pod/destroyed; limits on pods | Eject to StarDock, lose 25%, 3rd death = elimination | Different |
| 24 | Capture mechanic | Kill figs, press O | Auto-capture when fighters = 0; level -1, treasury x0.5 | Partial |
| 25 | Planet destruction | Atomic Detonator (v1), colonist kill first | Atomic mine hits planet (lowers level, fighters, treasury) but never destroys | Partial |
| 26 | Genesis torpedo | Creates planet; used in overload trick (v1) | Creates planet with 2,500 colonists; min 3 hops; 4 turns | Different |
| 27 | Planet cap per sector | "Usually 5" (S3) | None found | Missing |
| 28 | Colonist growth / bell curve | Peak at 50% of max pop | +5%/day if organics > 0; no cap | Different |
| 29 | Production formulas | Per class ratios | Per-100 coefficients | Partial |
| 30 | Corp planets | Shared; disband rules (CEO sector or Rogue) | Shared build/manage; no disband transfer; leave does nothing | Partial |
| 31 | Orphans / abandoned planets | Rogue on disband (S5) | `PLANET_ORPHANED` on elimination; `claim_planet` inherits citadel and fighters | Better (clearer, evented) |
| 32 | Planet scanner / info hiding | Scanner shows non-shielded planets only | Any planet in your sector is fully visible in the observation | Different |
| 33 | Planet income | 2% treasury interest; sell FOE at ports | 30% of daily value gain paid as credits + stockpile sales | Different |
| 34 | Alignment/XP for planet ops | Formulas in S2 | XP for build, genesis, claim; atomic -50 alignment | Partial |
| 35 | Combat transparency for spectators | Text logs | Per-round structured events + UI volley log | Better |

## Gap list, ranked by importance to gameplay

1. **No way to stock a planet with fighters or shields, and no fighter production.** Planet fighters appear only as a free citadel gift. That makes planets undefendable beyond what the engine hands out and removes the main resource sink for late-game credits. (Rows 14, 15)
2. **Siege flow is too thin:** a fight with 0 planet fighters is a free capture; shields don't gate; no 2:1/3:1 split; no sector-defense phase. Also the possible free-retry (no turn charge on repel) and the post-capture build block. These two look like bugs and are the cheapest fixes. (Rows 17, 18, 19, 24)
3. **No Quasar cannon.** It is the signature late-game weapon and fuel ore drain is the original's "war of ore". Without it the fuel ore a planet produces has no combat use. (Rows 8, 9)
4. **Level mapping is inconsistent across the engine, prompts, DESIGN.md and UI.** Bots and players are told different things about what L3, L4 and L5 do. (Section 2.2)
5. **No treasury actions.** The L1 reward is a dead field. Easy to add and gives a safe place for credits and a reason to defend. (Row 6)
6. **Photon missile has no effect on planets or sector defenses.** The photon is the original's counter to the Quasar. (Row 22)
7. **Interdictor, planet TransWarp, planetary transporter missing.** Lower priority for a game with simplified travel, but they define "late-game." (Rows 10, 11, 13)
8. **Citadel costs ignore planet class and commodities**, flattening the strategic choice of which class to build on. (Rows 2-5)
9. **Planet destruction and the atomic path:** atomic mines never destroy a planet, and no colonist-kill step exists. (Row 25)
10. **Corp planet edge cases** (leave and disband, ally siege). (Row 30)
11. **Spectator staleness:** capture and defense changes don't patch the live planet table. (Section 2.8)

## What we do differently or better

- **Fog-safe, owner-only planet intel for bots**, with `production`, `organics_days_left`, `growth_active` and precomputed `citadel_next_build` (blocker text included). The original has no such helper.
- **`legal_actions` with precondition reasons**, including `land_planet.contested`, and a cockpit warning before a hostile landing.
- **Structured per-round combat events** (`rounds[]`, absorbed shields, fighters lost, `ended_here`) and a spectator volley log, which suit video/cockpit presentation.
- **Orphan and claim flow** (`PLANET_ORPHANED`, `claim_planet`), which gives a clear event and a decision for survivors.
- **Predictable build costs in credits and colonists**, which are simpler for LLM bots to plan than the original's four-commodity tables.
- **Planet value dividend** (30% of value gains) gives owners a tangible daily reward.
- **Net worth includes planet defense value**, so garrisons count towards the score.
- **Corp treasury can pay citadel costs.**

## Recommended next slices (small, fog-safe)

Each one is meant to be a small change. Items marked "engine" change rules; "cockpit" changes display only.

1. **Engine bug fixes, no new rules.** (a) On siege capture, set `citadel_target = citadel_level` and `citadel_complete_day = None`. (b) Charge turns on a repelled siege. (c) Add a test for the full siege path (repel, win, ship loss, post-capture build). Also test that a 0-fighter, shielded planet falls only by design.
2. **Planet fighter and shield stocking (engine).** Add `deposit_planet_defense` and `withdraw_planet_defense` actions (landed, owner or corp, 1 turn, ship fighters or shields to the planet, 10 ship shields = 1 planet shield, citadel level >= 2). Cap planet fighters with a constant. This is owner-only data and needs no fog change.
3. **Shield gate in the siege (engine).** Attack shields first, and only when shields are down do the planet's fighters fight. Keep three rounds. Show the phase in the existing `rounds[]` payload so the spectator log needs only a label.
4. **Treasury actions (engine + cockpit).** `deposit_treasury` and `withdraw_treasury` at L1+, with optional daily interest as a constant. Show the treasury in the Empire panel (add `treasury` to the `owned_planets` rows; today only the sector brief and the spectator planet block carry it).
5. **One consistent level table.** Pick one level->perk list, put it in `constants.py` as the single source, and have `prompts.py`, `web/app.js` `CITADEL_TIERS`, `DESIGN.md` and the planets.py comment read from or match it. Consider moving shields to the original's L5 and combat control to L2 so the numbers read like the original.
6. **Fuel-ore Quasar, sector shot only (engine).** Settings: `quasar_sector_pct` on the planet. On warp-in to a sector with a hostile L3+ planet, fire `fuel * pct / 3` damage and burn `fuel * pct` fuel. Emit a `QUASAR_FIRE` event. This gives fuel ore a combat purpose and a cheap moth counter. Atmospheric shot can follow later once the TWGS-vs-MBBS factor is decided.
7. **Cockpit siege preview (cockpit only).** In the `land_planet` form, when the target is `contested`, show planet fighters, shields, your fighters and shields, and a plain note about 3 rounds. All of it is already in the sector observation. No fog change.
8. **Spectator patch fix (server).** Add `LAND_PLANET` (seized) and planet `COMBAT` events to the live planet-patch event set so the table updates without a refresh.
9. **Later:** class-specific citadel tables, photon effect on planetary defenses, interdictor, and planet destruction rules.

Open decisions needed from Ben before slices 2-6: whether to keep credits as the citadel cost (our current choice) or move to commodities, and whether the original's slow build times (34-52 days) are wanted at all, given the default match length of `VICTORY_DEFAULT_MAX_DAYS = 30`.

## What I could not verify

- Official EIS/TWGS manual text. Everything in Part 1 comes from community write-ups.
- Which TWGS atmospheric Quasar factor is right (S1 vs S2 conflict).
- Exact meaning of "20:1" for shields in S1.
- Original per-mine damage in TWGS 3.x, and a per-sector planet limit in TWGS.
- Any daily planet attack limit in the original.
- Runtime behavior of our engine (I did not run it or any tests). Items tagged CODE-READ ONLY are from reading source.
- Spectator behavior after capture, and the corp-leave interaction with planet access.
- Whether `_planet_brief` leaking treasury/stockpile of rival planets in your sector is intended.
