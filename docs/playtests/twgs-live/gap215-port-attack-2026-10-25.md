# GAP 2.15 - Port attack defensive rating / laser (TWGS Slot A)

Engine: TW2002 v3.34b under TWGS v2.20b. Game: TW Test Game 2 (Slot A).
Captured: 2026-10-25 America/Los_Angeles.
Earlier pass: `gap215-port-attack-2026-10-24.md` (classes 2, 3, 5, and non-Fed 8 were DEF_ONLY that day).
JSON: `gap215_final.json`.

Method: a 0-fighter commit aborts after the def and shield text with no ship loss. A 1-fighter commit yields the laser barrage battle points and usually destroys the Merchant or the pod. Slot A was the existing GameA (BigBang window opened, then Activate on GameA data). Lasers via `gap215_lasers.py`.

## Primary table

| Class | Port name | Sector | Def rating | Laser/battle pts | Shield text | Status | Notes |
|------:|-----------|-------:|-----------:|-----------------:|-------------|--------|-------|
| 0 | Sol | 1 | | | | BLOCKED | FedSpace / Terra. Attack prohibited / unsafe |
| 1 | H'Catha | 478 | 46 | 337 | No shielding evident, plasma lasers on dock. | CONFIRMED | Unchanged from 2026-10-24. Also Leipzig@708 def=49 (variance) |
| 2 | New Cesium | 160 | 55 | 482 | No shielding evident, plasma lasers on dock. | CONFIRMED | GrokGap218 1-fig attack; died. Also Mastro@173 def=71 (variance) |
| 3 | Peleus | 436 | 86 | 873 | Class 2 shielding evident, Halos missile battery. | CONFIRMED | GrokGap219 1-fig attack; died. Also Anaxagoras Primus@913 def=60 plasma (variance) |
| 4 | Duriron Minor | 122 | 110 | 1419 | (no separate shielding line; captain warning: massive port) | CONFIRMED | Unchanged from 2026-10-24 |
| 5 | Aesculapius | 404 | 59 | 391 | No shielding evident, plasma lasers on dock. | CONFIRMED | GrokGap220b 1-fig attack; died. Also Mirador Outpost@121 def=44 (variance) |
| 6 | Khancuhn Primus | 534 | 98 | 598 | Class 4 shielding, Sunstorm Ion battery | KNOWN | REPORT2 prior GameA sample (sector may differ in this BigBang) |
| 7 | Balmer | 688 | 98 | 1121 | Class 4 shielding evident, Sunstorm Ion battery. | CONFIRMED | Unchanged from 2026-10-24 |
| 8 | Vergil Minor | 119 | 99 | 954 | Class 4 shielding evident, Sunstorm Ion battery. | CONFIRMED | NON-FED GrokGap221 1-fig attack; died. Fed prior REPORT.md: def 91 / laser 701 / class 3 shielding (Fed BBB). That prior stays labeled FED_PRIOR and is not this shot |
| 9 | Stargate Alpha I | 842 | | | | BLOCKED | StarDock / FedSpace. Skip attack |

## Verbatim snippets (2026-10-25 lasers)

### Class 2 New Cesium @160
```
This port has a defensive rating of 55
No shielding evident, plasma lasers on dock.
...
Incoming laser barrage from New Cesium
The console reports damages of 482 battle points!
```

### Class 3 Peleus @436
```
This port has a defensive rating of 86
Class 2 shielding evident, Halos missile battery.
...
Incoming laser barrage from Peleus
The console reports damages of 873 battle points!
```

### Class 5 Aesculapius @404
```
This port has a defensive rating of 59
No shielding evident, plasma lasers on dock.
...
Incoming laser barrage from Aesculapius
The console reports damages of 391 battle points!
```

### Class 8 Vergil Minor @119 (non-Fed)
```
This port has a defensive rating of 99
Class 4 shielding evident, Sunstorm Ion battery.
...
Incoming laser barrage from Vergil Minor
The console reports damages of 954 battle points!
```

Fed prior class 8, from REPORT.md, is a different sample: def 91 / laser 701 / class 3 shielding. It is not this GameA shot.

## Key fidelity notes

- Def rating is per port, not a class constant (class 3 Peleus 86 vs Anaxagoras Primus 60).
- Classes 2, 3, and 5 are wired as class fallbacks (482, 873, 391). Engine class 8 is StarDock, so Vergil Minor 954 stays on the sample list and is not written into `PORT_DEFENSE_RATING` or `PORT_LASER_BARRAGE`.
- Variance rows Leipzig, Mastro, Anaxagoras Primus, and Mirador Outpost stay def-only. They do not borrow the class laser.
- Class 0 Sol and class 9 StarDock stay BLOCKED.
