# Planet Deep Dive: Current TW2K Planets vs. Classic TradeWars 2002

Date: 2026-04-28

## Executive Summary

The current planet system is partially functional. Players can create planets,
claim/land on them, move colonists onto them, build citadels, grow colonists,
produce commodity stockpiles, inherit orphaned planets, and receive net-worth
credit for planet assets. Hostile players can also siege planets if they attempt
to land on an enemy-owned planet with defenders.

The biggest gap is that planets are not yet full economic or military bases in
the classic TradeWars 2002 sense. Planet stockpiles increase net worth, but there
is no action to load fuel/organics/equipment from a planet into ship cargo, dump
ship cargo onto a planet, or sell planet-produced goods at ports. Planet defenses
only trigger when a hostile player attempts `land_planet`; they do not fire at
ships or Ferrengi merely entering the sector. There is no quasar cannon, no
military reaction percentage, no fighter production, no planetary transporter,
and no mobile planets.

Short version:

- Planets currently work as strategic net-worth assets and citadel projects.
- They do not yet work as liquid cash farms.
- Planetary defenses do shoot hostile players during a landing attempt.
- Planetary defenses do not shoot Ferrengi.
- Sector fighters/mines can defend a sector against player movement, but not
  Ferrengi movement.
- The AI prompt currently overstates planet mutual defense; the engine does not
  have citadel/quasar coverage over neighboring sectors.

## Reference Game Baseline

The most direct comparison target is classic TradeWars 2002. Public TW2002
reference material describes planets as:

- Genesis-created worlds in normal space, usually placed deep and away from
  high-traffic lanes.
- Colonist-powered production centers for fuel ore, organics, equipment, and
  fighters.
- Bases with six citadel levels.
- Defensive platforms once a citadel reaches meaningful levels, especially with
  combat control, military reaction settings, fighters, shields, and quasar
  cannons.
- Storage and logistics hubs for stockpiles, ships, credits, and corp activity.
- Economic engines when produced commodities can be moved to ports or used in
  red cashing loops.

Useful references used for this comparison:

- The Stardock TW2002 archive, `core/planets.md`
- The Stardock TW2002 archive, `advanced/economy.md`
- The Stardock TW2002 archive, `strategy/defense.md`
- Break Into Chat's general TradeWars 2002 overview

## Current Engine Inventory

### Planet Data Model

Implemented in `src/tw2k/engine/models.py`.

Each `Planet` has:

- `id`, `sector_id`, `name`, `class_id`
- `owner_id`, `corp_ticker`
- `citadel_level`, `citadel_target`, `citadel_complete_day`
- colonist pools: `fuel_ore`, `organics`, `equipment`, `colonists`
- stockpile: `fuel_ore`, `organics`, `equipment`
- `fighters`, `shields`, `treasury`

The model supports the basic state needed for colonization, production, and
defense. It does not include quasar cannon settings, military reaction
percentage, planetary transporter range, planetary ownership permissions beyond
owner/corp, per-commodity storage caps, or mobile planet fields.

### Genesis Deployment

Implemented in `src/tw2k/engine/runner.py::_handle_deploy_genesis`.

What works:

- Requires a Genesis torpedo on the ship.
- Cannot deploy in FedSpace.
- Cannot deploy too close to StarDock; current minimum is
  `GENESIS_MIN_HOPS_FROM_STARDOCK = 3`.
- Requires the player to be in space, not landed.
- Costs `GENESIS_DEPLOY_TURN_COST = 4` turns.
- Rolls planet class from `PLANET_CLASS_WEIGHTS`.
- Creates a player-owned planet in the current sector.
- Seeds 2,500 colonists across productive/idle pools.
- Seeds a small organics stockpile so growth can start.

Compared to classic TW2002:

- This is directionally good.
- The seed population is a deliberate playability improvement. Classic TW2002
  expects colonists to be ferried from Terra; the current game allows L1 citadel
  construction to start without a long zero-progress phase.

### Landing, Neutral Claiming, and Orphan Claiming

Implemented in `src/tw2k/engine/runner.py::_handle_land_planet` and
`_handle_claim_planet`.

What works:

- `land_planet` lands on a planet in the current sector.
- Neutral map-start planets are automatically claimed by landing.
- True orphaned planets, created when an eliminated player loses solo-owned
  planets, require the explicit `claim_planet` action.
- `claim_planet` transfers orphaned citadels, fighters, stockpile, and colonists
  to the claiming player.
