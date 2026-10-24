# hardware-price-v1

A live TWGS v3.34b shop card priced an armid mine at 1,000 credits and said it does up to 30 points of damage. A limpet was 10,000. A genesis torpedo was 20,000. An ether probe was 3,000. This copy charges 100, 250, 25,000, and 5,000. An armid hit is 20 while the hardware switch is on, and 100 on the older path.

`HARDWARE_PRICE_MODE` defaults to `legacy`. Those prices and that hit stay, so the pin and the scripted digests stay put.

`live` charges the four card prices. One armid hit deals 30. The shop said "up to 30" and the combat was not played, so 30 is that ceiling, not a measured roll. How many mines blow up on a move stays as it is. The atomic mine stays at 4,000. The live atomic detonator is a planet killer, and this copy's atomic mine is a different item.

Ven 2026-10-24 GameA TWSTATS puts ship TransWarp on this same card (`hardware_price_live`): Type I 50,000, Type II 80,000, upgrade 10,000 (`docs/playtests/twgs-live/twstats-costs-ven.txt`). Stored cabal samples stay 12,500, 20,000, and 9,000. SOURCE-CONFLICT. `SHIP_TW_MODE` is not this switch. Citadel Transport Unit 50,000 and Upgrade 25,000 already match the planet transporter constants. No shop switch for those.

Do not turn the switch on until Ben says so.

Suite on 79d98ff: 2495 passed, 3 failed, 1 skipped, 3071s. Two failures are the known flakes (WinError 10048 and the spectator-feed timeout). The third, tests/test_v5p_skip_pod.py::test_death_card_dismiss_keeps_the_pod, is a video click that saw no clip playing. That screen was not changed. It passed alone in 8s. Two new tests passed. pb1 and pb2 were re-broken and restored.

10-day seed 250925 digest 24863a3d and seed 4242 digest 98a47c8a, both rejected 0/0, both the same as the runs on 99391c8. 30-day seed 250925 digest 86a15277. N3 3,390,327, N2 1,106,844, and H 529,130 rejected 0/0. N1 1,441,461 had one engine reject (0/1). Exceptions 0. 30-day seed 4242 digest b274e3d1. N3 2,071,033, N2 768,667, N1 632,729, H 74,827, all rejected 0/0, exceptions 0. The flag stayed legacy.
