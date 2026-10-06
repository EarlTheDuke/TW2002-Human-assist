# Bots use rob, steal, hardware, and Terra

Slice `bots-use-rob-steal-hardware-v1`. The engine already had these verbs. The seat brain barely used them. This page is when N1, N2, and N3 may choose one. They share `SeatBrain`. The gate is cash, alignment, and the fogged legal list, not the seat letter.

Cross-links: `docs/playtests/ports/ROB_STEAL.md`, `docs/playtests/ships/SHIP_HARDWARE.md`, `docs/playtests/ships/SHIP_HARDWARE_V2.md`, `docs/playtests/ports/CLASS0_TERRA.md`, `docs/playtests/fedspace/FEDSPACE_POLICE.md`. FedSpace police is on this branch. This page does not change those rules. The brain leaves FedSpace before an Extern tow and will not attack Zyrain, Nelson, or Clausewitz.

## Bots now use

| verb | when | cash / align / exp | turns | sensible means | hidden when |
| --- | --- | --- | --- | --- | --- |
| `rob` | holds are full, at a trading port, not busted, not the sector just robbed | alignment <= -100, amount = min(vault, experience * 6) | a dock turn | the safe cap, never the whole vault, never "just to try" | `ROB_MODE` legacy |
| `steal` | empty-ish holds and a buyer port already seen | alignment <= -100, qty = min(stock, free holds, experience / 21) | a dock turn | product you can carry and sell, inside the cap | `ROB_MODE` legacy |
| `buy_equip` psychic_probe, corbomite, armid_mines, marker_beacon, cloak | at StarDock, a world already exists. After Ferrengi have been seen, one gadget is bought before the next ferry. Otherwise credits must be past 200,000 and the citadel reserve, and the ferry must not be waiting | one probe, up to 10 corbomite, 5 armids, 1 beacon, 1 cloak if Ferrengi were seen or a photon is aboard | 1 | one gadget per visit, never past credits or the ship max | `HARDWARE_MODE` legacy |
| `buy_equip` mine_disruptor | same, and a neighbor already shows mines | price plus the reserve | 1 | not a ferry-capital dump | `HARDWARE_MODE` legacy |
| `deploy_mines` armid | standing on the home sector | mines already bought | 1 | not FedSpace, not an MSL | legacy has no sweep note |
| `deploy_fighters` | helper only; the ladder does not park fighters | qty under the legal max | 1 | refused in FedSpace / MSL, so a stack never sits at 99 for a tow | — |
| `photon_missile` | Missile Frigate or Imperial StarShip, adjacent sector only | a missile aboard | attack turns | not from a merchant hull, not a far sector | `HARDWARE_MODE` legacy |
| `fire_disruptor` | a disruptor aboard, adjacent sector | — | attack turns | not a far sector | `HARDWARE_MODE` legacy |
| `cloak` | a device aboard, and every legal exit is NavHaz >= 10% | — | 0 | a clear warp is taken instead | `HARDWARE_MODE` legacy |
| `launch_beacon` | one beacon, home sector, none already here | a beacon aboard | 0 | a second beacon in the sector is refused | `HARDWARE_MODE` legacy |
| `deploy_atomic` | helper only | a detonator, landed, colonists already gone | planet-destroy turns | colonists aboard or still on the world: refuse | `HARDWARE_MODE` legacy |
| `remove_limpet` | StarDock or Class 0, a limpet is attached | fee plus the cash buffer | 0 | do not detour for it | `HARDWARE_MODE` legacy |
| `terra_colonists` | sector 1, cargo room, a world still needs bodies | free | 1 (`TERRA_LOAD_TURNS`) | never `buy_equip` colonists while Class 0 is on; never load a full hold | `CLASS0_MODE` legacy |
| attack a ship | helper only | — | — | Zyrain, Nelson, Clausewitz, and any federal occupant are refused | — |

NavHaz on an adjacent sector comes from the fogged scan. The warp list drops a hazardous exit when another exit is under 10%. The heuristic seat uses the same filter when it flees.

## Deliberate differences

