# citadel-cost-fidelity-v1

`CITADEL_FIDELITY_MODE` is `tw2002` or `legacy`. Legacy keeps the credit table. An explicit `CITADEL_COST_MODE` of `class` still consumes colonists; that path is not the live rule.

Tw2002 spends the class-table fuel ore, organics, and equipment already in `CITADEL_CLASS_COSTS`, scaled by `CITADEL_BUILD_TIME_SCALE`. Colonists are a population requirement and are not consumed. There is no credit cost.

Class M colonist counts in that table are 1000/2000/4000/6000/6000/6000, matching S1. The live TWGS note of 1,000,000 colonists for a class M level-1 citadel disagrees. This slice follows S1 and the coded table. Slice 72 records the live number on the gap map.

Level-1 class M goods are 300 ore, 200 organics, 250 equipment, 4 raw days. That matches the live note's goods and days.

Planet fighters do not shoot until citadel level 2 while this mode is on. Colonists landed from a ship join the fuel_ore production pool. The idle pool remains for legacy.

Net worth prices a finished citadel at the goods it required, not at the credit-tier table.

The seat keeps those goods on the planet and will not sell them through a port or a planetary trade while the next level still needs them. When it is already docked at a port that sells the missing good, it buys a useful lot and hauls it home. It does not cross the map looking for a seller. HeuristicAgent never builds a citadel or assigns colonists; the engine rule is what redirects a colonist drop into the fuel ore pool.

A corp mate at the port in the same sector was selling the citadel goods before the build. The trade menu now offers only the surplus above the next level's ore, organics, and equipment when the planet already has the colonists.

## 10-day seed 250925

Seats N3,N3,N2,N2,N1,H. Universe 1000, 1000 turns/day, 20,000 credits, Ferrengi on. Rejected 0/0 and exceptions 0 in both modes.

| Mode | Digest | Citadels |
|---|---|---|
| tw2002 | 94e24a5b | P1 class O level 2, class H level 1 building level 2. P3 class M level 2. P5 class M level 1 and class U level 0. P2 class K level 0. P4 no planet. |
| legacy | 7a34702d | P1 class O level 2, class H level 1. P3 class M level 2 and class M level 0 building level 1. P5 class K level 1. P2 class U level 0. P4 class H level 0. |

## 10-day seed 4242

Same seats and settings. Rejected 0/0 and exceptions 0 in both modes.

| Mode | Digest | Citadels |
|---|---|---|
| tw2002 | f4893d1b | P5 class M level 2 and class O level 2. P3 class O level 2. P1 class O level 1 building level 2. P2 class O level 0. P4 class M level 0. |
| legacy | 8ab91c41 | P5 class M level 3. P1 class O level 2 and class C level 1 building level 2. P3 class L level 2. P2 class O level 0. P4 class M level 0. |

## 30-day seed 250925

Same seats and settings. Rejected 0/0, exceptions 0, and save_load_day15 identical in both modes.

| Mode | Digest | Citadels |
|---|---|---|
| tw2002 | 8b76bd0f | P1 class O level 5, class L level 3, class H level 2, class O level 2. P3 class M level 5 and class L level 2. P5 class M level 2 and class U level 0. P2 class K level 0. P4 no planet. |
| legacy | c7b08a7c | P1 four citadels at level 2 (O, H, M, M). P3 class M level 3, class M level 2, class K level 1. P5 class K level 1. P2 class U level 0. P4 class H level 0. |
