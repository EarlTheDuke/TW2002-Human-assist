# Bots use corporations

`CORP_BOTS_MODE` `tw2002` | `legacy`. Legacy is the engine before this slice. Code bots do not create, join, or use a corporation, any member may buy a Corporate FlagShip, a FlagShip pilot may join, and the member planet list has no production or stock.

Sources: Iago, the MBBS manual, the Corporate FlagShip note, the Cabal corps page, the EIS corporate menu, the TWGS Bible, and `CORP_RULES.md`. TWGS 3.11 is the default. MBBS breaks ties. A strategy row says how a bot chooses to use a rule. It does not change the engine.

## Rules

| # | Rule | Mark | Constant | Test |
| --- | --- | --- | --- | --- |
| bc1 | The mode is on in a tw2002 game that already has corp rules. The default bot policy is pair. Off and team are the alts | OURS | `CORP_BOTS_MODE` tw2002, `BOT_CORP_POLICY` pair, `BOT_CORP_TEAM_SIZE` 3 | `test_bc1_mode` |
| bc2 | Partners are consecutive SeatBrain seats before day 1. N3,N3,N2,N2,N1,H pairs P1+P2 and P3+P4. N1 and H stay solo. An explicit pair list overrides that. No rng | OURS | `BOT_CORP_PARTNERS` consecutive | `test_bc2_pairs` |
| bc3 | The lower seat id founds on day 1, before its first trade, wherever create is legal. The ticker is the first three letters of its name | STRATEGY | — | `test_bc3_founder` |
| bc4 | The C.E.O. then sets a 6-character password from the game seed and the ticker. The password is not in a thought, a memo, a report, or saved memory | CONFIRMED length; derivation OURS | `BOT_CORP_PASSWORD_LEN` 6 | `test_bc4_password` |
| bc5 | The C.E.O. invites only its partner, and retries at most 3 days | CONFIRMED invite; retry OURS | `BOT_CORP_INVITE_RETRIES` 3 | `test_bc5_invite` |
| bc6 | The partner joins with the ticker and password from that invite, and ignores every other invite | CONFIRMED join; who OURS | `BOT_CORP_ACCEPT_INVITES` partner_only | `test_bc6_join` |
| bc7 | Opposite sides still form the corp when tomorrow's mixed loss is at most 400 experience. Above that, the evil partner leaves | STRATEGY | `BOT_CORP_MIXED_POLICY` allow, `BOT_CORP_MIXED_MAX_PENALTY` 400 | `test_bc7_mixed` |
| bc8 | A corp bot deploys fighters and mines as corporate. A solo bot does not add an ownership argument | CONFIRMED | — | `test_bc8_deploy` |
| bc9 | Corp mates, and deployments that carry the corp ticker, are friends. Rogue groups and rival corps stay hostile | CONFIRMED | — | `test_bc9_friends` |
| bc10 | The partner uses the C.E.O.'s home sector | STRATEGY | `BOT_CORP_SHARED_HOME` True | `test_bc10_home` |
| bc11 | Planets the pair claim are corporate. Only one member builds a citadel step at a time | CONFIRMED planets; builder OURS | `BOT_CORP_SINGLE_BUILDER` True | `test_bc11_planets` |
| bc12 | In the same sector, the richer partner hands over a shortfall plus 1,000, at least 5,000, once a day. A purchase the buyer can afford does not wait | STRATEGY | `BOT_CORP_TRANSFER_PAD` 1000, `BOT_CORP_MIN_TRANSFER` 5000 | `test_bc12_credits` |
| bc13 | A good member over the tax line gives the excess to an evil mate in the same sector instead of banking it | STRATEGY | `BOT_CORP_TAX_SHIELD` True | `test_bc13_tax` |
| bc14 | A member may take fighters or shields from a mate in the same sector. The giver keeps 30 percent. Negative amounts do not exist | CONFIRMED transfer; keep OURS | `BOT_CORP_KEEP_FIGHTERS_PCT` 30 | `test_bc14_topup` |
| bc15 | A meetup is at most 3 hops and 30 turns. Otherwise the bot does not detour | STRATEGY | `BOT_CORP_MEET_MAX_HOPS` 3, `BOT_CORP_MEET_MAX_TURNS` 30 | `test_bc15_meet` |
| bc16 | Only the C.E.O. keeps surveying once StarDock is known. The partner trades. Survey returns if the C.E.O. is gone | STRATEGY | `BOT_CORP_EXPLORER` ceo | `test_bc16_explorer` |
| bc17 | Hunt, rob, steal, capture, tow, photon, and attack never pick a mate | CONFIRMED | — | `test_bc17_mates` |
| bc18 | The C.E.O. sends at most one memo a day, and only when something changed. The text has no password and no credit figure | CONFIRMED memo; text OURS | — | `test_bc18_memo` |
| bc19 | If the partner is gone, the survivor plays solo. If the C.E.O. leaves, the corp dissolves and the partner does not found another | CONFIRMED dissolve; refound OURS | `BOT_CORP_REFOUND` False | `test_bc19_loss` |
| bc20 | Only the C.E.O. considers buying the Corporate FlagShip | CONFIRMED | `BOT_CORP_FLAGSHIP` ceo | `test_bc20_flagship_choice` |
| bc21 | Corp bots do not flag a ship corporate or use ship transport. That policy stays off | CONFIRMED | — | `test_bc21_no_corpship` |
| bc22 | At most 6 free corp actions a day. The count resets at the day tick | OURS | `BOT_CORP_MAX_FREE_ACTIONS_PER_DAY` 6 | `test_bc22_cap` |
| bc23 | Pairing, role, home, and the free-action count persist in seat memory. Corp code does not draw the universe rng | OURS | — | `test_bc23_memory` |
| bc24 | Only the C.E.O. may buy a Corporate FlagShip, including a spare. An ex-C.E.O. keeps flying one. The alt would also stop a non-C.E.O. from boarding | SOURCE-CONFLICT | `CFS_CEO_RULE` purchase | `test_bc24_ceo_buys` |
| bc25 | A pilot flying a FlagShip cannot be invited or join. Creating a corp is still allowed. A parked FlagShip does not count | CONFIRMED refuse; create UNVERIFIED | `CFS_HOLDER_MAY_JOIN` False, `CFS_HOLDER_MAY_CREATE` True, `CFS_JOIN_CHECK` flown | `test_bc25_flagship_join` |
| bc26 | A member's planet list adds the planet id, daily production, and stock. Rivals do not see that | CONFIRMED | — | `test_bc26_planet_list` |
| bc27 | The match report counts corps, joins, transfers, corporate deployments, and FlagShips. It never prints a password | OURS | — | `test_bc27_report` |
| bc28 | The planetary lab's corp table follows tw2002 leave when corp rules are on, and the legacy leave otherwise | OURS | — | `test_bc28_lab` |
| bc29 | Every corp verb a bot emits is legal. Rejected stays 0 | OURS | — | `test_bc29_legal` |
| bc30 | A bot decides from its own observation. It does not read another seat's memory | CONFIRMED | — | `test_bc30_fog` |
| bc31 | Policy off emits no corp verb. The FlagShip and planet-list rules still apply, so a digest moves only when those rules are exercised | OURS | — | `test_bc31_off` |
| bc32 | GAP 10 and the corp rules doc name this slice for the bot policy, the FlagShip gates, and the planet list | OURS | — | `test_bc32_docs` |