- Rob and steal are not on the good-alignment trade ladder. N1/N2/N3 acceptance seats stay above -100, so they do not rob.
- Hardware buys at StarDock when a world already exists. After Ferrengi have been seen, one gadget is bought before the next ferry, as long as credits cover the price plus working capital plus the first citadel's cash. Otherwise the seat waits for 200,000 credits and does not buy while a ferry is the current job. Armids and beacons are bought once per scratchpad so a visit cannot rebuy the same stack.
- Atomic detonation and ship-vs-ship attacks are helpers the ladder does not call. The ladder must not spend a trade day hunting.
- The 99-fighter tow is the fedspace-police brain (`_avoid_fed_tow`). This slice also refuses to deploy fighters or armids in FedSpace or on an MSL.
- `_haggle_from_memory` will raise the next sell of that commodity by one small step. The live ladder does not attach `unit_price`. A counter the port refuses spends the turn (`the port lost patience`), and the acceptance rule is rejected 0.

## Plants

Each line was put back before the suite. The tests hardcode -100, experience * 6, and 99.

| plant | result |
| --- | --- |
| Alignment check forced false | `test_good_alignment_does_not_invent_rob` — rob of 3000 was returned |
| Rob amount used the vault | `test_rob_stays_inside_the_experience_cap` — `assert 80000 == 60` |
| StarDock and Class 0 check removed | `test_no_rob_at_stardock_or_class0` — rob of 1000 was returned |
| Same-sector crime check forced false | `test_no_second_rob_in_the_same_sector` — a second rob of 600 was returned |
| Hardware reserve ignored | `test_rich_hardware_does_not_buy_past_the_reserve` — bought a psychic probe |
| Photon hull check forced false | `test_photon_refused_on_a_merchant_hull_and_off_the_lane` — photon at sector 4 was returned |
| FedSpace fighter park forced false | `test_no_armids_or_fighter_park_in_fedspace` — deploy of 99 fighters was returned |
| MSL/FedSpace armid check removed | same test — lay of 5 armids was returned |
| NavHaz filter forced false | `test_navhaz_warp_prefers_the_clear_exit` — `assert 5 not in [5, 6]` |
| Psychic reading ignored | `test_psychic_reading_steps_the_next_sell` failed |
| Cloak with zero devices forced false | photon test — a cloak action was returned |
| Full-hold Terra load (early return and qty) | `test_terra_load_not_buy_equip_and_not_when_full` line 206 — `terra_colonists` qty 10 was returned |
| Verb line `rob steal` removed from the prompt | `test_prompt_and_hint_name_the_new_verbs` — `Ports:       rob steal` missing |
| Federal name check forced false | `test_federal_ship_is_not_attacked` — attack on Zyrain was returned |
| Second-beacon check forced false | `test_one_beacon_and_no_atomic_with_colonists` — a second beacon was returned |

## Scripted match

`python scripts/run_scripted_match.py --seats N3,N3,N2,N2,N1,H --seed 250925 --days 10`. Same seed, Ferrengi on, economy tw2002. Solo acceptance bars stay Ferrengi-off and were not lowered.

Before (old brain, no feature split):

| Seat | Net worth | Credits | Ship | Planets | Deaths | Rejected |
| --- | --- | --- | --- | --- | --- | --- |
| N3-P2 | 460,644 | 256,245 | cargotran | 3 | 0 | 0/0 |
| N3-P1 | 361,525 | 187,100 | cargotran | 3 | 1 | 0/0 |
| N1-P5 | 289,309 | 141,935 | merchant_cruiser | 2 | 0 | 0/0 |
| N2-P4 | 283,365 | 73,034 | cargotran | 2 | 1 | 0/0 |
| N2-P3 | 250,188 | 101,478 | merchant_cruiser | 2 | 0 | 0/0 |
| H-P6 | 181,834 | 157,064 | merchant_cruiser | 0 | 0 | 0/0 |

After:

| Seat | Net worth | Credits | Ship | Planets | Deaths | Rejected | Feature use |
| --- | --- | --- | --- | --- | --- | --- | --- |
| N3-P1 | 579,906 | 334,309 | cargotran | 3 | 0 | 0/0 | armid, cloak, corbomite, beacon, probe, terra 9 |
| N3-P2 | 355,408 | 204,741 | cargotran | 2 | 0 | 0/0 | armid, cloak, corbomite, probe, terra 18 |
| N2-P4 | 353,012 | 94,103 | cargotran | 2 | 1 | 0/0 | armid, cloak, corbomite, beacon, probe x2, launch_beacon, terra 52 |
| N2-P3 | 199,214 | 31,873 | cargotran | 2 | 0 | 0/0 | armid, corbomite, beacon, probe, deploy_mines, launch_beacon, terra 25 |
| N1-P5 | 172,366 | 28,457 | scout_marauder | 1 | 3 | 0/0 | armid, cloak, corbomite, beacon, probe x2, terra 121 |
| H-P6 | 141,220 | 117,570 | merchant_cruiser | 0 | 0 | 0/0 | none (heuristic does not buy these) |

