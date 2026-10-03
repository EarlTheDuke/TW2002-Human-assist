# Corp planet edge cases

A member who leaves keeps the planets they own. Those planets lose the corp ticker, so the old mates cannot manage them. The leaver does not take a corp-mate's planet, and they cannot move it or deposit in its treasury. The corp stays. The mates' own planets keep the ticker.

The last member leaving removes the corp. A planet whose owner is still alive keeps that owner and loses the ticker. A planet whose owner is dead, missing, or already empty becomes unowned, loses the ticker, and gets the existing orphan event.

Landing on an allied planet is still a siege. The siege grid does not call corp_leave, so those cells did not change.

| Case | Owner | Ticker | Ok | Turns | Orphans |
|---|---|---|---|---:|---:|
| leave planet_transwarp | D | ZZ | no | 0 | 0 |
| leave planet_transport | D | ZZ | no | 0 | 0 |
| leave deposit_treasury | D | ZZ | no | 0 | 0 |
| leave own ticker | A | none | no | 0 | 0 |
| disband live | A | none |  |  | 0 |
| disband dead | none | none |  |  | 1 |
| ally land | D | none | no | 3 | 0 |
