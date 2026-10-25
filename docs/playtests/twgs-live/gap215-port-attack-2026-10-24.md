# GAP 2.15 ? Port attack defensive rating / laser (TWGS Slot A)

Lasers for classes 2, 3, 5, and non-Fed 8 were measured on 2026-10-25. That pass is `gap215-port-attack-2026-10-25.md`. The JSON `gap215_final.json` is the 2026-10-25 file. This note is the 2026-10-24 capture. Those four rows were DEF_ONLY that day.

Engine: TW2002 v3.34b under TWGS v2.20b. Game: TW Test Game 2 (Slot A).
Captured: 2026-10-24 America/Los_Angeles.

## Primary table

| Class | Port name | Sector | Def rating | Laser/battle pts | Shield text | Status | Notes |
|------:|-----------|-------:|-----------:|-----------------:|-------------|--------|-------|
| 0 | Sol | 1 | ? | ? | ? | BLOCKED | FedSpace / Terra ? attack prohibited / unsafe |
| 1 | H'Catha | 478 | 46 | 337 | No shielding evident, plasma lasers on dock. | CONFIRMED | GrokAFK24 pod death; align -5; also Leipzig@708 def=49 (variance) |
| 2 | New Cesium | 160 | 55 | ? | No shielding evident, plasma lasers on dock. | DEF_ONLY | 0-fighter abort; also Mastro@173 def=71 (variance) |
| 3 | Peleus | 436 | 86 | ? | Class 2 shielding evident, Halos missile battery. | DEF_ONLY | 0-fighter abort; also Anaxagoras Primus@913 def=60 plasma (variance) |
| 4 | Duriron Minor | 122 | 110 | 1419 | (no separate shielding line; captain warning: massive port) | CONFIRMED | GrokAFK24 Merchant death; align -5; exp -3 |
| 5 | Aesculapius | 404 | 59 | ? | No shielding evident, plasma lasers on dock. | DEF_ONLY | 0-fighter abort; also Mirador Outpost@121 def=44 (variance) |
| 6 | Khancuhn Primus | 534 | 98 | 598 | Class 4 shielding, Sunstorm Ion battery | KNOWN | REPORT2 prior GameA sample (sector may differ in this BigBang) |
| 7 | Balmer | 688 | 98 | 1121 | Class 4 shielding evident, Sunstorm Ion battery. | CONFIRMED | GrokGap217 1-fig attack; pod at 579 after; align -5 |
| 8 | Vergil Minor | 119 | 99 | ? | Class 4 shielding evident, Sunstorm Ion battery. | DEF_ONLY | NON-FED sample via 0-fighter abort. Fed prior REPORT.md: def 91 / laser 701 / class 3 shielding (Fed BBB). |
| 9 | Stargate Alpha I | 842 | ? | ? | ? | BLOCKED | StarDock / FedSpace ? skip attack |

## Verbatim snippets (CONFIRMED)

### Class 1 H'Catha @478
```
This port has a defensive rating of 46
No shielding evident, plasma lasers on dock.
...
Incoming laser barrage from H'Catha
The console reports damages of 337 battle points!
```

### Class 4 Duriron Minor @122
```
This port has a defensive rating of 110
Captain!@!@!  That's a massive port!  We don't stand a chance!
...
Incoming laser barrage from Duriron Minor
The console reports damages of 1419 battle points!
```

### Class 7 Balmer @688
```
This port has a defensive rating of 98
Class 4 shielding evident, Sunstorm Ion battery.
...
Incoming laser barrage from Balmer
The console reports damages of 1121 battle points!
```

## Key fidelity notes

- **0-fighter abort works**: after def/shield text, `How many fighters?` ? `0` returns to Command with no combat.
- **Def rating is per-port, not a class constant** (e.g. Class 3 Peleus 86 vs Anaxagoras 60).
- **Non-Fed Class 8 exists** (Vergil Minor @119 def 99 / Class 4 Sunstorm) ? differs from Fed Class 8 prior (91/701 / class 3).
- Class 0 Sol and Class 9 StarDock left BLOCKED (Fed/StarDock).

JSON: `gap215_final.json`
