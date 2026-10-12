# gap-map-refresh-v2

Plan only. Compared the October 10 gap map (tip `62961c5`) with origin tip `afdf796` and with `C:\Users\sugar\tw2002_reference\live_twgs\REPORT.md`, `REPORT2.md`, `game5_p7_findings.md`, and `cockpit_play_log.md`. No default was changed. The 3D map stays out.

## What the old ranked list became

Section 18 of `docs/plans/GAP_MAP.md` named 14 slices. Each one now has a mode flag. The default of every one of those flags is still the old behavior, so the bank pin stays `9b607d3dae940c0b1a69f6d7`.

| Old slice | Flag now | Default |
|---|---|---|
| port-open-full-v1 | `PORT_OPEN_STOCK_MODE`, `PORT_REGEN_MODE` | legacy |
| genesis-score-v1 | `GENESIS_SCORE_MODE` | legacy |
| action-result-v1 | `ACTION_RESULT_MODE` | legacy |
| starting-package-v1 | `STARTING_PACKAGE_MODE`, `TURN_REGEN_MODE`, `LIVE_PACE_MODE` | legacy |
| port-class-map-v1 | `PORT_CLASS_MAP_MODE` | legacy |
| trade-in-90-v1 | `TRADE_IN_MODE` | legacy |
| haggle-window-v1 | `HAGGLE_WINDOW_MODE`, `HAGGLE_LIVE_MODE` | legacy |
| hardware-price-v1 | `HARDWARE_PRICE_MODE`, `DETECT_GEAR_MODE` | legacy |
| citadel-days-v1 | `CITADEL_DAYS_MODE` | legacy |
| planet-shields-v1 | `PLANET_SHIELD_ACTIVE_MODE` | legacy |
| cash-tax-v1 | already the 5% over 100,000 rule | no new flag |
| fedspace-deploy-v1 | `FEDSPACE_DEPLOY_MODE` | legacy |
| own-planet-turn-v1 | `OWN_PLANET_TURN_MODE`, `OWN_PLANET_FIGHTER_MODE` | legacy |
| stardock-sector-v1 | not built | StarDock stays sector 1 on purpose |

Game 5's high rows land on those same flags: empty ports, the 308,000 genesis score, `accepted: true` before the engine answers, the thin starting pocket, class numbers, trade-in, the 3,000 colonist cap, and a foreign fighter blocking your own planet. The cockpit play log's plot, landing, Terra form, dividend, header, citadel line, turn rise, and cut-order notes are in Batch H through J.

## Still open

Class M citadel colonists are still a conflict. The handbook table says 1,000. The live v3.34b screen said 1,000,000. This copy still uses 1,000. Do not guess.

Class M population is the same kind of conflict. The handbook cap used here is 30,000, so the live production rule (off unless that flag or the live profile is on) treats 191,000 colonists as over half and removes about 5% a day. The live game kept about 196,000 overnight and did not show that loss. The planet panel already names the die-off when the rule is on. The cap number stays 30,000 until Ben chooses.

Planet goods on the live server moved during the day (fuel, organics, and equipment were higher after 7.3 hours). This copy makes them only when the day ticks. That is the first Batch K slice.

Random StarDock stays a written difference, not a slice. The 3D map stays out.

## Batch K

1. `planet-realtime-prod-v1`. New flag, default legacy. While it is on, a planet's daily product also accrues as time passes, at the same daily rate times the fraction of 24 hours elapsed. The day tick must not pay that fraction twice. Legacy stays midnight-only, and the pin stays put.
2. `batch-k-gate-v1`. Full suite and the two 30-day digests after K1.