- Corp-owned planets are protected from the solo orphan-claim path.

Compared to classic TW2002:

- The neutral/orphan distinction is a game-specific simplification, but it now
  gives agents a clear mechanic.
- Inheriting built-up planets is good gameplay because it turns eliminations
  into map objectives.

### Colonists

Implemented in `src/tw2k/engine/runner.py::_handle_buy_equip` and
`_handle_assign_colonists`.

What works:

- Players can buy colonists at StarDock using
  `buy_equip item=colonists qty=N`.
- Colonists load into ship cargo.
- A landed owner/corp member can move colonists from ship cargo onto a planet.
- Colonists can be assigned to `fuel_ore`, `organics`, `equipment`, or idle
  `colonists`.
- Colonists can be picked back up from those pools into ship cargo.
- Build-citadel consumes total colonists from the planet.

Important naming issue:

- `assign_colonists from=fuel_ore to=ship` means "move colonists assigned to the
  fuel_ore work pool back to the ship."
- It does not mean "load fuel ore stockpile into the ship."

Compared to classic TW2002:

- Colonist ferrying basically works.
- The current command name and pool names are easy for humans and AIs to
  misread as commodity movement. This is one reason P1/P3 can talk about
  "equipment loops" that do not actually exist yet.

### Citadel Construction

Implemented in `src/tw2k/engine/runner.py::_handle_build_citadel` and
`src/tw2k/engine/planets.py::_complete_citadels`.

What works:

- Six citadel levels exist.
- Each tier has a credit cost, colonist cost, and build time.
- Requires owner/corp access and landing on the planet.
- Corp treasury can pay citadel credit cost before personal credits.
- Completed L2+ citadels auto-grant a minimum planet defense:
  `fighters = max(existing, 1000 * level)` and
  `shields = max(existing, 250 * level)`.
- Citadel value counts toward full net worth.

Compared to classic TW2002:

- The level ladder exists, but tier capabilities are simplified.
- Current citadels do not require commodity stockpiles for advancement.
- Current citadels do not unlock distinct functions per level beyond defense
  minimums and scoring.
- There is no L2 combat-control/military-reaction setting.
- There is no L4+ mobile planet behavior.
- There is no L5 shield installation feature beyond the simplified shield
  minimum.
- There is no L6 interdictor-style behavior.

### Daily Production and Growth

Implemented in `src/tw2k/engine/planets.py::_advance_planets`.

What works:

- Every day, each productive colonist pool creates commodity stockpile.
- Production coefficients are class-specific:

| Class | Fuel | Organics | Equipment |
| --- | ---: | ---: | ---: |
| M | 3 | 5 | 3 |
| K | 6 | 1 | 1 |
| L | 5 | 3 | 1 |
| O | 1 | 6 | 3 |
| H | 8 | 0 | 1 |
| U | 1 | 1 | 6 |
| C | 1 | 3 | 5 |

- Produced amount is `int(colonists * coeff / 100)`.
- If organics stockpile is positive, total colonists grow by about 5 percent.
- Growth consumes organics.

Compared to classic TW2002:

- This is a simplified linear production model.
- Classic TW2002 has class-specific maximum colonists, maximum stockpiles,
  commodity ratios, and fighter production formulas.
- Classic TW2002 Class U is effectively non-productive; current Class U is the
  best equipment producer.
- Current stockpiles have no storage caps.
- Current planets do not produce fighters.
- Current production creates net-worth value but does not create spendable
  credits unless future actions let players move/sell the goods.

### Stockpiles and Making Money

Stockpile valuation is implemented in
`src/tw2k/engine/victory.py::_planet_asset_value`.

What works:

- Stockpiles count toward time/net-worth scoring at base commodity prices.
- Planet treasury counts toward planet value.
- Colonists, defenses, and citadel investment count toward planet value.

What does not work:

- No action exists to load planet fuel/organics/equipment stockpile into ship
  cargo.
- No action exists to dump ship fuel/organics/equipment cargo onto a planet.
- No action exists to trade directly between a planet and nearby port.
- No action exists to sell a planet stockpile for credits.
- `planet.treasury` exists but there is no direct player-facing deposit or
  withdraw action for planet treasuries.

Verification probe:

```text
stockpile_load_attempt False invalid 'from' pool 'stockpile'
fuel_ore_pool_to_ship_moves_colonists True
ship_colonists 10
ship_fuel_ore 0
stockpile_fuel_ore 1000
fuel_ore_colonist_pool 5
```

