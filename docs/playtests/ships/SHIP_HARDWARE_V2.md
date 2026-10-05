# Ship hardware v2 (NavHaz, corbomite, beacons, psychic probe, atomic detonator, entry order)

This is the follow-on to `SHIP_HARDWARE.md` (v1), behind the same switch: `K.HARDWARE_MODE` (`tw2002` is the default; `legacy` pins today's behaviour). Sources are under `C:\Users\sugar\tw2002_reference\`: the gap map; the TWGS docs (twgs.html price list); the TW2002 Bible Hardware Emporium; EIS HardwareMenu.html; cabal formulas.html for density and limpets; the MBBS manual and Misc_shipodds; Gypsy and Iago ship and command data. Target TWGS 3.11, with MBBS breaking ties. Marks are CONFIRMED / SOURCE-CONFLICT / UNVERIFIED.

**Legacy (`HARDWARE_MODE = "legacy"`):** none of the five items are sold. `launch_beacon` and `deploy_atomic` do not appear in the legal list or the harness `/rules` verbs, and their handlers keep the old "unsupported action" reply. Sector entry keeps the old order (limpet, armid, fighters, then a post-move quasar). NavHaz never rolls, the scanner keeps the old navhaz behaviour, and planet destroy step 2 needs no detonator. The legacy bars and goldens are pinned so nothing drifts.

## Rules table

Row numbers match the `vN` references in the code comments.

| # | rule | original | mark and source | this slice (HARDWARE_MODE tw2002) |
| --- | --- | --- | --- | --- |
| **Corbomite transducer** | | | | |
| v1 | Price | TWGS twgs.html: 1,000 per unit. The Bible table reads like 100. | SOURCE-CONFLICT (TWGS taken as the 3.11 default). | `K.CORBOMITE_COST = 1_000`. |
| v2 | Cap | 1,500 units per ship. | CONFIRMED: Bible / HardwareMenu. Per-hull caps UNVERIFIED (no per-hull table found). | `K.CORBOMITE_MAX = 1_500` on every hull except the pod (0). Buy refuses past it, and legal `max_by` matches. |
| v3 | Effect | When your ship is destroyed, the transducer blasts the ship that killed you. MBBS: 1,500 units "will blow 30,000 fighters off of the attacker". Misc_shipodds: "30000 battle points". | CONFIRMED (both give 20 per unit). | `K.CORBOMITE_DAMAGE_PER_UNIT = 20`. Fires from `combat._destroy_ship` with damage to shields, then fighters. If both reach 0 the killer dies (reason `corbomite`). No chain. Also handles a Ferrengi killer. |
| v4 | Trigger scope / hidden | It answers the ship that destroyed you. Undetectable to rivals. | Scope UNVERIFIED for mines/NavHaz (no source says they trigger it). Hidden is CONFIRMED in shape. | Fires only for reason combat/ferrengi with a killer. Never in rival views or scans; shown only in your own ship view. Net worth counts it at cost. |
| **Marker beacons** | | | | |
| v5 | Price / cap | 100 each. "Beacon Max" in the ship data (Merchant Cruiser 50, Imperial StarShip 150, pod none). | CONFIRMED: TWGS price; Gypsy / Iago ship tables. | `K.BEACON_COST = 100`, `K.BEACON_MAX_BY_HULL`. Buy refuses past the cap. |
| v6 | Launch | Release a beacon into the current sector with a message. | CONFIRMED: Gypsy "Release Beacon" (41-character message). | New verb `launch_beacon {"message"}` uses 1 beacon. `K.BEACON_MESSAGE_MAX = 41`. |
| v7 | Turn cost | Not listed as a turn-using command. | UNVERIFIED. | `K.BEACON_TURNS = 0`. |
| v8 | Second beacon | A beacon launched into a sector that already has one: both explode. | CONFIRMED: Bible / HardwareMenu. | Both are removed. The launcher gets BEACON_DESTROYED. |
| v9 | Density / visibility | +1 density. The message is seen on entry or scan; the owner is not shown. | CONFIRMED: cabal density table; Gypsy. | `K.DENSITY_PER_BEACON = 1`. `Sector.beacon` is the text only. It shows in the current-sector view, holo scans and the remembered adjacent view. BEACON_* events go to the actor only. |
| **Psychic probe** | | | | |
| v10 | Price / cap | 2,500, one per ship. | CONFIRMED: TWGS price; Slice-10 record "PsyProbe * 1". | `K.PSYCHIC_PROBE_COST = 2_500`, `K.PSYCHIC_PROBE_MAX = 1`. |
| v11 | Reading | After a trade, tells you what percent of the port's limit your price was. | CONFIRMED in shape: HardwareMenu. Exact formula UNVERIFIED. | After a successful trade, an actor-only `PSYCHIC_PROBE` event. pct = unit / haggle bound when you sell, bound / unit when you buy (`haggle_bound`). The listed price is captured before the trade executes. |
| v12 | Private | Only the owner learns it. | CONFIRMED in shape. | The event is actor-only and never appears in rival observations. |
| **Atomic detonator (redesign)** | | | | |
| v13 | Price | TWGS 60,000; Iago 15,000. | SOURCE-CONFLICT (TWGS taken). | `K.ATOMIC_DETONATOR_COST = 60_000`. |
| v14 | Cap | Max 5 aboard. | CONFIRMED: Bible. | `K.ATOMIC_DETONATOR_MAX = 5`. |
| v15 | planet_destroy last step | "Try to Destroy Planet: first you purchase Atomic Detonators". | CONFIRMED: Gypsy. | Under tw2002, step 2 of `planet_destroy` needs and uses one detonator (checked in `planet_destroy_reason`, so legal equals handler). Step 1 (killing colonists) is unchanged. Legacy needs none. |
| v16 | Use | Land on the planet and set the detonator. | CONFIRMED. | `deploy_atomic {"planet_id"}` (existing ActionKind) is dispatched only under tw2002 and requires being landed. A hostile planet needs 0 fighters and 0 shields. Your own or an unowned planet is allowed (P-busting). Corp-mate or ally planets are refused. |
| v17 | Colonists alive | The blast takes your ship with it. | CONFIRMED: Bible (ship lost). Planet left standing is UNVERIFIED. | The detonator is used up, your ship is destroyed (reason `atomic_detonator`), and the planet stays. |
| v18 | Empty planet / alignment | Planet destroyed. Spec: alignment -50. | Destroy CONFIRMED. Alignment is SOURCE-CONFLICT: spec -50 vs the RANK_MODE tw2002 x7 planet-destroy rule (-1 align / +50 xp). | The planet is removed by the shared `_remove_planet` (same path as planet_destroy). -50 alignment under RANK legacy; RANK tw2002 keeps x7 so both destroy paths agree. NavHaz +10. |
| v19 | `atomic_mines` port nuke | Not in the original (this game's invention). | n/a | Kept: `K.ATOMIC_MINES_PORT_NUKE = True`, because it is the only port-kill path. False under tw2002 retires it: not sold, deploy refused, hidden from choices (`K.atomic_mines_sold()`). |
| **NavHaz** | | | | |
| v20 | Storage | NavHaz is a sector percentage. | CONFIRMED: cabal / MBBS. | The existing `Sector.nav_hazard`, read as an integer %, capped at `K.NAVHAZ_MAX_PCT = 100`. |
| v21 | Hit chance / damage | Odds equal the %. Each 1% does 10 damage. | CONFIRMED: cabal glossary. | On warp entry: hit if rng < N%, damage N × `K.NAVHAZ_DAMAGE_PER_PCT` (10) to shields then fighters. Death when both are 0 (reason `navhaz`). No RNG is drawn at 0%. |
| v22 | Source | "Each planet destroyed produces 10% Haz". | CONFIRMED: MBBS manual. | `K.NAVHAZ_PER_PLANET_DESTROYED = 10` on planet_destroy and on a detonator kill. |
| v23 | Dispersion | MBBS: "generally it'll be reduced by 3%" each night. FedSpace is cleaned. | MBBS (tie-breaker); TWGS 3.11 value UNVERIFIED. | Day tick: FedSpace set to 0, other sectors -`K.NAVHAZ_DISPERSION_PER_DAY` (3). |
| v24 | Density / scan | 21 density per %. | CONFIRMED: cabal density table (210 = destroyed planet). | `K.DENSITY_PER_NAVHAZ_PCT = 21`. Scanner `navhaz` reports the real value under tw2002. Sector view shows `nav_hazard_pct` when above 0. |
| v25 | StarDock | StarDock never carries NavHaz. | CONFIRMED in shape (revision history). | `add_navhaz` refuses the StarDock sector. |
| **Entry order and follow-ups** | | | | |
| v26 | Entry order | NavHaz → limpet → armid → sector quasar → fighters → avoid prompt. | CONFIRMED: spec / Bible order. | `_apply_sector_hazards` uses this order under tw2002. Processing stops if the ship is dead after armids. The sector quasar fires before fighters, and the post-move quasar in `_handle_warp` is skipped under tw2002. Legacy keeps the old order. |
| v27 | One limpet | A new limpet makes the old one fall off. Only one attaches per entry. | CONFIRMED: cabal formulas.html. | Only one limpet attaches per entry, and `drop_other_limpets` removes the earlier one. |
| v28 | Avoid prompt | After mines: "you will be asked whether you want to avoid the sector". | CONFIRMED: Bible. | Actor-only `HAZARD_AVOID_PROMPT` after entry when hostile mines were present (no photon wave). `plot_course` execute stops there. No avoid list is kept (deliberate). |
| v29 | Strip on loss | The escape pod carries none of the gadgets. | CONFIRMED in shape: Bible pod. | v1 follow-up: losing your ship under tw2002 zeroes the v2 items, cloaks, disruptors and cloaked state. |
| v30 | Mode / legal | One switch. Legal list equals handlers. | — | `HARDWARE_MODE` tw2002 enables all of the above. `legacy` hides `launch_beacon`/`deploy_atomic` (legal list, ship view, harness `/rules` verbs) and keeps legacy behaviour byte-identical. |

### Deliberate differences

- There is no persistent avoid list. The prompt only stops autopilot; the seat decides next.
- No beacon shooting and no TransWarp-into-beacon (both exist in the original; TransWarp is out of scope).
- Corbomite answers only ship-to-ship kills (combat / Ferrengi). It does not answer mines, NavHaz, quasars or detonators. There is no corbomite chain.
- Corbomite cap is a flat 1,500 for every hull (no per-hull source found).
- `atomic_mines` port nuke kept behind `K.ATOMIC_MINES_PORT_NUKE` (default True) because it is the only port-kill path. This is our invention, not original.
- A detonator set off with colonists alive leaves the planet intact (UNVERIFIED).
- Detonator alignment keeps the RANK tw2002 x7 rule (SOURCE-CONFLICT, row v18). -50 applies only under RANK legacy.
- NavHaz dispersion is the MBBS 3% per night, applied on day ticks (TWGS value UNVERIFIED; named constant).
- Beacon launch costs 0 turns (UNVERIFIED).
- v1 follow-up: losing your ship under tw2002 now strips cloaks, disruptors and cloaked state as well as the v2 items (escape pod starts bare).
- Prices: TWGS picked over the Bible/Iago where they conflict (corbomite 1,000; detonator 60,000).

## What the engine does (HARDWARE_MODE tw2002)

- New items for `buy_equip` at StarDock: `corbomite`, `marker_beacon`, `psychic_probe`, `atomic_detonator`. Legal `max_by` matches the caps above.
- New verb `launch_beacon`. `deploy_atomic` is enabled. Both are in the legal list only when usable, and the legal list equals the handlers.
- New events: NAVHAZ_HIT, CORBOMITE_BLAST, BEACON_LAUNCHED, BEACON_DESTROYED, PSYCHIC_PROBE, ATOMIC_DETONATOR, HAZARD_AVOID_PROMPT. Beacon, psychic and avoid-prompt events go to the actor only. NAVHAZ_HIT and ATOMIC_DETONATOR by a cloaked actor are hidden from rivals (extends the v1 cloak filter).
- Fog: corbomite, probe and detonator counts appear only in your own ship view. Beacon text shows, the beacon owner never does.
- Seat brains/prompts: equipment lines, verb docs and an entry-order note. Seat acceptance REQUIRED_ARGS cover `launch_beacon` and `deploy_atomic`.

## Out of scope

FedSpace changes, Class 0 ports, TransWarp (including beacon lock), avoid lists, beacon attack.

## Planted bugs

Each plant was a real code mutation applied to the engine, run against `tests/test_ship_hardware_v2.py`, then reverted. The table is filled from that run.

| # | planted bug (real mutation) | file | result | caught by |
| --- | --- | --- | --- | --- |
| p22 | legacy rolls NavHaz on entry | `runner.py` | caught | test_plant_legacy_hides_v2 |
| p23 | legacy quasar moved before fighters (legacy order drift) | `runner.py` | caught (missed on the first run; test added) | test_plant_legacy_entry_order_unchanged |

23 plants: 22 caught on the first run. p23 (legacy entry-order drift) was MISSED at first, so `test_plant_legacy_entry_order_unchanged` was added, and the re-run caught it. Final: 23/23 caught.

## Delivered

- Rules table v1-v30 with marks. Deliberate differences listed. Everything sits under the existing `HARDWARE_MODE` switch (default `tw2002`; `legacy` hides `launch_beacon`/`deploy_atomic`, and the legacy goldens/bars are unchanged). The `ATOMIC_MINES_PORT_NUKE` switch is documented. 23 planted bugs, all caught (one after adding a test). Legal list equals handlers. Brains rejected 0.
- Collateral test updates: the parity_s4 builder covers `launch_beacon`; the parity_s6 harness verb count is 55; planet_destruction_v1 and the experience_alignment scenario give the attacker one detonator for step 2 (all numbers unchanged); scanners legacy-fog golden digests were refreshed (diff checked: only the four new own-ship keys and the two new legal entries); planet_invariants_fuzz players carry 5 detonators.
- Before/after `scripts/run_scripted_match.py --seats N3,N3,N2,N2,N1,H --seed 250925 --days 10`, default modes. Before = origin e48076b (ship-hardware-v1 QC fixes), after = this slice. The JSON is byte-identical. The bots never buy the v2 items. Map generation gives no sector NavHaz and no planet is destroyed, so `apply_navhaz` never draws RNG. No hostile mines or quasar planets sit on their lanes, so the reorder and the avoid prompt never fire. The psychic probe is never aboard.

| # | Seat | Net worth before | Net worth after | Ship | Planets | Rejected | Exceptions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | N3-P1 | 540,933 | 540,933 | battleship | 3 | 0/0 | 0 |
| 2 | N3-P2 | 387,789 | 387,789 | battleship | 3 | 0/0 | 0 |
| 3 | N2-P4 | 343,561 | 343,561 | cargotran | 2 | 0/0 | 0 |
| 4 | N1-P5 | 331,595 | 331,595 | merchant_cruiser | 2 | 0/0 | 0 |
| 5 | N2-P3 | 202,320 | 202,320 | cargotran | 2 | 0/0 | 0 |
| 6 | H-P6 | 196,161 | 196,161 | merchant_cruiser | 0 | 0/0 | 0 |
