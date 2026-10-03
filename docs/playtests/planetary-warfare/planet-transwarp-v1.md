# Planet TransWarp

Each row is one attempt to move a planet two warp sectors. Fuel cost is 400 per sector, so two hops cost 800. The destination needs a fighter of the owner. A short stock, a missing fighter, or a citadel below level 4 leaves the planet where it is.

| Case | Level | Fuel before | Fighter | Moved | Sector after | Fuel after |
|---|---:|---:|---|---|---:|---:|
| 2 hops, 1000 fuel | 4 | 1000 | yes | yes | 42 | 200 |
| 2 hops, 799 fuel | 4 | 799 | yes | no | 40 | 799 |
| no fighter at dest | 4 | 1000 | no | no | 40 | 1000 |
| level 3 | 3 | 1000 | yes | no | 40 | 1000 |
