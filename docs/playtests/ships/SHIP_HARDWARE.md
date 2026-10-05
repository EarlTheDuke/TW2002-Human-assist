# Ship hardware (mines, photons, cloaks, disruptors)

Rules table first, then what the engine does. Sources under `C:\Users\sugar\tw2002_reference\` (gap map 4.5, 4.7-4.10, 5.3, 5.17-5.18; cabal formulas.html density + armid 50%; Bible Hardware Emporium prices and caps; EIS HardwareMenu.html; Gypsy / Iago; TEDIT samples). Target TWGS 3.11; MBBS breaks ties. Marks: CONFIRMED / SOURCE-CONFLICT / UNVERIFIED.

Today kept as `HARDWARE_MODE = "legacy"`: armid hits = min(count, rand 1..10) x ARMID_DAMAGE 100; photon = same-sector player fighter-scramble; no cloak; no disruptor; no limpet-removal service. Pin legacy in bars/goldens so old behaviour does not drift.

## Rules table

| # | rule | original | mark and source | this slice (HARDWARE_MODE tw2002) |
| --- | --- | --- | --- | --- |
| **Armid mines (gap 5.3)** | | | | |
| h1 | Detonation fraction | On hostile entry, if armids detonate, floor(count/2) mines blow (50% rounding down). | CONFIRMED: cabal formulas.html "50% of the mines will detonate, rounding down"; Bible "half of them will blow up". | Built: `hits = count // 2` when count >= 1 and detonation triggers. Own/corp/ally mines still skip. |
| h2 | Damage per mine | Bible: 20 points of damage per detonating mine. | SOURCE-CONFLICT: our legacy uses 100 dmg x random 1..10 hits; no separate v3.11 per-mine number beyond Bible. | Built: `K.ARMID_DAMAGE_TW2002 = 20`. Legacy keeps `K.ARMID_DAMAGE = 100` and random 1..10. |
| h3 | Sector mine cap | 99 mines per sector (old versions / SECTOR_FIGHTER_MODE). | CONFIRMED in shape (gap 4.8). | Unchanged under SECTOR_FIGHTER_MODE. |
| h4 | Own / corp / ally | Own and corp ships do not set off the mines (most of the time). | CONFIRMED: EIS HardwareMenu. | Built: skip own/corp/ally (existing). |
| **Photon missile (gap 4.10 / 5.18)** | | | | |
| h5 | Who may buy/fire | Only Missile Frigate (max 10) and Imperial StarShip (max 5). | CONFIRMED: Bible, HardwareMenu, MBBS. | Built: existing `max_photons` on those hulls; fire refuses other hulls under tw2002. |
| h6 | Target | Fired at an **adjacent** sector, not a same-sector player. | CONFIRMED: Bible adjacent rule; Gypsy fire-into-adjacent. | Built: `photon_missile {"target": <sector_id>}` must be a direct warp neighbour. Legacy keeps same-sector player scramble. |
| h7 | Wave effect | For Photon Wave duration: neutralize sector mines and sector fighters; damp Quasar / CCC / Interdictor on planets there; decloak every cloaked ship in that sector. L5+200 shields still ignores damp. | CONFIRMED: HardwareMenu + planet handbook / existing planet photon damp. Duration: TEDIT sample "Photon Wave Dur.: 1 seconds". | Built: `K.PHOTON_WAVE_DURATION = 1` day-tick of sector damp (`Sector.photon_wave_remaining`). Mines/fighters inert while > 0; planet damp marked for approach; immediate decloak. |
| h8 | Carried-photon blast | Carrying a photon into offensive fighters or mines can detonate the missile and cost the rest of the day's turns. | CONFIRMED: Bible. | Built: on warp entry with hostile armids or hostile offensive fighters while `photon_missiles > 0`, all photons aboard are lost and `turns_today = turns_per_day`. Documented turn-based mapping (no partial-day clock). |
| h9 | FedSpace | Existing FedSpace weapon penalty / RANK_MODE protection. | Partial already. | Keep / align existing FedSpace photon/attack rules; no new Fed invention. |
| h10 | Price | Photon ~12,000. | CONFIRMED in shape (existing constant). | Unchanged `PHOTON_MISSILE_COST = 12_000`. |
| **Cloaking device (gap 4.5)** | | | | |
| h11 | Buy | StarDock Hardware Emporium. | CONFIRMED: Bible, HardwareMenu. | Built: `buy_equip item=cloak`. |
| h12 | Price | Bible 25,000. TEDIT sample 6,250. | SOURCE-CONFLICT. | Built: `K.CLOAK_COST = 25_000` (Bible). Easy to flip. |
| h13 | Cap | Max 5 per ship. | CONFIRMED: Bible / HardwareMenu / gap 4.17. | Built: `K.CLOAK_MAX = 5`; buy refuses past cap. |
| h14 | Activate | Consumes one cloak; one-shot item. | CONFIRMED: HardwareMenu / Gypsy. | Built: action `cloak` (no args); decrements stock; sets `ship.cloaked`. |
| h15 | Hide | Density 0 + anomaly YES; hidden from corp Member Location; unattackable while cloaked. | CONFIRMED: cabal density table; HardwareMenu; Iago invulnerable while cloaked. | Built: density skips cloaked ships but sets anomaly; observation hides sector/location from others including corpmates; attack / photon-as-player refuse. |
| h16 | Fail rate | TEDIT Cloaking FailRate 3%; after ~24 hours of use detection risk rises (HardwareMenu / Gypsy). | CONFIRMED FailRate sample; 24h CONFIRMED in shape. | Built: `K.CLOAK_FAIL_RATE = 0.03`. Map "24 hours" to remaining cloaked across a day tick: on `tick_day`, if still cloaked, roll fail (3%) and decloak on failure. Documented mapping. |
| h17 | Photon decloak | Photon into the sector decloaks. | CONFIRMED: gap 4.5 / HardwareMenu sense. | Built: sector photon wave decloaks everyone there. |
| **Mine disruptor (gap 4.7)** | | | | |
| h18 | Buy / cap | Max 10 aboard. | CONFIRMED: Bible. | Built: `buy_equip item=mine_disruptor`; `K.DISRUPTOR_MAX = 10`. |
| h19 | Fire | From an adjacent sector; clears up to 12 mines in the target. | CONFIRMED: Bible. MBBS "average of 6 or 7" is SOURCE-CONFLICT. | Built: `fire_disruptor {"target": <sector_id>}`; clears `rng.randint(1, 12)` mines (armid + limpet counts), capped by sitting mines. Ceiling 12. |
| h20 | Price | Bible ~40,000; TEDIT 1,500; MBBS ~6,000. | SOURCE-CONFLICT. | Built: `K.DISRUPTOR_COST = 40_000` (Bible). |
| h21 | Effect | Deactivates limpets and/or armids in that sector (sweeper). | CONFIRMED: HardwareMenu. | Built: reduces mine deployment counts in the target sector. |
| **Limpet removal (gap 4.9)** | | | | |
| h22 | Service | StarDock removes an attached limpet for a fee. | CONFIRMED service exists; fee TEDIT sample 1,250 UNVERIFIED as 3.11 default (only number found). | Built: `remove_limpet` at StarDock; `K.LIMPET_REMOVAL_COST = 1_250`. |
| h23 | One limpet | Only one limpet attached at a time. | CONFIRMED. | Unchanged (existing attach). |
| h24 | Query | `query_limpets` stays. | Already built. | Unchanged. |
| **Mode / caps** | | | | |
| h25 | HARDWARE_MODE | New switch. | — | `tw2002` (default) enables the rules above; `legacy` pins today's bars. |
| h26 | Caps refuse | buy_equip / deploy refuse past per-ship caps; legal list matches handler. | — | Cloaks 5, disruptors 10; photons/mines/genesis already on SHIP_SPECS. |