## SOURCE-CONFLICT

- bc24 who the FlagShip rule binds: `CFS_CEO_RULE` purchase (only the C.E.O. may buy one) vs use (only the C.E.O. may fly one).

## UNVERIFIED

bc25 a FlagShip pilot may found a corp (`CFS_HOLDER_MAY_CREATE` True). A parked FlagShip does not block a join (`CFS_JOIN_CHECK` flown).

## Deliberate differences

Pairs are assigned before day 1. The password is derived from the seed and handed over only on the invite. Credit pooling uses a corp transfer, not the bank. Bots never send a negative transfer. The heuristic seat stays solo. Prompt text is unchanged.

## Match, seed 250925, 10 days

`scripts/run_scripted_match.py --seats N3,N3,N2,N2,N1,H --days 10 --seed 250925 --corp-report`. Rejected 0, exceptions 0, both runs. Policy off formed no corp. Policy pair formed N3P (P1, P2) and N2P (P3, P4) on day 1: 2 creates, 2 passwords, 2 invites, 2 joins, 12 transfers, 0 mate-on-mate attacks. Corporate deployments were 0 in both runs. The seats bought mines and did not lay them.

Policy off is the same net worth as the alien-traders ignore run. The paired seats together finished a little under their solo total. The N3 pair gained (1,144,181 vs 1,042,805). The N2 pair lost (748,900 vs 916,098) because the solo N2-P4 bought a battleship and the paired seats stayed in CargoTrans.

| Seat | Off net worth | Pair net worth | Off ship | Pair ship | Off deaths | Pair deaths |
| --- | --- | --- | --- | --- | --- | --- |
| N3-P1 | 828,617 | 619,960 | battleship | cargotran | 0 | 0 |
| N3-P2 | 214,188 | 524,221 | cargotran | cargotran | 0 | 0 |
| N2-P3 | 335,428 | 386,390 | cargotran | cargotran | 0 | 0 |
| N2-P4 | 580,670 | 362,510 | cargotran | cargotran | 0 | 0 |
| N1-P5 | 169,056 | 296,257 | scout | cargotran | 1 | 0 |
| H-P6 | 7,975 | 7,975 | scout | scout | 4 | 2 |

## Match, seed 4242, 10 days, pair

Same seats. Exceptions 0. Corps N3P and N2P, 10 transfers, 0 mate attacks, 0 corporate deployments. N2-P4 had one engine reject: a trade that wanted 25 holds with 20 free. That is a trade, not a corp verb.

| Seat | Pair net worth | Ship | Deaths |
| --- | --- | --- | --- |
| N3-P2 | 623,798 | battleship | 0 |
| N2-P4 | 508,720 | cargotran | 1 |
| N3-P1 | 487,562 | battleship | 0 |
| N1-P5 | 415,256 | merchant cruiser | 0 |
| H-P6 | 359,143 | merchant cruiser | 0 |
| N2-P3 | 347,544 | cargotran | 1 |

Policy off on the same seed also had that one trade reject, on N2-P4, and no corp events. The reject is not a corp verb.

| Seat | Off net worth | Pair net worth | Off ship | Pair ship | Off deaths | Pair deaths |
| --- | --- | --- | --- | --- | --- | --- |
| N3-P1 | 154,345 | 487,562 | scout | battleship | 1 | 0 |
| N3-P2 | 824,873 | 623,798 | battleship | battleship | 0 | 0 |
| N2-P3 | 529,402 | 347,544 | cargotran | cargotran | 0 | 1 |
| N2-P4 | 335,134 | 508,720 | scout | cargotran | 2 | 1 |
| N1-P5 | 432,305 | 415,256 | merchant cruiser | merchant cruiser | 0 | 0 |
| H-P6 | 7,975 | 359,143 | scout | merchant cruiser | 3 | 0 |