Interpretation:

- The engine rejects `from=stockpile`.
- Moving `from=fuel_ore to=ship` moves colonists assigned to fuel production,
  not fuel ore stockpile.
- Planet stockpile stayed at 1,000 fuel ore.
- Ship fuel ore stayed at 0.

Answer to "How can you use planetary resources to make money?":

- Today: by increasing net worth for time/net-worth victory.
- Not today: by loading goods from the planet and selling them at ports for
  spendable credits.

This is the most important missing planet economy feature.

### Planetary Defense

Implemented in `src/tw2k/engine/runner.py::_handle_land_planet`.

What works:

- If a hostile player tries to land on a planet and the planet has fighters,
  the landing triggers planet-vs-ship combat.
- Planet fighters and shields absorb/deal damage.
- If the attacker is destroyed, the ship is destroyed and ejected.
- If the planet defenders survive, landing is repelled.
- If defenders are wiped, the attacker seizes the planet, damages the citadel by
  one level, and captures half the treasury.
- If the hostile planet has no fighters, the attacker seizes it.

What does not work:

- Planet defenses do not fire at a hostile player merely entering the sector.
- Planet defenses do not fire at Ferrengi.
- Planet defenses do not protect nearby sectors.
- Planet defenses do not use fuel ore as ammunition.
- There is no quasar cannon damage pass.
- There is no military reaction percentage.
- There is no setting to decide how aggressively a citadel reacts.

Verification probe:

```text
sector_fighters_vs_player_warp_ok True
combat_events ['combat']
remaining_sector_fighters 0
```

This probe verifies sector fighters can hit a player entering a defended sector.
That is sector defense, not planet defense.

### Sector Fighters and Mines

Implemented in `src/tw2k/engine/runner.py::_handle_deploy_fighters`,
`_handle_deploy_mines`, and `_handle_warp`.

What works against players:

- Players can deploy fighters in defensive, offensive, or toll mode.
- Offensive fighters attack hostile players on warp-in.
- Toll fighters charge a simplified toll.
- Armid mines damage hostile players on warp-in.
- Limpet mines attach trackers.
- Atomic mines detonate immediately and can damage ports, planet treasury,
  planet fighters, citadel levels, and hostile sector fighters.

What does not work against Ferrengi:

- Ferrengi movement does not pass through `_handle_warp`.
- Ferrengi do not trigger sector fighters.
- Ferrengi do not trigger mines.

Verification probe:

```text
ferrengi_roamed_to 21
ferr_fighters 400
sector_fighters 500
combat_events []
```

Interpretation:

- A Ferrengi moved into a sector with 500 hostile offensive fighters.
- Ferrengi fighters remained unchanged.
- Sector fighters remained unchanged.
- No combat event fired.

So, no, current defenses do not shoot Ferrengi entering the sector.

### Ferrengi and Planets

Implemented in `src/tw2k/engine/ferrengi.py`.

What works:

- Ferrengi spawn outside FedSpace.
- Ferrengi roam one sector per day with a configured probability.
- Ferrengi attack co-located player ships if aggression rules allow.
- Ferrengi can kill players and cause planet orphaning after player
  elimination.

What does not work:

- Ferrengi do not attack planets.
- Ferrengi do not siege citadels.
- Ferrengi do not attack or trigger sector fighters/mines.
- Ferrengi do not loot stockpiles or treasury.

That means a planet cannot currently be lost directly to Ferrengi. The danger is
indirect: Ferrengi kill the owner repeatedly, the owner is eliminated, and solo
planets become orphaned.

## Feature Comparison Matrix

