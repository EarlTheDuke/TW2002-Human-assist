# planet-shields-v1

The manual says 10 ship shields make 1 planet shield, and an attacker needs about 20 fighters to break one. Those two rules are already in this copy. Shields can be loaded before citadel level 5. They only stop a landing once level 5 is finished. This copy lets any stocked shields fight, at any level.

`PLANET_SHIELD_ACTIVE_MODE` defaults to `legacy`. Stocked shields still fight, so the pin and the scripted digests stay put.

`live` ignores shields in a landing until the citadel is level 5. The stock stays on the planet. The free gift stays 0. No new shield count is invented. The level 5 perk line still says planetary shields are not in this game while the switch is off.

Do not turn the switch on until Ben says so.

Suite on 962bd7f: 2500 passed, 2 failed, 1 skipped, 3088s. Both failures are the known flakes (WinError 10048 and the spectator-feed timeout). Two new tests passed. pb1 and pb2 were re-broken and restored.

10-day seed 250925 digest 24863a3d and seed 4242 digest 98a47c8a, both rejected 0/0, both the same as the runs on 52874a6. 30-day seed 250925 digest 86a15277. N3 3,390,327, N2 1,106,844, and H 529,130 rejected 0/0. N1 1,441,461 had one engine reject (0/1). Exceptions 0. 30-day seed 4242 digest b274e3d1. N3 2,071,033, N2 768,667, N1 632,729, H 74,827, all rejected 0/0, exceptions 0. The flag stayed legacy.
