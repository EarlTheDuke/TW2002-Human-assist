# War balance

Slice 66. Seed 4242, 30-day, war full, after the net-worth risk cap: N3-P1 ends at 1,027,193 in a cargotran with 8 deaths, and that seat deposited 620 fighters. War off on the same seed leaves N3-P1 at 3,563,863 in a battleship with 0 deaths. That is 29% of the war-off net worth. The other N2 and N3 seats on seeds 250925 and 4242 are already at or above 75% of their war-off net worth in those same reports.

The warfare note already required an attack to leave 25% of the fighters aboard and at least 100, and a prize of at least 1.5 times the fighter cost. Those two checks were not in the code. The failed-siege cooldown was on `siege_refusal` and the landing path never passed the day.

## Decision

1. No new mode. `BOTS_WAR_MODE` stays the switch. Legacy does not read the new checks.
2. After the estimate survives and the 40% net-worth cap passes, refuse unless fighters left are at least 100 and at least 25% of the fighters brought.
3. Refuse unless the seen treasury is at least 1.5 times the credits of the fighters the estimate spends. A missing treasury counts as 0. A fight that spends nothing still passes.
4. A siege that does not leave this seat landed on that planet, or owning it, records `war_fail_day`. The existing 2-day cooldown then applies.
5. Engine rules stay as they are. The legacy pin stays `9b607d3dae940c0b1a69f6d7`.

## Bars

Every N2 and N3 seat stays at or above 75% of its war-off day-30 net worth on seeds 250925 and 4242. Each 30-day war-on match still has at least one planet attack. Rejected 0/0. Save identical.
