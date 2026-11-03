# Seat brain ops

After any commit that changes the seat brain (`src/tw2k/agents/seat_brain.py` or `scripts/seat_brain_v2.py`):

1. Restart **the brain process only**. Leave the match, the harness, and the other seats running.
2. Confirm the new process prints a startup line containing the new commit:

   `seat_brain_v2 <SEAT> SHA=<commit> module_mtime=<utc> module=tw2k.agents.seat_brain`

3. The same SHA and module mtime are copied onto every `turns.jsonl` row (`--log-dir`). `live_summary.json` (in that log directory, or `<mailbox>/<SEAT>.live_summary.json` when `--log-dir` is omitted) is rewritten on every decision with day, sector, credits, net worth, goals, planets, last action, and stall/replan counts.

Do not restart the universe to pick up a brain change.
