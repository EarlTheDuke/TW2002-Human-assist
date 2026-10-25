# port-attack-defense-v1

`PORT_ATTACK_MODE` stays `legacy`. Live, an attack with target `port` asks first. The confirmation text is the one from the class 6 attack in REPORT2 section 8. Saying yes costs 5 alignment and the fighters you send.

Class 6 was the only measured port when this slice landed: defensive rating 98, laser barrage 598. That barrage is more than a Merchant Cruiser's 400 shields, so the cruiser is destroyed after the fighters are spent. A class 6 port is not removed. The handbook line that destroying a port costs 50 alignment and pays 50 experience was not seen in that attack (the ship died first), so this slice does not destroy the port.

Ven GameA (`docs/playtests/twgs-live/gap215-port-attack-2026-10-25.md`) measured the class fallbacks. When `PORT_ATTACK_MODE` is live, a port that is not one of the named samples uses that class's confirmed pair: class 1 def 46 / laser 337, class 2 def 55 / laser 482, class 3 def 86 / laser 873, class 4 def 110 / laser 1419, class 5 def 59 / laser 391, class 6 def 98 / laser 598, class 7 def 98 / laser 1121. Classes 2, 3, and 5 were measured 2026-10-25. A port whose name is in `PORT_ATTACK_GAMEA_SAMPLES` uses that port's own def and only a laser that shot actually measured. Live TWGS varies per port. Generation does not copy the class fallback onto the port. Engine class 8 stays StarDock, so the Vergil Minor def 99 / laser 954 sample is stored and not applied there. A class with no sample still costs the 5 alignment and the fighters, and the ship stays.

QC: five tests. pb1 dropped the alignment hit (alignment stayed 0). pb2 dropped the barrage kill (deaths stayed 0). Both restored. Bank pin 9b607d3dae940c0b1a69f6d7. 10-day digests 24863a3d and 98a47c8a, rejected 0/0.
