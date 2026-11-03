# Project North Star v1 (Ben, 2026-10-16)

Posted by Grok Bot Commander, 2026-10-16 2:55 PM PT, from Ben's calls today. Board entry: COMMANDER NOTE 46 in docs/COMMANDER_NEXT.md. Direction only, not a build slice.

## 1. The three-layer next phase
a. Keep testing the cockpit methodically, like last night's hourly loop, and keep improving it.
b. Build an AI player that plays strictly from what the cockpit shows. No direct access to game state.
c. Put a voice front end on that AI player so a human can steer it out loud.

## 2. The core question
Is the data on the cockpit enough for an AI to make every decision a human player would make?
If any human decision needs data that is not on screen, the AI is playing blind. Every gap found is a cockpit bug.

## 3. Method
- Compare screen by screen against how original TW2002 (v3.x, TWGS, v3.11 rules) presented information, to find holes in what we render.
- Use click-heavy human play as stress tests. Example: haul about 1000 colonists to a target planet, chaining sector navigation, cargo management, several trips, and planet-to-planet transfers, all through cockpit clicks only.
- Adding more data than the original showed is fine where useful.

## 4. Side-loaded game documentation
Make game documentation available at the cockpit level for both the AI and the human player: all the rules, how points and net worth are scored, and how the game works.

## 5. Keep Cursor moving
Keep Cursor moving efficiently over the next 24 to 48 hours. The hourly Commander loop ACKs each delivery, retests it in play, and queues the next fixes so the board always has a released NOTE waiting.

## 6. Map
The richer map feature is valued and should stay on track. The separate 3D map prototype stays out for now.

## 7. Active task and next slices
- Active now: COMMANDER NOTE 45 cockpit-info-audit-v1 (the dashboard information audit) feeds this North Star.
- Likely next: the AI dashboard-only player (reads only the cockpit, acts only through cockpit controls).
- Then: the voice front end on that AI player.

## Standing rules
- Fidelity to the original game first.
- Cockpit changes behind COCKPIT_LAYOUT=redesign, with /bot unchanged.
- Engine changes behind flags that default to legacy.
- Batch O stays on hold.