### Deliberate differences

- No NavHaz and no full entry-order reorder (NavHaz then limpet then armid then quasar then fighters then avoid). That is **ship-hardware-v2**.
- No corbomite, marker beacons, psychic probe, or atomic-detonator redesign (v2).
- Genesis empty-start seed 2500 stays as already documented in PLANET_ECONOMY_LIMITS.md.
- Cloak "24 hours" maps to one day-tick fail check while still cloaked (turn-based), not a real-time clock.
- Photon wave "1 second" maps to one day-tick of `photon_wave_remaining` (named constant).
- Carried-photon blast spends the rest of the day's turns (`turns_today = turns_per_day`) rather than a wall-clock day end.
- Disruptor clears a uniform random 1..12 mines (Bible ceiling), not an MBBS average curve.
- Limpet removal fee uses the only TEDIT sample found (UNVERIFIED as 3.11 default).

## What the engine does (HARDWARE_MODE tw2002)

- `K.HARDWARE_MODE` defaults to `tw2002`. `legacy` keeps armid random/100, same-sector player photon, and hides cloak / disruptor / remove_limpet (not in the legal list, the ship view, or the harness `/rules` verbs; handlers refuse).
- New actions: `cloak`, `fire_disruptor`, `remove_limpet`. Photon target becomes an adjacent sector id under tw2002.
- Fog / INFO_MODE: cloaked ships dens 0 + anomaly; limpets still anomaly; armid dens 10 / limpet dens 2 unchanged. Photon damp and cloak state reach seats only through fogged observation / events.
- Seat brains and prompts learn the verbs and expert habits (cloak with a photon; disrupt before a mined lane; photon adjacent then warp in). Brains stay rejected 0; acceptance bars still pass.

