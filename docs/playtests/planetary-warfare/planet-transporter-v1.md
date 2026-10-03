# Planet Transporter

The player buys the transporter once for 50,000 credits. A hop moves the player. The planet stays. The first hop costs 50,000 credits and each extra hop costs 25,000. The planet pays 10 fuel per sector. A failed hop spends nothing.

| Case | Credits before | Fuel before | Ok | Credits after | Fuel after | Sector |
|---|---:|---:|---|---:|---:|---:|
| buy | 60000 | 0 | yes | 10000 | 0 | 40 |
| 1 hop | 80000 | 100 | yes | 30000 | 90 | 41 |
| 2 hops | 80000 | 100 | yes | 5000 | 80 | 42 |
| short credits | 40000 | 100 | no | 40000 | 100 | 40 |
| short fuel | 80000 | 9 | no | 80000 | 9 | 40 |
