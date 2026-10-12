# planet-realtime-prod-v1

A live TWGS day showed planet fuel, organics, and equipment higher after 7.3 hours. This copy made those goods only when the day ticked.

`PLANET_REALTIME_PROD_MODE` defaults to `legacy`. The day tick is unchanged, the new clock fields are left out of a save, and the pin stays put.

`live` spreads that same daily amount across 24 hours. A day tick pays the seconds the clock has not already paid, so the fraction is not paid twice. A pause longer than a day pays one day and then waits. The live profile turns this on with the other helpers. The profile stays off.

Do not turn the switch on until Ben says so.
