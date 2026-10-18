# v311-daylen-and-yard-v1 (NOTE 60) screens

Made by `tests/test_v311_daylen_and_yard_browser_v1.py` on the redesign cockpit (`/bot?layout=redesign`), at 1920 x 1080 and 390 x 844.

The v3.11 page runs `V311_PROFILE=v311` with a 600 s day (`turn_regen_day_seconds=600`) and 60 turns, so a turn comes back every 10 s. The test rolls each day by moving the server's day mark back one day length, so the loop rolls on its own clock.

| Screen | What it shows |
| --- | --- |
| `*-yard-list-v311.png` | Every hull with its price; the hulls the seat cannot buy are grey with the reason (credits, corporation, alignment) |
| `*-scout-v311.png` | Scout Marauder from the server's `stats_by`: holds 10 of 25, fighters 250 (RULINGS s4) |
| `*-no-turns-v311.png` | "No turns left. Next turn in about N s (time). Day 2 starts at time." from the observation's `turn_clock` |
| `*-day-roll-v311.png` | "Day 2. Turns come back about 360 an hour; you have N of 60." |
| `*-citadel-quote-v311.png` | Citadel L1 on a class M planet on day 2: "4 days. Ready day 6." |
| `*-citadel-l1-v311.png` | Day 6: the card shows Citadel level 1 and the L1 perk (Treasury) |
| `*-yard-list-legacy.png` | The legacy roster list (profile off) |
| `*-scout-legacy.png` | Scout Marauder under the legacy roster: holds 25, fighters 150 |
| `*-no-turns-legacy.png` | The legacy line: "No turns left today. Day N starts when the other traders finish." |

With the profile off and `YARD_STATS_MODE` legacy the server sends no `stats_by`, and the cockpit's `HULL` table is the fallback (the same legacy numbers). `scout-legacy` is taken with only `YARD_STATS_MODE=live`, so its figures come from the server.
