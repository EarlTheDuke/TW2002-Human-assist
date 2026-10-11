# cockpit-audit-v1

2026-10-11. Docs only. No new switch. The bot screen is `web/bot.html` plus `web/bot.js`.

The screen already has a button for the verbs in the always-on row and the four groups. A button the engine marks illegal stays on screen, disabled, with the engine's reason. A refused action prints FAILED and the error. Hold slot is the H button. End turn is Wait (E). Rank, experience, alignment, credits, and turns left are on the status line.

## On the screen

Always on: warp, scan, wait, trade, plot_course, probe.

Combat: attack, retreat, pay_toll, surrender, photon_missile, deploy_fighters, deploy_mines, deploy_atomic, recall_deployed, ship_transwarp, ship_transport, tow_engage, tow_release.

StarDock: buy_ship, buy_equip, corp_create, sell_ship.

Planet: land_planet, liftoff, claim_planet, load_planet_cargo, dump_planet_cargo, assign_colonists, build_citadel, deploy_genesis, deposit_planet_defense, withdraw_planet_defense, set_military_reaction, deposit_treasury, withdraw_treasury, set_quasar_sector, set_quasar_atm, planet_transwarp, planet_buy_transporter, planet_transport, planet_destroy, planet_trade.

Comms: hail, broadcast, propose_alliance, accept_alliance, break_alliance, corp_invite, corp_join, corp_leave, corp_deposit, corp_withdraw, corp_memo, query_limpets.

## Not on the screen

These verbs exist in the engine. The bot page has no button and no form. A seat can still send them through the action API.

P0. terra_colonists. A human cannot pick up colonists at Terra. The colonize loop stops after the first genesis seed.

P1. The rest of a normal game that the screen cannot start:

- Bank: bank_deposit, bank_withdraw, bank_transfer.
- Hardware: cloak, fire_disruptor, remove_limpet, launch_beacon.
- Ports: rob, steal, port_upgrade, port_build.
- Corporation finish: corp_set_password, corp_drop, corp_transfer. Create is on the screen. Join refuses until a password is set, and that verb has no button, so a new corporation cannot take a member from this page.
- Ship flags: ship_set_corporate, ship_set_personal, ship_set_password.
- Police: apply_commission, post_reward, claim_reward.

P2. Flavor the screen does not offer: tavern_announce, tavern_talk, tavern_graffiti, tavern_order, grimy_ask, grimy_curse, underground_enter, underground_contract, underground_claim, tricron, cineplex.

## Next

cockpit-fixes-v1 should put a button on every P0 and P1 verb. P2 can wait. The switch for any behavior change is COCKPIT_FIX_MODE, and it stays off until that slice.
