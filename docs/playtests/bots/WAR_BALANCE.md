# War balance

Slice 66. Seed 4242, 30-day, war full, after the net-worth risk cap: N3-P1 ends at 1,027,193 in a cargotran with 8 deaths, and that seat deposited 620 fighters. War off on the same seed leaves N3-P1 at 3,563,863 in a battleship with 0 deaths. That is 29% of the war-off net worth. The other N2 and N3 seats on seeds 250925 and 4242 are already at or above 75% of their war-off net worth in those same reports.

The warfare note already required an attack to leave 25% of the fighters aboard and at least 100, and a prize of at least 1.5 times the fighter cost. Those two checks were not in the code. The failed-siege cooldown was on `siege_refusal` and the landing path never passed the day.

## Decision

1. No new mode. `BOTS_WAR_MODE` stays the switch. Legacy does not read the new checks.
2. After the estimate survives and the 40% net-worth cap passes, refuse unless fighters left are at least 100 and at least 25% of the fighters brought.
3. Refuse unless the seen treasury is at least 1.5 times the credits of the fighters the estimate spends. A missing treasury counts as 0. A fight that spends nothing still passes.
4. A siege that does not leave this seat landed on that planet, or owning it, records `war_fail_day`. The existing 2-day cooldown then applies.
5. Engine rules stay as they are. The legacy pin stays `9b607d3dae940c0b1a69f6d7`.
6. A home hit is answered once. Arriving acks that event, so the same notice does not turn the trade route around again.

Seed 4242 30-day on dac501d, both columns rejected 0/0. War full 719s. War off 729s, save identical.

| Seat | War full | War off | Share |
| --- | --- | --- | --- |
| N3-P1 | 2,599,336 battleship, 0 deaths | 3,382,543 battleship, 0 deaths | 77% |
| N2-P3 | 1,331,157 cargotran, 2 deaths | 1,846,217 cargotran, 1 death | 72% |
| N2-P4 | 651,391 cargotran, 0 deaths | 625,055 cargotran, 0 deaths | 104% |
| N3-P2 | 518,712 scout, 13 deaths | 629,982 cargotran, 0 deaths | 82% |

N2-P3 is the miss on `dac501d`. It made no ship attacks. It laid 57 armids, deployed fighters 4 times, and warped 1,353 times against 474 with war off, with 1,125 trades against 1,459.

Seed 4242 30-day on `1790d97`, war full, 1567s, rejected 0/0, save identical. The home ack is what changed. Shares are against the war-off column above.

| Seat | War full | Share of war off |
| --- | --- | --- |
| N3-P1 | 2,528,732 battleship, 0 deaths | 75% is 2,536,907, so this is 8,175 short |
| N2-P3 | 1,696,805 cargotran, 1 death | 92% |
| N2-P4 | 626,310 cargotran, 0 deaths | 100% |
| N3-P2 | 483,682 scout, 10 deaths | 77% |

## Bars

Every N2 and N3 seat stays at or above 75% of its war-off day-30 net worth on seeds 250925 and 4242. Each 30-day war-on match still has at least one planet attack. Rejected 0/0. Save identical.
