# Cockpit AI seat v1

NOTE 54. North Star question: is the data on the cockpit enough for an AI to make every decision a human player would make? This slice answers that with the surfaces below, then a client that can only use them. The voice front end stays out. Batch O stays on hold. The 3D map stays out.

`AI_COCKPIT_SEAT_MODE` defaults to legacy. The server never starts this seat. A test turns the switch on and runs the client against that test server only.

## Observation surface

The seat may GET these four routes for its own seat, with its own bearer token:

- `GET /harness/v1/{seat}/observation` — the harness observation the redesign paints. Top-level fields the cockpit uses: `day`, `turns_remaining`, `credits`, `experience`, `alignment`, `rank`, `net_worth`, `ship`, `sector`, `adjacent`, `legal_actions`, `planet_landed`, `owned_planets`, `recent_events`, `known_ports`, `known_warps`, `known_sectors`, `fighter_challenge`, `ferrengi_encounter`, `bank_balance`, `corp`, `inbox`.
- Sector fields the cockpit uses: `id`, `warps_out`, `is_fedspace`, `port` (class, code, buys, sells, stock), `planets` (name and class), `occupants`, `fighter_group`, `mines`, `beacon`, `nav_hazard_pct` when the sector has it.
- `legal_actions` rows: `kind`, `legal`, `reason`, `turn_cost`, `params`. Warp targets and trade side, commodity, and quantity come from `params`.
- `GET /harness/v1/{seat}/reference` — the same Rules and Help page as Z. Sections: `rules`, `scoring`, `ranks`, `ships`, `prices`.
- `GET /harness/v1/{seat}/events` — the log rows the cockpit prints.
- `GET /harness/v1/{seat}/status` — whether it is this seat's turn.

The seat does not GET another seat, and it does not read the universe, the runner, or an observation built inside the process.

## Action surface

The seat POSTs `/harness/v1/{seat}/action` with `turn_seq` and one kind the redesign can send. The main keys are Move `warp`, Port `trade`, Land `land_planet`, Scan `scan`, Attack `attack`, Fighters `deploy_fighters`, Mines `deploy_mines`, Genesis `deploy_genesis`, Probe `probe`, Wait `wait`. Planet keys are Take `load_planet_cargo`, Leave `dump_planet_cargo`, Colonists `assign_colonists`, Stock fighters `deposit_planet_defense`, Take fighters `withdraw_planet_defense`, Build citadel `build_citadel`, and Lift off `liftoff`. Computer keys that post are Course `plot_course`, Photon `photon_missile`, Announce `broadcast`, Avoid `avoid`. Ship and port forms that post include `buy_ship`, `buy_equip`, `hail`, `radio`, `surrender`, `retreat`, `rob`, `steal`, `port_upgrade`, `port_build`, and the bank verbs. A kind outside that list is refused before it is posted.

## Gaps for a full game

`docs/plans/cockpit-info-audit-v1.md` is the gap table. Its P1 rows (planet class on the sector line, empty holds and fighter and shield room, daily production on your planet) are on the cockpit. Later notes closed the table's follow-ups: NavHaz on the sector line, the avoid list on Computer O, the rank ladder on the reference, and the class-M colonist trend when that line is present. The colonist long-haul in that plan has no missing cockpit step.

What is still not a full original game for a seat that only reads this surface:

- The fidelity switches stay legacy, so the numbers on screen are the legacy game until Ben flips a switch. The seat believes the screen.
- Class M production ratios (NOTE 41 item 10) stay Ben's call.
- The 3D map stays out. The 2D map is already on the main screen.
- The voice front end is not this slice.

## Success bar

A 10-day headless seat passes when it finishes 10 days using only the reads and posts above, never opens the universe, and a human can replay that same log from the redesign cockpit. The scripted-match digests stay the legacy digests because this seat is not in those matches.

This slice does not claim that 10-day bar. Its bar is day 1 on a test server: read the reference, leave StarDock, warp one hop the cockpit lists, then buy one unit if that port's trade form is open, otherwise wait.