## Out of scope (ship-hardware-v2)

Corbomite, marker beacons, psychic probe, atomic-detonator redesign, NavHaz + full hazard entry order, genesis empty-start changes.

## Planted bugs (caught)

| # | planted bug | where | caught by |
| --- | --- | --- | --- |
| p1 | cloak without owning one | legal + handler | test_plant_cloak_without_owning |
| p2 | cloak still attackable | legal + handler | test_plant_cloak_still_attackable |
| p3 | density shows cloaked ship as 40 | density_reading | test_plant_cloaked_density_not_forty |
| p4 | photon from wrong hull | legal + handler | test_plant_photon_from_wrong_hull |
| p5 | photon same-sector player under tw2002 | handler | test_plant_photon_same_sector_player_refused |
| p6 | photon does not neutralize mines/fighters | handler + warp | test_plant_photon_clears_mines_fighters |
| p7 | disruptor from non-adjacent | legal + handler | test_plant_disruptor_non_adjacent |
| p8 | disruptor clears >12 | handler | test_plant_disruptor_clears_at_most_12 |
| p9 | armid still 100 dmg under tw2002 | handler | test_plant_armid_not_100_under_tw2002 |
| p10 | limpet removal free / not at StarDock | legal + handler | test_plant_limpet_removal_needs_fee_and_stardock |
| p11 | legal list offers photon with 0 missiles | legal | test_plant_legal_photon_with_zero_missiles |
| p12 | carried photon does not blast into offensive figs | warp handler | test_plant_carried_photon_blast |
| p13 | legacy still offers cloak / half-armid | legal + armid helper | test_plant_legacy_keeps_old_armid_and_hides_gadgets |

## Delivered

- Rules table, HARDWARE_MODE switch (default `tw2002`; `legacy` pinned in the old goldens/bars), 13 planted bugs caught, seats legal (rejected 0).
- Before/after `scripts/run_scripted_match.py --seats N3,N3,N2,N2,N1,H --seed 250925 --days 10`, default modes. Before = origin f243af2 (rob-steal QC fixes), after = this slice. JSON byte-identical (bots do not yet buy photons/cloaks/disruptors in this match; no hostile armids on their lanes):

| # | Seat | Net worth before | Net worth after | Ship | Planets | Rejected | Exceptions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | N3-P1 | 540,933 | 540,933 | battleship | 3 | 0/0 | 0 |
| 2 | N3-P2 | 387,789 | 387,789 | battleship | 3 | 0/0 | 0 |
| 3 | N2-P4 | 343,561 | 343,561 | cargotran | 2 | 0/0 | 0 |
| 4 | N1-P5 | 331,595 | 331,595 | merchant_cruiser | 2 | 0/0 | 0 |
| 5 | N2-P3 | 202,320 | 202,320 | cargotran | 2 | 0/0 | 0 |
| 6 | H-P6 | 196,161 | 196,161 | merchant_cruiser | 0 | 0/0 | 0 |