| Feature | Classic TW2002 expectation | Current TW2K status | Gap |
| --- | --- | --- | --- |
| Genesis planets | Core planet creation mechanic | Works | Mostly good |
| Deep placement | Strategic safety requirement | Works via StarDock hop minimum | Good |
| Planet classes | Strong class identity and production caps | Works, simplified | Needs fidelity pass |
| Colonist ferrying | Core growth loop | Works | UX/action names confusing |
| Commodity stockpiles | Produced, stored, moved, sold/used | Produced and valued only | Major economy gap |
| Fighter production | Planets produce fighters | Missing | Major defense/economy gap |
| Citadel levels 1-6 | Unlock progressive functions | Levels exist | Capabilities simplified |
| Citadel construction requirements | Colonists plus commodities/time | Credits plus colonists/time | Needs resource requirements |
| Planet treasury | Citadel cash storage | Field exists, limited use | Missing player-facing actions |
| Planetary landing defense | Defenders fight invasions | Works | Good basic siege |
| Sector-wide citadel defense | Q-cannons/reaction defend sector | Missing | Major defense gap |
| Ferrengi vs planets | NPC threat can affect safety in spirit | Missing direct interaction | Design choice/gap |
| Sector fighters vs players | Fighters can defend sectors | Works | Good |
| Sector fighters vs Ferrengi | Defenses should matter to NPC traffic | Missing | Major consistency gap |
| Mines vs players | Mines trigger on movement | Works | Good |
| Mines vs Ferrengi | Should matter if Ferrengi are real ships | Missing | Consistency gap |
| Planetary transporters | High-level logistics engine | Missing | Major advanced economy gap |
| Mobile planets | High-level strategic tool | Missing | Advanced gap |
| Corp planet access | Shared corp use | Works for owner/corp checks | Good base |
| Orphan planet inheritance | Capture abandoned assets | Works | Good game-specific feature |

## AI Prompt Accuracy Issues

The current prompt is mostly aligned with implemented actions, but it overstates
planet capability in a few places.

Prompt claim:

