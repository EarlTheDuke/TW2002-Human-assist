# What the planet work changed

Each line is one slice, from stocking a planet through what happens when a corp ends.

**B1 Stocking.** You can move fighters and shields between your ship and your planet with `deposit_planet_defense` and `withdraw_planet_defense`. The planet can hold `PLANET_FIGHTER_CAP` fighters (1,000,000). Ten ship shields become one planet shield. `PLANET_DEFENSE_MIN_LEVEL` is 0, so this works before the citadel is fancy. The old game let you stock a planet once it could fight. We match the move, and we differ on purpose by leaving the level gate open.

**B2 Treasury.** `deposit_treasury` and `withdraw_treasury` move credits into the planet. A level 1 citadel earns `PLANET_TREASURY_INTEREST_PCT` (2 percent) a day, up to `PLANET_TREASURY_CAP`. The old game had a planet bank that earned interest. We match that.

**B3a Level names.** `CITADEL_PERK` is the one list of what each level says it does. The old game had a ladder of citadel tricks. We match the ladder we wrote down. Some tricks say "not yet" until a later slice turns them on.

**B3b No free army.** `CITADEL_GIFT_FIGHTERS_PER_LEVEL` and `CITADEL_GIFT_SHIELDS_PER_LEVEL` are 0. Finishing a level adds no fighters and no shields. The old game handed you a garrison. We differ on purpose.

**B4 Fighter farms.** Each day, colonists on a planet can make fighters. The number depends on the planet class. No new action. The old game did this too. We match it.

**C1 Shield wall.** `PLANET_SHIELD_ODDS` is 20. While the planet still has shields, its fighters do not shoot, and a ship with no fighters cannot break the shields. The old game made shields hard to crack. We match that idea.

**C2 Fight odds.** Attackers shoot at `PLANET_OFFENSE_ODDS` 2. Defenders shoot at `PLANET_DEFENSE_ODDS` 3. `set_military_reaction` chooses how many fighters attack after the shields fall. The old game used those same odds. We match them.

**C3 Sector first.** Mines and fighters already in the sector hit you before the planet fight. The old game did the sector first. We match that. A landing on an ally is still a fight.

**C4 The fight is visible.** A siege writes a combat event the cockpit can show. The old game showed you the battle. We match that. The event does not add a new secret number.

**D1 Sector cannon.** `set_quasar_sector` and `QUASAR_MIN_LEVEL` 3. A hostile ship warping in can lose a percent of the planet's fuel, and that burned fuel divided by 3 is the damage. The old game had a quasar cannon. We differ on purpose: the damage math is the MBBS formula.

**D2 Air cannon.** `set_quasar_atm` and `QUASAR_ATM_FACTOR` 2. On a hostile landing the planet burns fuel before the shields, and again after they fall. Damage is twice the sector shot. The old game fired in the air too. We differ on purpose by using that double factor.

**D3 Photon damp.** `QUASAR_PHOTON_SHIELD_MIN` is 200. A photon shuts the cannons off for that ship's one approach, unless the planet is level 5 with 200 shields. The old game let a photon silence a weak cannon. We match that.

**D4 Interdictor.** `INTERDICTOR_MIN_LEVEL` 6 and `INTERDICTOR_FUEL` 500. A hostile warp out fails, the planet burns 500 fuel, and the sector cannon fires on what is left. The error is "interdicted by a planet". The old game's top citadel could hold a ship. We match that.

**D5a Planet move.** `planet_transwarp` at level 4, once a day, `PLANET_TRANSWARP_FUEL_PER_SECTOR` 400, to a sector that already has a fighter of the owner. Not into FedSpace. The old game could move a whole planet. We match the move. Alliance fighters do not count, which is a difference on purpose.

**D5b Personal hop.** `planet_buy_transporter` costs `PLANET_TRANSPORTER_COST_FIRST` (50000). `planet_transport` costs 50000 plus `PLANET_TRANSPORTER_COST_EXTRA` (25000) for each hop after the first, and `PLANET_TRANSPORTER_FUEL_PER_SECTOR` (10) from the planet. You move. The planet stays. The old game had a personal transporter. We match those prices. Alliance fighters do not count.

**E1 Class prices, switched off.** `CITADEL_CLASS_COSTS` is a table of colonist and ore prices, and `CITADEL_BUILD_TIME_SCALE` is 0.25. `CITADEL_COST_MODE` stays "credits", so the live game still charges credits. The old game charged goods based on the planet class. We differ on purpose by keeping credits, and the class mode is not turned on.

**E2 Destroy a planet.** `planet_destroy` costs 1 turn and `PLANET_DESTROY_ALIGNMENT` (50). The first use kills the colonists. The second removes the planet. Nothing is refunded. Friendly planets and planets that still have fighters or shields are refused. The old game used atomics for this. We differ on purpose: atomics still do not delete the planet. This action does.

**E3 Corps.** When the last member leaves, planets lose that corp ticker. A living owner keeps the planet. A planet with no living owner is abandoned with the old orphan event. Someone who leaves keeps their own planets and cannot run a former friend's planet. The old notes wanted only the boss's sector to stay owned, and wanted allies to skip the fight. We differ on purpose: every living owner keeps their planet, and landing on an ally is still a siege.

## Differences on purpose

Citadel builds still cost credits. The class-goods table is in the code and switched off.

Quasar damage is the MBBS formula: burned fuel divided by 3. The air shot multiplies that by 2.

Build times are the old day counts times 0.25, and never shorter than 1 day, so they fit a 30-day game.

A planet transwarp or transporter hop needs a fighter of the owner or a corp mate. A fighter that belongs only to an ally does not count.

## Not done yet

A scanner still does not hide fighters and shields from strangers. That fog slice was not built.

Class-table citadel mode is still dark. The game charges credits.
