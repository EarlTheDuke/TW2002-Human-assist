# Interdictor

Each row is one attempted warp out of a planet sector. Citadel level 6 with at least 500 fuel holds the ship, burns 500 fuel, then the sector cannon uses the fuel that remains. Below 500 fuel, or below level 6, the warp leaves.

500 fuel burns the whole stock, so the cannon has nothing left to fire. 10,000 fuel burns 500, then 10 percent of the remaining 9,500 deals 316.

| Case | Level | Fuel before | Held | Sector after | Damage | Fuel after |
|---|---:|---:|---|---:|---:|---:|
| 500 fuel | 6 | 500 | yes | 40 | 0 | 0 |
| 10000 fuel | 6 | 10000 | yes | 40 | 316 | 8550 |
| 499 fuel | 6 | 499 | no | 1 | 0 | 499 |
| level 5 | 5 | 10000 | no | 1 | 0 | 10000 |
