# StarDock leftovers

Tri-Cron and the Cineplex, plus the LLM quasar reminder. Legacy play is `STARDOCK_EXTRA_MODE=legacy`.

## What the sources say

The slice blurb called Tri-Cron a galactic news board and the Cineplex a rumor venue. The live TWGS screen, TWINSTR, and the original Bible say otherwise.

Tri-Cron is a Lost Trader's Tavern game. Play is `TRICRON_MODE`, stored default legacy. `STARDOCK_EXTRA_MODE` no longer deals the match. The confirmed screen is `docs/playtests/twgs-live/tricron.txt`: 10 rounds, three crons each (0-9), positions 1 (hundreds), 2 (tens), or 3 (ones), the greater ten-round total wins, payback 2 to 1, the ante is 100 credits and goes into the jackpot, the jackpot stands at 5,000, and the champion score was 5,000. One match paid "You win 100 credits!" The Bible names 2-3-1 as the best placement, and that is the order when the action omits one. The capture shows no turn charge. This build uses the tavern turn cost, which is 0.

The Cineplex is a StarDock menu theatre. TWINSTR describes a picture and popcorn. The Bible says the show is a useless ANSI for a nominal credit amount and holds no secrets. The live player did not enter it (`REPORT.md`: exist, not read). No price number is in those sources, so `CINEPLEX_COST` is 0 and stays the stored default. NOTE 129 (`docs/playtests/twgs-live/illegal-goods.txt`) later asked 100 credits for show 1, Vulcan Thunder. The theatre is on the where-to list in `stardock-menus.txt`. Titles that were not opened are not sold here. The picture text has no secrets. The 100-credit ticket is the live card with the other 19 Oct StarDock prices, not a change to this stored 0.

## Prices re-checked from slice 62

The live tavern screen and the clone constants disagree. The clone numbers were left in place.

| Item | Live screen | Clone constant |
|---|---|---|
| Announcement | 100 credits | `TAVERN_ANNOUNCE_COST` 100 |
| Drink | 0 | `TAVERN_DRINK_COST` 20 |
| Food | 0 | `TAVERN_FOOD_COST` 20 |
| Grimy STARDOCK info | 50 | `GRIMY_TRACE_COST` 3000 |
| Grimy UNDERGROUND info | 600 | charged as `GRIMY_PASSWORD_COST` 2000 |
| Grimy password | 0 | `GRIMY_PASSWORD_COST` 2000 |
| Underground name change | 247, no experience on that screen | UNVERIFIED/DIFFERENT. The measured total unknown is 100 (`name-change.txt`), behind `UG_NAME_MODE`. `UG_NAME_CHANGE` stays false |

The 19 Oct day-1 screen is a later visit (`docs/playtests/twgs-live/stardock-menus.txt`). It quotes a StarDock tip at 23 credits and a paid password at 160. Those two sit behind `GRIMY_TIP_MODE`. This table stays the earlier screen. The underground ladder of 2,500 then 600, and a password topic at 1,500, are not in that switch.

## Quasar reminder

`LLM_QUASAR_NUDGE_MODE` off leaves the LLM turn text unchanged. On, one line is added only for an LLM seat landed on its own or corporate planet when the citadel is at least `QUASAR_MIN_LEVEL` (3), fuel ore is at least 500, and either cannon percent is still 0. `BOT_WAR_QUASAR_ORE_FLOOR` stays 2000.

## Matches

10-day seed 250925, seats N3,N3,N2,N2,N1,H. Digest `f1b4188d`, the same digest as the deploy slice. Rejected 0/0, exceptions 0. No seat played Tri-Cron or the Cineplex. Tavern talk stayed at one line each for P1, P2, P3, P4, and H.

| Seat | Net worth | Credits | Planets | Deaths |
|---|---:|---:|---:|---:|
| N3-P1 | 429,645 | 99,862 | 2 | 0 |
| N2-P3 | 310,952 | 58,593 | 2 | 0 |
| N3-P2 | 167,678 | 13,115 | 1 | 0 |
| N2-P4 | 91,736 | 5,783 | 1 | 4 |
| N1-P5 | 45,199 | 0 | 1 | 6 |
| H-P6 | 10,452 | 0 | 0 | 5 |

Seed 4242, same seats, digest `764b3596`, the same digest as the deploy slice. Rejected 0/0, exceptions 0. No seat played Tri-Cron or the Cineplex.

| Seat | Net worth | Credits | Planets | Deaths |
|---|---:|---:|---:|---:|
| N3-P1 | 655,993 | 81,748 | 3 | 0 |
| H-P6 | 527,643 | 22,069 | 0 | 2 |
| N1-P5 | 437,390 | 68,750 | 1 | 0 |
| N2-P3 | 156,801 | 0 | 1 | 5 |
| N2-P4 | 119,734 | 0 | 1 | 4 |
| N3-P2 | 93,247 | 8,224 | 1 | 2 |

Fourteen plants (sd1, sd3, sd4, sd5, sd7, sd8, cx1, cx2, cx3, qn1, qn3, qn4, qn5, qn6) were re-broken one at a time and each named test failed. The files were restored.

30-day seed 250925, same seats, digest `c434db80`. Rejected 0/0, exceptions 0. No seat played Tri-Cron or the Cineplex. Day 10 of this run matches the 10-day table above.

| Seat | Net worth | Credits | Planets | Deaths |
|---|---:|---:|---:|---:|
| N3-P1 | 2,050,233 | 717,685 | 4 | 0 |
| N2-P3 | 945,984 | 0 | 4 | 13 |
| H-P6 | 648,439 | 55,644 | 0 | 8 |
| N3-P2 | 311,341 | 65,219 | 1 | 0 |
| N2-P4 | 245,424 | 8,603 | 1 | 9 |
| N1-P5 | 136,776 | 0 | 2 | 19 |

The day-15 save check on seed 250925 is identical. Digest `61bcb8cc`, the same digest as the deploy slice. Rejected 0/0. Corporate deploys P1 13, P2 3, P3 66, P4 1. Day 15 net worth matches the 30-day run: P1 962,682, P3 768,621, P2 187,508, P4 124,503, P5 53,149, H 45,042.

Suite on 547da63: 2450 passed, 2 failed, 1 skipped, 22 warnings, 3078s. Both failures are the known flakes: WinError 10048 on the reserved live port, and the spectator-feed timeout.