> mutual defensive support (one citadel's quasar cannon covers neighbors)

Current engine reality:

- No quasar cannon exists.
- No planet defense covers neighboring sectors.
- Planet defenses only trigger when an enemy lands on that exact planet.

Recommended immediate prompt correction:

- Replace "one citadel's quasar cannon covers neighbors" with something like:
  "shared logistics and nearby sector fighter coverage are easier to manage."

Prompt/AI confusion around stockpiles:

- The prompt correctly describes colonist assignment, but the action name
  `assign_colonists` plus pool names like `equipment` make it easy for AIs to
  infer that they can run an "equipment loop" from a planet.
- Add a clear negative rule until the economy feature is implemented:
  "Planet stockpiles currently count for net worth only; you cannot load
  stockpiled fuel/organics/equipment into ship cargo yet."

## Recommended Planet Phase Roadmap

### Phase P1: Make Planet Resources Liquid

This is the highest-value next step because it turns planets from passive score
assets into active economic engines.

Add actions:

- `load_planet_cargo`
  - Preconditions: landed, owner/corp access, commodity is fuel/organics/equipment,
    enough stockpile, enough ship cargo space.
  - Effect: move stockpile to ship cargo.
- `dump_planet_cargo`
  - Preconditions: landed, owner/corp access, commodity cargo available.
  - Effect: move ship cargo to planet stockpile.
- Optional: `planet_trade`
  - Preconditions: landed on a planet in a sector with a port.
  - Effect: sell/buy between planet stockpile and port using existing economy
    prices, probably with a turn cost.

Why first:

- It answers the user's "how do I make money with planetary resources" question.
- It enables real directives like "farm organics on the O-class planet and sell
  at nearby Bxx ports."
- It makes stockpile production matter during live play, not just at scoring.

Tests to add:

- Load stockpile to ship cargo.
- Reject load when cargo holds are full.
- Reject load by non-owner/non-corp.
- Dump ship cargo to planet stockpile.
- Sell loaded planet goods at a port via existing `trade`.
- Optional direct `planet_trade` price/stock behavior.

### Phase P2: Add Fighter Production

Add daily fighter production from colonist assignment and class-specific ratios.

Suggested simple model:

- Add a `fighters` production pool or reuse idle `colonists` as defense/fighter
  workers.
- Generate planet fighters daily based on class factor.
- Consider consuming equipment or fuel ore for higher fidelity.

Why second:

- Classic planet play is about growing a defensive fighter base.
- It gives players a reason to protect and revisit planets.
- It lets planets scale from fragile claim to serious stronghold.

Tests to add:

- Class O/L/M produce fighters at expected relative rates.
- Class U produces no or low fighters depending on design.
- Fighter production respects caps if caps are added.
- Net worth reflects produced fighters.

### Phase P3: Make Sector Defense Affect Ferrengi

Ferrengi should either be "real ships" that trigger sector defenses, or the UI
and prompt should explicitly say they ignore player defenses. The better game
direction is to make defenses matter.

Add to Ferrengi roam:

- On moving into a sector, check hostile sector mines/fighters.
- Trigger armid/limpet effects.
- Trigger offensive fighters.
- Allow Ferrengi to flee or die.

Design choice:

- Toll fighters probably should not charge Ferrengi unless the game wants
  pirate toll payments.
- Defensive fighters can remain passive.

Tests to add:

- Ferrengi entering offensive fighter sector takes combat.
- Ferrengi entering armid mine sector takes mine damage.
- Ferrengi entering limpet sector gets tracked or consumes mine.
- Allied/corp logic does not apply to NPCs.

### Phase P4: Add Citadel Reaction / Quasar Defense

This is the missing "real base defense" layer.

Minimal implementation:

- Add fields to `Planet`:
  - `military_reaction_pct`
  - `quasar_enabled`
  - optional `quasar_sector_range`
- At citadel L2+, allow the planet to fire when hostile players enter the
  planet's sector.
- Consume fuel ore from stockpile as ammunition.
- Scale damage by citadel level, reaction percentage, and stockpile fuel.

Conservative first rule:

- Only defend the same sector.
- Do not defend neighboring sectors until the same-sector behavior is balanced.

Tests to add:

- L1 planet does not fire.
- L2+ planet fires on hostile player entering sector.
- Fuel ore is consumed.
- No fire on owner/corp/ally.
- Ferrengi behavior is explicitly tested based on chosen design.

### Phase P5: Add Classic Citadel Tier Capabilities

After the basics work, make levels feel different.

Potential level map:

- L1: planet treasury deposit/withdraw.
- L2: combat control and military reaction.
- L3: stronger logistics/intel, maybe faster loading.
- L4: planetary transporter or limited movement.
- L5: shield installation / stronger defense.
- L6: interdictor or top-tier anti-invasion behavior.

This does not need to be exact TW2002. The important part is that each level
unlocks something legible and worth pursuing.

### Phase P6: Add Production Caps and Class Fidelity

Bring classes closer to TW2002:

- Per-class max colonists.
- Per-class max stockpiles.
- Bell-curve production or at least diminishing returns.
- U-class very low/no production.
- O-class strong organics.
- H/K/L strong fuel.
- M balanced.
- C niche/low-output.

This should come after liquid resources, because caps matter more once resources
can be exploited.

## Suggested AI Directives After Current State

Until planet resource loading exists, do not tell an AI to "sell planet
stockpile" or "run an equipment loop from the planet." It cannot do that.

Good current directives:

- "Build net worth through safe trading first, then buy a Genesis torpedo and
  colonists."
- "Place Genesis at least 3 hops from StarDock, preferably in a dead-end or
  low-traffic sector."
- "Land, build Citadel L1, then ferry more colonists to keep upgrading."
- "Use planet stockpile as net-worth growth, not spendable cash."
- "Deploy sector fighters/mines around the planet if you want protection from
  players. Do not rely on them to stop Ferrengi yet."
- "If you expect combat, buy ship fighters/shields. Planet defenses only help
  if the enemy tries to land on the planet."

Bad current directives:

- "Load organics from planet and sell them."
- "Use planet equipment stockpile for a port loop."
- "Let planet defenses kill Ferrengi entering the sector."
- "Trust quasar cannons to cover neighboring sectors."

## Verification Performed

Code inspected:

- `src/tw2k/engine/models.py`
- `src/tw2k/engine/actions.py`
- `src/tw2k/engine/runner.py`
- `src/tw2k/engine/planets.py`
- `src/tw2k/engine/ferrengi.py`
- `src/tw2k/engine/victory.py`
- `src/tw2k/agents/prompts.py`
- `tests/test_phase_abc.py`
- `tests/test_history_buffer.py`

Runtime probes performed:

1. Player enters hostile offensive sector fighters:
   - Combat fired.
   - Sector fighters were consumed/damaged.
2. Ferrengi enters hostile offensive sector fighters:
   - No combat fired.
   - Ferrengi and sector fighters were unchanged.
3. Player tries to load planet stockpile:
   - `from=stockpile` rejected.
   - `from=fuel_ore to=ship` moved colonists, not commodity fuel ore.

Conclusion:

- Planet landing defense works against hostile player landing attempts.
- Sector defenses work against player movement.
- Ferrengi bypass sector defenses.
- Planet stockpiles cannot currently be converted into spendable credits.

## Recommended Next Coding Task

Implement Phase P1 first: `load_planet_cargo` and `dump_planet_cargo`, plus tests
and prompt/UI updates.

This is the smallest change that unlocks the most visible gameplay:

- A planet can actually generate money.
- AI directives about planet farming become valid.
- Stockpile numbers in the UI become actionable.
- Future citadel resource requirements and quasar fuel consumption have a
  real logistics base.
