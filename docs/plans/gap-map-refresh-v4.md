# gap-map-refresh-v4

Plan only. Re-read the October gap map against origin tip `39344c1`. No default was changed. The 3D map stays out.

The October grid is still the last full pass over all 171 rows: 9 Match, 34 Partial, 59 Different, 69 Missing. v3 only re-read five rows. This pass re-read the holes Note 17 named, plus the October Missing names that those holes sit next to. It did not re-grade every Partial and Different cell, so a new total of 171 would be a guess. The October numbers stay the historical grid.

## What Note 17 asked about

| Hole | At 39344c1 |
|---|---|
| 5.1 / 5.2 NavHaz and entry order | Already in, and on. Hardware mode defaults to the original path. Entering a sector checks NavHaz, then a limpet, then armids, then the sector quasar, then fighters. One percent of NavHaz is 10 damage, with a chance equal to the percent. FedSpace clears it at Extern. |
| 4.3 marker beacons, 4.4 corbomite, 4.5 cloak, 4.7 mine disruptor | Already in, and on, through that same hardware path. |
| 5.9 flee / retreat | Already in. Retreat is a verb, and a flee spends extra turns. |
| 3.12 mid-ships and 3.14 Interdictor | The names are in the ship table. The roster switch stays off (`ship-roster-stats-v1`). Not a new slice. |
| Day-1 port stock and prices | Already flagged (`port-regen-mcic-v1`, `port-price-curve-v1`). Those switches stay off. Not a new slice. |
| 1.13 dead ends | `universe-topology-v1`. The switch stays off. |

Class M citadel colonists and the class M cap of 30,000 stay Ben's choice. Random StarDock stays a written difference.

## Batch N

No build slice. Copying a rule that already has a handler would either do nothing or move the recorded games. The Batch N gate would re-run the suite that just closed on this same tip, so it is not started.
