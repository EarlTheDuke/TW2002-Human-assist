# Alien traders

`ALIEN_MODE` `tw2002` | `legacy`. Legacy is the engine before this slice: no alien records, no alien movement, and attack targets are only players, Ferrengi, and Feds.

Sources: the TWGS Bible, the v3 Trade Wars and computer-display docs, Iago, Gypsy, the MBBS manual, the v3.11 revision notes, and the ALIENS.DAT field list. TWGS 3.11 is the default. MBBS breaks ties. Gold-mode aliens stay out (GAP 8.9).

## Rules

| # | Rule | Mark | Constant | Test |
| --- | --- | --- | --- | --- |
| al1 | Classic aliens run in every tw2002 game. Population 0 is the alt | SOURCE-CONFLICT | `ALIEN_SOURCE` classic, `ALIEN_POPULATION_PER_1000` 40 | `test_al1_population` |
| al2 | An alien is not a player. It has a name, a ship name, a hull, experience, alignment, and credits | CONFIRMED fields; names UNVERIFIED | `ALIEN_NAMES` | `test_al2_record` |
| al3 | They start scattered in non-FedSpace sectors that have no deployments. Only the alien rng is drawn | UNVERIFIED start | `ALIEN_START` scatter | `test_al3_scatter` |
| al4 | A dead or captured alien is replaced at StarDock on the next day tick. The live count stays at the population | CONFIRMED entry; delay UNVERIFIED | `ALIEN_RESPAWN_DELAY_DAYS` 1 | `test_al4_respawn` |
| al5 | About half are good and half evil. Alignment magnitude is 50 to 500 | UNVERIFIED split | `ALIEN_GOOD_PCT` 50, `ALIEN_ALIGN_MIN` 50, `ALIEN_ALIGN_MAX` 500 | `test_al5_sides` |
| al6 | Hull, fighters, shields, experience, credits, and corbomite grow with the day and are capped | CONFIRMED that they grow and cap; numbers UNVERIFIED | `ALIEN_HULLS_BY_DAY`, `ALIEN_FIGHTERS_BASE` 300, `ALIEN_FIGHTERS_PER_DAY` 20, `ALIEN_SHIELDS_BASE` 50, `ALIEN_SHIELDS_PER_DAY` 5, `ALIEN_EXP_CAP` 5000, `ALIEN_CREDITS_CAP` 100000, `ALIEN_CORBOMITE_MAX` 5 | `test_al6_age` |
| al7 | Each day an alien takes 3 hops into neighbours with no deployed fighters. No legal neighbour means it stays. Rogue and corporate fighters block too | CONFIRMED block; hop count UNVERIFIED | `ALIEN_HOPS_PER_DAY` 3 | `test_al7_hops` |
| al8 | Armid mines hit an alien the way they hit a Ferrengi. A mine kill pays nothing and does not blast corbomite. Limpets do not attach | CONFIRMED mines; reward UNVERIFIED | `ALIEN_MINE_KILL_REWARD` False, `ALIEN_LIMPETS` False | `test_al8_mines` |
| al9 | Aliens never attack | UNVERIFIED | `ALIEN_AGGRESSION` never | `test_al9_never_attack` |
| al10 | A live alien in your sector is an attack target `alien:<n>`, from your ship, at the normal turn cost | CONFIRMED | — | `test_al10_target` |
| al11 | Combat uses the alien's hull odds. Shields fall before fighters | CONFIRMED | — | `test_al11_odds` |
| al12 | Fighters and shields lost stay lost. No regeneration | CONFIRMED | `ALIEN_REGEN` False | `test_al12_damage_persists` |
| al13 | After a hit it survives, it flees like a trader. Always-flee is the alt. A neighbour with fighters, or an interdictor, holds it | SOURCE-CONFLICT; interdictor UNVERIFIED | `ALIEN_FLEE_RULE` player, `ALIEN_INTERDICTED` True | `test_al13_flee` |
| al14 | A fedsafe alien in FedSpace is protected like a fedsafe trader | CONFIRMED | — | `test_al14_fedsafe` |
| al15 | Opposite side pays floor(exp / 2). Same side pays floor(exp / 4). The trader-kill award is the alt | SOURCE-CONFLICT | `ALIEN_KILL_EXP_RULE` bible | `test_al15_experience` |
| al16 | Alignment moves against the alien by half the alien's alignment | UNVERIFIED share | `ALIEN_KILL_ALIGN_SHARE` 0.5 | `test_al16_alignment` |
| al17 | The killer takes the alien's credits. No bounty | UNVERIFIED | `ALIEN_LOOT_CREDITS` True, `ALIEN_BOUNTY` 0 | `test_al17_loot` |
| al18 | A destroyed alien blasts the killer with its corbomite. Capture and mine death do not | CONFIRMED | — | `test_al18_corbomite` |
| al19 | A beaten alien can be captured under the existing capture rules. Legacy capture destroys it | CONFIRMED | `ALIEN_CAPTURE` True | `test_al19_capture` |
| al20 | Aliens do not trade at ports | UNVERIFIED | `ALIEN_PORT_TRADE` False | `test_al20_no_trade` |
| al21 | Experience, alignment, credits, and hull stay at the spawn values except for combat losses | UNVERIFIED | — | `test_al21_static` |
| al22 | An alien cannot join a corporation. Feds and Ferrengi ignore aliens | CONFIRMED no corp; NPC fights UNVERIFIED | `ALIEN_NPC_FIGHT` False | `test_al22_not_a_player` |
| al23 | Each alien adds 40 to the density, the same as a manned ship | CONFIRMED | `DENSITY_PER_SHIP` 40 | `test_al23_density` |
| al24 | Sector views, holo scans, and probes list aliens on their own key, with the real hull | DERIVED | — | `test_al24_view` |
| al25 | Alien Trader Ranks lists every live alien's rank, side, and experience. No location | CONFIRMED | — | `test_al25_ranks` |
| al26 | Spawn, sight, flee, mine, and capture are their own events. A kill is ship-destroyed with kind alien | DERIVED | — | `test_al26_events` |
| al27 | Placement, hops, and flee draw the alien rng only. The universe rng is unchanged | DERIVED | — | `test_al27_rng` |
| al28 | An empty alien map is omitted from the save, so a legacy dump stays the same | DERIVED | — | `test_al28_save` |
| al29 | Bots ignore aliens. An align-hunt policy is the alt | DERIVED | `BOT_ALIEN_POLICY` ignore, `BOT_ALIEN_MARGIN` 1.5 | `test_al29_bot` |
| al30 | One prompt line, only when the mode is on and an alien is in the sector | DERIVED | — | `test_al30_prompt` |
| al31 | The legal attack list and the handler agree on which aliens can be shot | DERIVED | — | `test_al31_legal` |
| al32 | Feds refuse fighter sectors, Ferrengi ignore them and hit mines, aliens refuse them and hit mines | CONFIRMED pieces | — | `test_al32_gap_8_8` |

