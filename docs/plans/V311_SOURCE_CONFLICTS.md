# V311 source conflicts

Ben can rule on these. Each row is one where two sources print different numbers, or one printed number has two readings that do not describe the same map. The current choice is what the engine does today. A switch that is off leaves the stored game alone.

## NOTE 157 — universe and navigation

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| 1.2 Two-way warp count | 30 percent of the sectors as the total, or 30 percent extra on a connected tree | Cabal `twgs.html` option F: "Total number of two way warps... Default is 30% of the total sectors." `Big_Bang.html` says 100 percent creates as many two-way warps as there are sectors, and recommends 30 percent. A total of 30 percent cannot connect the map. GAP_MAP 1.2 reads the same 30 percent as extra lanes. | `TWO_WAY_WARP_MODE` adds extra two-way lanes equal to 30 percent of the sector count, on top of the spanning tree. A 1,000-sector game adds 300. Off, the average stays 2.7. A game that sets `avg_warps` keeps that average. |
