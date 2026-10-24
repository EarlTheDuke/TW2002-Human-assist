# port-attack-defense-v1

`PORT_ATTACK_MODE` stays `legacy`. Live, an attack with target `port` asks first. The confirmation text is the one from the class 6 attack in REPORT2 section 8. Saying yes costs 5 alignment and the fighters you send.

Class 6 was the only measured port when this slice landed: defensive rating 98, laser barrage 598. That barrage is more than a Merchant Cruiser's 400 shields, so the cruiser is destroyed after the fighters are spent. A class 6 port is not removed. The handbook line that destroying a port costs 50 alignment and pays 50 experience was not seen in that attack (the ship died first), so this slice does not destroy the port.

Other port classes had no measured rating or barrage when this slice landed. A live attack there still costs the 5 alignment and the fighters, and the ship stays. No number was invented for them.

Ven GameA on 2026-10-24 (`docs/playtests/twgs-live/gap215-port-attack-2026-10-24.md`) recorded more classes. CONFIRMED lasers from that capture: class 1 337, class 4 1419, class 6 598, class 7 1121. This slice still wires only class 6. Those later samples are not in `PORT_DEFENSE_RATING` or `PORT_LASER_BARRAGE`.

QC: five tests. pb1 dropped the alignment hit (alignment stayed 0). pb2 dropped the barrage kill (deaths stayed 0). Both restored. Bank pin 9b607d3dae940c0b1a69f6d7. 10-day digests 24863a3d and 98a47c8a, rejected 0/0.