N2 and N3 each used hardware and Terra. No seat robbed: alignment stayed above -100. N1 died three times in the shared Ferrengi match and finished in a scout. That match is not the N1 acceptance bar. The day path changed because hardware is bought before the ferry once Ferrengi are seen, so day-10 net worth is not comparable seat-for-seat. Rejected stayed 0/0.

## QC (bots rob-steal-hardware QC fixes, on 9dbe56b)

Independent QC of 7288c8e, rebased onto ferrengi-aliens-v1 (9dbe56b).

Fixes:

- **Armids on a shared lane.** Seed 250925: N1-P5 laid armids on its home, sector 14. Sector 14 is the only way into N2-P3's dead-end home, 428. The mines destroyed P3's colonist ferry three times (days 4, 4 and 5). Now `_home_is_corridor` blocks armids when any of these is true:
  - a rival planet is in the sector
  - a rival ship is there
  - a neighbour is a known dead end leading back (`known_warps == [home]` or density `warps == 1`)
  - a rival planet has been seen next door
- **Psychic probe never used (spec plant p10).** Seats bought the probe, but no live sell used the reading. `_haggle_live` now asks `min(listed*100/pct, listed*109//100)` on sells, starting from this port's listed bid. Every port's counter room is at least 110% (`PORT_HAGGLE_MIN_PCT`), so the ask can never make a port lose patience. It runs only when a probe is aboard and the last reading is under 95%.
- **Heuristic (H) seat dead ends** (fogged INFO only; the all-legacy digest is unchanged):
  - When holding cargo, H only hops to ports that buy that cargo (seed 250925 P6 had orbited 674/261/708 with 20 organics since day 2).
  - A port where it just failed to trade is skipped for that day and the next (it had also orbited the drained 572/687/744).
  - When drifting, a ruled-out port loses ties to a plain sector, but visit counts still decide first. A hard skip trapped it in the dead-end pockets 985/434/986.
  - `_flee` waits instead of warping when out of turns (seed 99: 3 "warp: out of turns" refusals).
- **FedSpace tow (the >=99-fighter stranding the fedspace ACK asked for).** Seed 20260925 on 9dbe56b: N3-P1 (200 fighters, 14 turns left) plotted from 525 to 447. The autopilot's own shortest path ran 525-323-269-1 and the turns ran out in sector 1, so the Feds towed it at Extern. Now, when a seat carries more fighters than the tow limit, its turns cannot finish the route today, and FedSpace is within reach, `_plot` takes one known warp at a time and re-checks every hop. It does not move at all if the only hops it can still afford end in FedSpace.

Tests: `tests/test_bots_use_rob_steal_hardware_qc_v1.py` (23). Plants: 29 of 29 caught. Cur's tests alone missed the StarDock crime gate and Terra take past free holds.

10-day `N3,N3,N2,N2,N1,H` net worth (9dbe56b vs 9dbe56b + QC). Deaths in brackets. Rejected 0/0.

| Seed | N3-P1 | N3-P2 | N2-P3 | N2-P4 | N1-P5 | H-P6 | Tows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 250925 before | 616,659 | 320,464 | 122,573 (3) | 263,308 | 338,175 | 64,211 | 0 |
| 250925 after | 800,260 | 308,741 | 352,445 | 449,489 | 417,141 | 605,891 (2) | 0 |
| 99 before | 342,724 | 342,273 | 188,741 (2) | 378,208 | 151,082 (1) | 93,859 | 0 |
| 99 after | 534,019 | 593,014 | 305,813 | 465,731 | 318,302 | 331,085 (2) | 0 |
| 20260925 before | 694,004 (1) | 595,661 (1) | 40,392 (1) | 345,972 | 40,344 (1) | 21,674 | 0 |
| 20260925 after | 900,763 (1) | 851,849 (1) | 35,842 (2) | 558,098 | 40,344 (1) | 118,460 (2) | 0 |

Seed 20260925: N2-P3 and N1-P5 get stuck in Scouts by Ferrengi mines on 9dbe56b both before and after QC; QC did not cause it. No seat robbed or stole: none of the acceptance seats ever reaches -100 alignment.
