# live-profile-pace-fix-v1

LIVE_PACE_MODE stays legacy. The live profile turns it on.

A live opening still starts at 250 turns when the caller left the engine default of 1,000. Any other count, including `--turns-per-day 50`, is the count the seat gets.

Spent seats get their hourly turns back before the day is allowed to roll. A day that just rolled waits out that hour. It does not roll again on the next pass, and the day tick still does not refill a live seat to full.

`SEAT_DEADLINE_MODE=off` and `ASYNC_DAY_MODE=off` stay off even when the live profile is on. `TW2K_SEAT_DEADLINE_MODE` and `TW2K_ASYNC_DAY_MODE` (`legacy`, `live`, or `off`) override the stored switch.

Cockpit profile, for a person at the keyboard: live profile on, both of those switches off, `--external-idle-wait-s 0` so an empty seat is not skipped after 8 seconds, `--external-timeout-s` set to that seat's own wait (a played seat can use a very large number), and `--pause-on-seat-drop` only if the match should pause when the browser stops polling.
