# Sector quasar

Each row is one hostile warp. pct is 0-100. Burned fuel is fuel * pct // 100. Damage is that fuel // 3. Shields soak first, then fighters.

10,000 fuel at 10% burns 1,000 and deals 333. The next shot on the remaining 9,000 burns 900 and deals 300. A level 2 citadel, a 0 percent setting, and an empty fuel stockpile do not fire.

| Case | Level | Pct | Fuel before | Shields | Fighters before | Damage | Fuel after | Fighters after | Shields after |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10% of 10000 | 3 | 10 | 10000 | 0 | 1000 | 333 | 9000 | 667 | 0 |
| second shot | 3 | 10 | 9000 | 0 | 667 | 300 | 8100 | 367 | 0 |
| level 2 | 2 | 10 | 10000 | 0 | 1000 | 0 | 10000 | 1000 | 0 |
| pct 0 | 3 | 0 | 10000 | 0 | 1000 | 0 | 10000 | 1000 | 0 |
| no fuel | 3 | 10 | 0 | 0 | 1000 | 0 | 0 | 1000 | 0 |
| shields first | 3 | 10 | 10000 | 100 | 500 | 333 | 9000 | 267 | 0 |
