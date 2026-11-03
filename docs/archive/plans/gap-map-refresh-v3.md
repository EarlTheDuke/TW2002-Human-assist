# gap-map-refresh-v3

Plan only. Re-read the October 10 gap map against origin tip `7ed755f`. No default was changed. The 3D map stays out.

The October grid is still the last full pass over all 171 rows: 9 Match, 34 Partial, 59 Different, 69 Missing. Later slices added rules without editing those cells, so that Missing count is high. The five rows Note 16 named were re-read in the engine. The other cells were not re-graded one by one, so this note does not invent a new total.

## The five named rows

| Row | October status | At 7ed755f |
|---|---|---|
| 1.13 Bubbles, tunnels, dead ends | Missing | Still missing. `universe.py` refuses a sector with no way out, and it refuses a one-way that leaves no path back to sector 1. There is no bubble, tunnel, or black-hole pass. |
| 1.3 Course length | Missing | Not missing. A plotted course stops at 60 hops (`PLOT_COURSE_MAX_DEPTH` 10, times 6). The Big Bang setting of 45 is unverified for TWGS 3.11. Not a slice. |
| 1.19 Fighters and mines per sector | Missing | Already in. 5,000 fighters, 30,000 when a planet is there, and 99 mines. |
| 1.17 Nightly Extern cleanup | Missing | Already in. The class-0 day tick runs the Extern sweep, and unmanned ships in FedSpace can be repossessed. That switch defaults on. |
| 1.9 Ferrengal | Missing | Already in for the home sector: 50 mines and 1,000 fighters, when Ferrengi mode is on (the default). The handbook quasar is not built. Ferrengal looks for a dead end and usually cannot find one, because generation forbids them. |

Class M citadel colonists (1,000 vs 1,000,000) and the class M cap of 30,000 stay Ben's choice. Random StarDock stays a written difference. Ship prices in section 3 and the economy scale in section 2 are still source conflicts. They are not new slices.

## Batch M

1. `universe-topology-v1`. New flag `UNIVERSE_TOPOLOGY_MODE`, default `legacy`. Legacy keeps today's graph, so the pin stays put. On, Big Bang style lanes are allowed: a sector may have no way out, a one-way may have no path back to sector 1, and a few tunnels can join distant sectors. Bubbles are a cluster with one way in. Bots and `plot_course` must accept "no route" instead of assuming every sector can reach sector 1. Ferrengal can then sit on a real dead end.
2. `batch-m-gate-v1`. Full suite and the two 30-day digests after that slice. Add the new flag to the live-profile helper list. The profile stays off.
