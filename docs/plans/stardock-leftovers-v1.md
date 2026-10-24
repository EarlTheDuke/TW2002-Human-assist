# stardock-leftovers-v1 source check

The slice blurb called Tri-Cron a news board and the Cineplex a rumor venue. The live TWGS screen, TWINSTR, and the original Bible describe a tavern game and a picture theatre. Those are the effects that shipped. The playtest note is `docs/playtests/fedspace/STARDOCK_EXTRA.md`.

Live prices from `live_twgs/REPORT.md` that disagree with the clone were left unchanged:

| Item | Live | Clone |
|---|---|---|
| Drink | 0 | `TAVERN_DRINK_COST` 20 |
| Food | 0 | `TAVERN_FOOD_COST` 20 |
| Grimy STARDOCK info | 50 | `GRIMY_TRACE_COST` 3000 |
| Grimy UNDERGROUND info | 600 | charged as `GRIMY_PASSWORD_COST` 2000 |
| Grimy password | 0 | `GRIMY_PASSWORD_COST` 2000 |

Announcement 100 matches. The screen behind this table had no Cineplex price, so `CINEPLEX_COST` stays 0. NOTE 129 later asked 100 credits for show 1, Vulcan Thunder (`docs/playtests/twgs-live/illegal-goods.txt`). The theatre is on the where-to list (`docs/playtests/twgs-live/stardock-menus.txt`). That ticket is the live card with the other 19 Oct StarDock prices. This stored 0 does not move, and the other titles on that board were not opened. Underground name change for a total unknown is 100 credits behind `UG_NAME_MODE` (`name-change.txt`). `UG_NAME_CHANGE` stays false. The earlier 247 figure has no experience and stays UNVERIFIED/DIFFERENT; it is not `UG_NAME_UNKNOWN_COST`.