## SOURCE-CONFLICT

- al1 who runs: `ALIEN_SOURCE` classic (the Bible, Iago, Gypsy) vs off (Big Bang "Internal Alien Traders : No", because Gold uses NONPSERV).
- al13 flee: `ALIEN_FLEE_RULE` player (same check as a trader) vs always (MBBS: the victim flees after every shot).
- al15 kill experience: `ALIEN_KILL_EXP_RULE` bible (half if opposite, quarter if the same) vs player (the trader-kill award plus 10 percent).

## UNVERIFIED

al1 count (`ALIEN_POPULATION_PER_1000` 40). al2 names (`ALIEN_NAMES`). al3 start (`ALIEN_START` scatter). al4 delay (`ALIEN_RESPAWN_DELAY_DAYS` 1). al5 split and magnitude (`ALIEN_GOOD_PCT` 50, `ALIEN_ALIGN_MIN` 50, `ALIEN_ALIGN_MAX` 500). al6 the age numbers (`ALIEN_HULLS_BY_DAY` and the fighter, shield, experience, credit, and corbomite constants). al7 hop count (`ALIEN_HOPS_PER_DAY` 3). al8 a mine kill pays nothing and limpets do not attach (`ALIEN_MINE_KILL_REWARD` False, `ALIEN_LIMPETS` False). al9 they never attack (`ALIEN_AGGRESSION` never). al13 an interdictor holds them (`ALIEN_INTERDICTED` True). al16 the alignment share (`ALIEN_KILL_ALIGN_SHARE` 0.5). al17 credits and no bounty (`ALIEN_LOOT_CREDITS` True, `ALIEN_BOUNTY` 0). al20 no port trade (`ALIEN_PORT_TRADE` False). al22 Feds and Ferrengi ignore them (`ALIEN_NPC_FIGHT` False).

## Deliberate differences

Day-tick hops instead of a real-time one-in-twenty. Aliens are not players, so they are absent from victory, net worth, and the seat list. They do not trade, and they do not attack. Gold races, homespace, grudges, and regeneration stay out. Photons, quasar cannons, and atomics ignore aliens in this slice.
