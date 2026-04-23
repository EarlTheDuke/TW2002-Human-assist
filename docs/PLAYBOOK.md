# TW2K match LLM playbook (reference)

Optional encyclopedia for **match** agents when `TW2K_HINT_LEVEL=minimal` — the live
`SYSTEM_PROMPT` points here instead of inlining this material. Nothing here is a
mandatory script; win conditions and engine rules in the system message + observation
remain authoritative.

---

## Opening progression (one common path)

Many commanders follow:

1. **TRADE** — build a loop of two ports with opposite buy/sell patterns; run it for profit.
2. **UPGRADE** — at StarDock (sector 1), buy a bigger ship when affordable. A CargoTran at ~43.5k gives far more holds than the starter hull.
3. **COLONIZE** — `buy_equip` genesis + colonists; warp outside FedSpace; `deploy_genesis` → `land_planet` → `assign_colonists` → `liftoff`.
4. **FORTIFY** — `build_citadel` on owned planets; advance levels over days.
5. **WIN** — compound production; out-trade or eliminate rivals; 100M credits, last alive, or time net worth.

You may skip or reorder steps if another strategy fits the board.

---

## Day-1 worked example (gold JSON)

Starting state: sector 1 (StarDock), ~20k cr, merchant_cruiser, turns 0/N.

**Turn 1** — scan to learn neighbor ports AND set three horizons:

```json
{"thought":"Map ports; commit to my plan.","scratchpad_update":"at sector 1, scanning",
 "goals":{"short":"scan; then warp to the best SELL port in warps_out",
          "medium":"find one org pair, run 5 round-trips, reach 45k, buy CargoTran",
          "long":"CargoTran day 1, Genesis-deploy dead-end sector day 2, Citadel L2 day 3"},
 "action":{"kind":"scan","args":{}}}
```

**Turn 2** — `warp` toward the seller port.

**Turn 3** — `trade` buy to fill holds.

**Turn 4** — `warp` to buyer.

**Turn 5** — `trade` sell to close the round trip.

Repeat until upgrade threshold, then return to StarDock for `buy_ship`.

---

## Trading (detail)

- Port codes use letters F-O-E for (fuel_ore, organics, equipment). `B`=port buys, `S`=port sells.
- `trade` args: `{"commodity":"fuel_ore|organics|equipment", "qty":<int>, "side":"buy|sell", "unit_price":<optional int>}`.
- Haggling: buyer offers below list, seller asks above list. Rejected asks settle at list price.
- Aggressive haggles (e.g. 20–30% past list) are often attempted by strong traders; adjust to your risk tolerance.
- Let drained ports rest (~50% stock) so prices recover.

---

## StarDock price sheet

Equipment — `buy_equip {"item":"<name>","qty":<int>}`:

| item | note |
|------|------|
| fighters | 50 cr each |
| shields | 10 cr per point |
| holds | +1 cargo (varies by hull) |
| armid_mines | 100 cr |
| limpet_mines | 250 cr |
| atomic_mines | 4,000 cr |
| photon_missile | 12,000 cr |
| ether_probe | 5,000 cr |
| genesis | 25,000 cr |
| colonists | 10 cr each |

Ships — `buy_ship {"ship_class":"<key>"}` (25% trade-in). Examples: `merchant_cruiser`, `cargotran`,
`scout_marauder`, `missile_frigate`, `colonial_transport`, `battleship`, `havoc_gunstar`,
`corporate_flagship` (corp), `imperial_starship` (alignment gate).

---

## Colonize — planet / citadel loop

Typical first planet (abbreviated):

1. `buy_equip` genesis + colonists at StarDock  
2. Warp to a quiet sector outside FedSpace  
3. `deploy_genesis` (4 turns)  
4. `land_planet` → `assign_colonists` pools → `build_citadel` when requirements met → `liftoff`  

Citadel tier costs and durations are in engine constants; L4 unlocks transwarp.

---

## Multi-planet expansion

**Cluster** — planets near each other: cheap ferries, mutual defense, good for corps.  
**Distributed** — spread across the map: risk spread, separate trade loops.

---

## Orphaned planets

When a rival is eliminated, solo-owned planets may become ownerless (`orphaned_planets` in observation).
`warp` → `land_planet` → `claim_planet` can inherit citadel + stockpile without a new Genesis (corp-owned
planets stay with the corp).

---

## Diplomacy & corps (long-form)

- `hail`, `broadcast`, `propose_alliance` / `accept_alliance` / `break_alliance`
- `corp_create` (500k at StarDock), invites, treasury deposit/withdraw rules
- See observation `rivals`, `corp`, `inbox` for live state

---

## Goal discipline (full-hint style)

When using `TW2K_HINT_LEVEL=full`, the system prompt treats goals as a commitment device across turns.
Under `minimal`, goals are advisory notes only — same JSON schema, softer psychology.
