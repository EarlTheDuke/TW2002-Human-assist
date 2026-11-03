# dashboard-wait-status-v1

A match that was stuck on one seat still said "live" in green.

While the scheduler is waiting on a seat, the header says `Waiting for <name> (day-done n/seats)` and the dot is not the green live dot. The line appears after 15 seconds, so a fast turn still says live. The tab says waiting. A model that is thinking still uses the thinking line.
