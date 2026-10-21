# V311 source conflicts

Ben can rule on these. Each row is one that NOTE 158 hit where two sources print different numbers, or where a printed figure was not adopted. A switch that is off leaves the stored game alone.

## NOTE 158 — scoring and the end of the game

| Row | Competing numbers | Sources | Current choice |
|---|---|---|---|
| Re-entry fighters | 250, or the Initial Fighters setting, or up to 2,500 | The v3.11 revision history: a Scout re-entry gets the minimum of 250 fighters and the Initial Fighters value, instead of up to 2,500. Cabal `twgs.html` leaves Initial fighters blank. RULINGS s2 prints 30. The stored start is 20. | `REENTRY_FIGHTERS_MODE` uses this game's initial fighters, capped at 250, and also capped by the scout's room. Off, the scout has 0. The 2,500 grant is not the on value. |
| Experience and alignment ceiling | 4,500,000, or 999,999,999 | The v3.11 revision says a gain past the limit stops at the boundary. The same history handles a name change from 0 to 4,500,000 experience, and caps a charge at 999,999,999. The editor range in `SysOpUpdated.html` is also 0 to 999,999,999. The sentence does not say which boundary is the stat cap. | No clamp. NOTE 158 did not pick one of those two ceilings. |
| Match length | No printed length, or this beta's 30 days and 100,000,000 credits | The Bible and EIS say there is no built-in win and the sysop sets the duration. Cabal `twgs.html` "Days to allow entry: Unlimited" is how long a new trader may join, not how long the match lasts. | The day cap, the last player standing, the credit bar, and a creator end stay. `EXP_SCORE_MODE` already ranks a day-cap finish by experience when it is on. NOTE 158 did not add an end switch. |
| Times blown up | Unlimited, or a later lockout | Cabal `twgs.html` prints Tournament Mode Off and Maximum times blown up Unlimited. `TWGS_v2_Revision_History.html` later adds pod and death lockouts. | `DEATH_DELAY_MODE` remains the timeout. The later lockout was not switched. Two pods a day and out-until-midnight stay the stored death path. |
| High score | TriCron HiScore 0, or the trader list | Cabal `twgs.html` prints TriCron HiScore 0 for that game. EIS `CompDisplays.html` lists traders in order of experience, with a title or the experience value, the corporation, and the ship. | `TRADER_RANK_LIST_MODE` is the list. NOTE 158 did not add a TriCron score. |
