# assign-colonists-pool-fix-v1

With citadel fidelity on, `assign_colonists` to `colonists` lands in the fuel-ore pool. Fuel, organics, and equipment already land in the pool you name.

`ASSIGN_POOL_FIX_MODE` defaults to `legacy`, so that redirect stays and the pin and the scripted games stay put.

`live` keeps `to=colonists` in the colonists pool. The named goods pools do not change.

Do not turn the switch on until Ben says so.

Tier S on dc6491e: the three tests pass, planted bugs failed the live and legacy tests and were restored, the bank pin stayed 9b607d3dae940c0b1a69f6d7, and the 10-day games stayed 24863a3d and 98a47c8a with rejected 0/0. The full suite and the 30-day games wait for the end of Batch A.
