# Atmospheric quasar

Each row is one hostile landing. pct is 10, citadel level 3, fuel 10,000. Burned fuel is fuel * pct // 100. Damage is that fuel times 2. The first shot is before the shield gate. The second shot waits until planet shields are already down or fall in that gate.

10,000 fuel at 10% burns 1,000 and deals 2,000. The next shot on the remaining 9,000 burns 900 and deals 1,800.

| Case | Planet shields | Ship fighters | Ship shields | Shots | Damage | Fuel after | Died |
|---|---:|---:|---:|---:|---|---:|---|
| both shots, shields already down | 0 | 10000 | 0 | 2 | 2000, 1800 | 8100 | no |
| shields hold, one shot | 500 | 10 | 8000 | 1 | 2000 | 9000 | no |
| first shot kills | 0 | 100 | 0 | 1 | 2000 | 9000 | yes |
