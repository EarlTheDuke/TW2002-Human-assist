# batch-k-gate-v1

Full suite on this branch: 2 failed, 2656 passed, 1 skipped, 3351s. Both failures are the known flakes. The reserved-port check cannot bind 8040-8044 while those ports are already taken, and the spectator feed still times out waiting for a warp row.

Thirty-day digests match the Batch I gate: seed 250925 is 86a15277, seed 4242 is b274e3d1. Ten-day digests stayed 24863a3d and 98a47c8a, rejected 0/0. The bank pin stayed 9b607d3dae940c0b1a69f6d7.

`PLANET_REALTIME_PROD_MODE` stays legacy. The live profile stays off. The 3D map stays out.
