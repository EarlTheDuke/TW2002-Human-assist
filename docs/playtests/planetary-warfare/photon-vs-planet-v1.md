# Photon damp

Each row is one hostile warp after a photon in the planet sector, except the first row which has no photon. Fuel is 10,000 at 10 percent. Damage is burned fuel // 3 when the sector cannon fires. A citadel L5 with 200 shields ignores the photon. Below L5 or below 200 shields skips that cannon for the one approach.

| Case | Level | Planet shields | Photon | Damped | Sector damage | Fuel after |
|---|---:|---:|---|---|---:|---:|
| no photon | 3 | 0 | no | no | 333 | 9000 |
| photon, citadel 3 | 3 | 0 | yes | yes | 0 | 10000 |
| L5 with 200 shields | 5 | 200 | yes | no | 333 | 9000 |
| L5 with 199 shields | 5 | 199 | yes | yes | 0 | 10000 |
| L4 with 200 shields | 4 | 200 | yes | yes | 0 | 10000 |
