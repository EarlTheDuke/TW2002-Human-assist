# batch-m-gate-v1

Batch M is the map-shape slice. `UNIVERSE_TOPOLOGY_MODE` stays `legacy`. The live profile stays off. The profile's helper list now includes `universe_topology_live`, so turning the profile on would allow dead ends. It is not turned on.

The full suite on this branch: 2 failed, 2668 passed, 1 skipped, 3402s. Both failures are the known ones (the reserved port was already taken, and the feed count timed out). Thirty-day digests 86a15277 (seed 250925) and b274e3d1 (seed 4242), the same pair as the Batch L gate. On seed 250925, N1 shows rejected 0/1, the same as earlier gates. Seed 4242 is rejected 0/0. Ten-day digests from the topology slice stay 24863a3d and 98a47c8a. Bank pin 9b607d3dae940c0b1a69f6d7.

pb1 and pb2 were broken again on this branch and the topology test failed both times, then the breaks were put back. The 3D map stays out.
