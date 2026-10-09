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

Announcement 100 matches. `CINEPLEX_COST` is 0 because no price number was on the screen. Underground name change stays unbuilt (`UG_NAME_CHANGE` false); the live price was 247.
