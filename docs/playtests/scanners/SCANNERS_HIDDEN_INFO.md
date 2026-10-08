# Scanners and hidden information

Rules table first, then what the engine does. Sources are the files under `docs/reference/tw2002/` (gap map rows 4.6, 4.11 to 4.14, 6.1 and 13.5). Marks: CONFIRMED (a source prints it), SOURCE-CONFLICT (sources disagree, the reading is given), UNVERIFIED (no source prints it; the value here is chosen and says so).

Today's build (before this slice, kept as `INFO_MODE = "legacy"`): every seat sees the full contents of every adjacent sector for free in `adjacent` (port code, deployed fighter count and owner, mine total, planets yes/no, occupant ids). `scan` needs no hardware, costs 1 turn and has three tiers: `basic` (one hop, port codes, fighters, occupants), `density` (two hops, counts) and `holo` (one hop, full intel including port stock and prices, mines). An ether probe reports one sector, is never destroyed and gives 3 experience. Port intel (`known_ports`) is a snapshot taken when you visit, scan or probe, and ages until you look again. Every mine in your own sector is listed, other traders' limpets included.

## Rules table

| # | rule | original | mark and source | this slice |
| --- | --- | --- | --- | --- |
| s1 | Density scanner | Hardware Emporium item ("Long Range Scanners"). The cheaper scanner: the relative density of the surrounding sectors, and a warning of a non-standard, undefinable mass. Iago's StarDock price list: 2,000. A TWGS editor dump: 500. | CONFIRMED that it is bought hardware: `eis_tw2002_v3_docs/HardwareMenu.html` (R), `S3_tw2002_bible_v1.htm` ("go to the hardware emporium 'H' and buy a DENSITY scanner"). SOURCE-CONFLICT on the price: `stardock_manuals_and_text_docs/Iago_War_Manual.txt` (2,000), `cabal_strategy_site/twgs.html` and `stardock_modernmanual/advanced__twgs-settings.md` (500, in a table where other items are 4x or 1/4 of Iago's, so a customised game). | Built: `buy_equip item=density_scanner`, 2,000 credits (Iago, the default list; the Bible's "at least 5,000 credits initially" fits it). |
| s2 | Holographic scanner | Has both density and holographic modes. Iago: 25,000. TWGS dump: 6,250. | CONFIRMED: `HardwareMenu.html` ("a Holographic Scanner which has both Density and Holographic capabilities"), Bible ("This scanner is a density scanner, but it also can be a scanner that graphically shows you exactly what's in the adjacent sectors"). SOURCE-CONFLICT on the price as in s1. | Built: `buy_equip item=holo_scanner`, 25,000 credits. A holo scanner also runs density scans. |
| s3 | Which hulls take which scanner | Some hulls take no scanner, some only the density one. | CONFIRMED for the restricted ones: `stardock_manuals_and_text_docs/Someguy_MBBS_manual.txt` (Scout "Density Scanner only", Missile Frigate "cannot carry a scanner (not even density)", T'Kasi "density scanner only, no holoscanner"), `stardock_manuals_and_text_docs/Gypsy_Big_Dummies_Guide.html` ship catalog ("Long Range Scan? No" for the Missile Frigate and Colonial Transport). The full H / D / N column is `stardock_manuals_and_text_docs/OldBBS_TW2002V8.faq.txt` (V2 beta 8) only, so holo versus density for the rest is UNVERIFIED for TWGS. | Built as `K.SCANNER_BY_HULL`: density only for Scout Marauder, Constellation, T'Khasi Orion; none for Missile Frigate, Colonial Transport and the escape pod (pod UNVERIFIED); holo for the other ten. |
| s4 | The scanner belongs to the ship | A new ship needs its own scanner. | CONFIRMED: `Gypsy_Big_Dummies_Guide.html` and `S7_softdocs_slice-10.txt` ("After buying a ship, buy a long range scanner for it"). | Built: `buy_ship` and the escape pod leave you with no scanner. |
| s5 | Density scan costs no turn | | CONFIRMED: Bible ("A Density scan doesn't take a turn, as a holographic scan does"). | Built: `scan tier=density` costs 0 turns. |
| s6 | What a density scan shows | For each adjacent sector: the density number, how many warps lead out, navigation hazard, and an anomaly flag. | CONFIRMED: Bible ("tells you how many warps lead out of the sectors around you, and what is in the sector, roughly"), `Someguy_MBBS_manual.txt` ("Anom" column), `eis_tw2002_v3_docs/Navigate.html` (S: densities, navigational hazards, "non-standard, undefinable mass"). | Built: `density`, `warps`, `navhaz` (always 0, this game has no nav hazards) and `anomaly`. |
| s7 | Density values | 0 cloaked ship (anomaly), 1 beacon, 2 limpet mine (anomaly), 5 per fighter, 10 per armid mine, 21 per 1 percent nav hazard, 38 unmanned ship, 40 manned ship (trader, alien or Ferrengi assault trader), 50 destroyed port, 77 Ferrengi Scorpion, 100 port (or Ferrengi Battle Cruiser / Dreadnaught), 462 / 489 / 512 the three Feds, 500 planet. Densities add up. | CONFIRMED: Bible and `Someguy_MBBS_manual.txt` print the same list ("Remember that Densities are cumulative"). | Built for what this game has: 5 per deployed fighter, 10 per armid mine, 2 per limpet mine (and the anomaly), 40 per ship (player or Ferrengi; the Bible's split by Ferrengi type is not modelled, UNVERIFIED), 100 per port, 500 per planet. A destroyed port leaves no wreck here (0, not 50). No beacons, nav hazards, unmanned ships, Feds or cloaks exist in this game. |
| s8 | Holo scan costs one turn | | CONFIRMED: `HardwareMenu.html` ("uses a small amount of your ship's fuel (one turn's worth)"), `Navigate.html` ("all for just the cost of one turn"), Bible. | Built: `scan tier=holo` costs 1 turn. |
| s9 | What a holo scan shows | What and who is in each adjacent sector: ports, planets, hazards, other players. | CONFIRMED: `HardwareMenu.html`, `Navigate.html` ("you will be able to see ports, planets, hazards and other players"), `classictw_museum_wiki/tw-attac_TW2002_v3_revision_history_to_v3.11.html` ("Long range scan now reports other users in scanned sectors"). Limpets never show: CONFIRMED `stardock_modernmanual/core__navigation.md` ("Limpet mines are invisible on holoscans or E-PROBE scans"). That the holo shows the sector display only (port class, not stock) is UNVERIFIED. | Built: per adjacent sector the port (name and class code, no stock or prices), planets (name and class, no owner or garrison), traders (name, ship, fighters), Ferrengi (name, fighters), deployed fighters (count, owner, mode) and armid mines (count, owner). No limpets. |
| s10 | A holo scan does not explore | The computer's "known universe" fills from sectors you travel through or probe. | UNVERIFIED for the holo (the sources describe exploring by travel and probes: `eis_tw2002_v3_docs/CompNavigation.html` K, `Iago_War_Manual.txt`). | Built: a holo scan does not add warps to `known_warps` and does not turn on the port report for that sector. |
| s11 | Entering a sector | The sector display: sector, ports (name, class), planets, traders "w/ N ftrs, in <ship>", unmanned ships, deployed fighters (count, owner, mode), warps out. | CONFIRMED: `stardock_manuals_and_text_docs/Misc_shipodds.txt` (sector 334 display), `cabal_strategy_site/economy2.html`. How mines are listed is UNVERIFIED. | Built: the current sector gains `traders` (every other player here: name, ship name, ship type, fighters aboard). Fighters, ports, planets and Ferrengi as today. Mines as today minus other players' limpets. |
| s12 | What stays hidden | Other traders' limpets ("sit almost invisible"), cloaked ships, corbomite, a planet's owner and garrison unless you have a planet scanner or land, and anything in a sector you have not entered, scanned or probed. | CONFIRMED: `HardwareMenu.html` (L limpets, C corbomite "no way to detect", D cloak, F planet scanner), `Someguy_MBBS_manual.txt` (invisible limpets, cloak anomaly), `Navigate.html` (adjacent sectors are what a scanner is for). | Built: in tw2002 `adjacent` keeps only the sector id, the explored flag, the port you remember and your own last scan of that sector. Other players' limpets are hidden everywhere (they still add 2 density each). Planet garrisons were already hidden from non-owners. Cloaks and corbomite do not exist here. Decided in slice 64 (cl6): a corp mate sees corporate limpets only. |
| s13 | Ether probe | Fired from anywhere to anywhere. Reports every sector passed through; the data goes into your computer "just as if you'd physically traveled that route". Any hostile fighter, in any mode, destroys it, and you are told. It self-destructs at the destination. Limpets do not show. | CONFIRMED: `Iago_War_Manual.txt` ("What are eprobes", "Hostile ftrs in a sector will destroy eprobes passing through regardless of which mode"), `HardwareMenu.html` (E), Bible ("It's like a moving Holo Scanner that goes multiple sectors"), `S7_softdocs_slice-10.txt` ("limpets don't show on eprobes"). The route is the shortest path (UNVERIFIED) capped at 45 hops (TWGS "Maximum Course Length : 45", `cabal_strategy_site/twgs.html`; that probes use it is UNVERIFIED). | Built: the probe flies the shortest path over the real warps. Each sector it passes is explored (warps learned, port recorded) and logged in `probe_log` with what a holo would show. The first sector holding fighters that are not yours, your corp's or an ally's destroys it; that sector is logged as the place it died, with nothing else. You get the report; the fighters' owner is not told (UNVERIFIED either way). |
| s14 | Probe turn cost | Bible: "takes one turn". Bible and EIS also sell it as a way to explore with "no turns left" / without using your turns. | SOURCE-CONFLICT: `S3_tw2002_bible_v1.htm`, `HardwareMenu.html`. | Kept at 1 turn (today's value, the one number a source prints). |
| s15 | Probe price | Iago 3,000; TWGS dump 12,000; this game 5,000. | SOURCE-CONFLICT. | Not changed (5,000). Out of scope. |
| s16 | Port report (CIM) | Relatively up-to-date information about any port in a sector you have explored: items traded, buying or selling, units on offer and percent of maximum. | CONFIRMED: `eis_tw2002_v3_docs/CompNavigation.html` (R), `stardock_manuals_and_text_docs/Someguy_TWINSTR.txt`, `Gypsy_Big_Dummies_Guide.html`. | Built: every `known_ports` entry for an explored sector (visited or probed) shows the live stock each turn (`report: "live"`, age 0). Prices stay in the entry (deliberate difference below). |
| s17 | Hostile fighters block the port report | Any hostile fighter in the port's sector occludes the report. | CONFIRMED: `Iago_War_Manual.txt` ("Hostile ftrs (again regardless of mode) will also block (occlude) the CIM report"), `CompNavigation.html` ("there may be enemy forces in that sector interfering with your computer's scan"). | Built: such an entry keeps the remembered snapshot and says `report: "blocked"`. |
| s18 | Port report delay | TWGS setting: new data only every N minutes. | CONFIRMED that it exists: `classictw_museum_wiki/TWGS_v2_Revision_History.html`. | Not built (no delay). |
| s19 | Experience for scans and probes | Not among the ways to gain experience. | UNVERIFIED (absent from the lists in `classictw_docs_wiki` Alignment and the cabal glossary, gap row 9.2). | Built: no experience for a scan or a probe in tw2002 (a free density scan would otherwise farm it). |
| s20 | Planet scanner | Shows creator, owner and defences of a planet without landing. | CONFIRMED: `HardwareMenu.html` (F), Bible. | Not built. Garrisons stay hidden from non-owners as today. |

## Switch

`K.INFO_MODE` defaults to `tw2002`. `legacy` is today's fog, unchanged: `test_legacy_fog_is_unchanged` compares observation and prompt digests recorded on 4b8fd31 and re-checked identical on origin 73971b3.

## What the engine does (INFO_MODE tw2002)

- `Ship.scanner` is `None`, `"density"` or `"holo"`. StarDock sells `density_scanner` (2,000) and `holo_scanner` (25,000) through `buy_equip`, qty 1. A hull takes the best scanner `K.SCANNER_BY_HULL` allows; a holo replaces a density scanner; nothing is offered that the hull cannot carry or that would not be an upgrade. `buy_ship` and losing the ship clear it. Net worth counts it at cost.
- `scan` is only legal with a scanner. `tier` choices are the fitted scanner's modes (`density`, plus `holo` on a holo scanner) with `turn_cost_by` `{density: 0, holo: 1}`. No scanner: illegal in the legal list and refused by the handler with the same reason.
- A density scan stores, per adjacent sector, `density`, `warps`, `navhaz` (always 0: this game has no nav hazard) and `anomaly` (limpets) in the scanner's memory. A later density scan refreshes those numbers and must not erase a prior holo reading of the same sector (QC). A holo scan also stores what is there: port name, code and class, planets (name, class), traders (name, ship name, ship type, fighters aboard), Ferrengi, deployed fighters (owner, count, mode) and mines without limpets (not even your own: limpets never show on a holo or a probe). No stock, no prices, no planet owners or garrisons. Neither scan explores (`known_warps`) or records port intel.
- `adjacent` in the observation: `id`, `known` and the port code you remember. Live contents are only filled from your own latest holo scan or probe pass (`fighter_count`, `fighter_owner`, `mines`, `has_planets`, `occupants`, `seen`, with `seen_day` / `seen_tick`), and your latest density reading adds `density`, `warps`, `navhaz`, `anomaly`, `scan_tier`, `scan_day`, `scan_tick`. Old readings are not refreshed.
- Your own sector (`sector`): as before, plus `traders` (name, ship name, ship type, fighters aboard). `mines` hides other traders' limpets (yours and your corp's show).
- `probe target=N`: one probe, 1 turn, a shortest route of at most 45 hops. Each sector on the route is explored (`known_warps`, port intel) and logged in `probe_log` with what a holo scan would show, until the first sector holding fighters that are not yours, your corp's or an ally's (any mode). There the probe is destroyed and `probe_log` says `probe_destroyed`. The PROBE event goes to the firer only.
- `known_ports` entries carry `report`: `live` (explored sector, no hostile fighters: today's stock, prices and percent of max), `blocked` (hostile fighters in the port's sector: the old snapshot) or `remembered` (not explored, or the port is gone: the old snapshot).
- With COMBAT_MODE tw2002, the warp list no longer shows `toll_due_by`: the toll is announced by the challenge when you arrive.
- No experience for scans or probes.

## Deliberate differences

- Port reports keep the price this game quotes (the original CIM report shows quantity and percent; prices come from haggling at the port). Seats trade on quoted prices everywhere else, so the report keeps them.
- A holo scan does not add sectors to the computer's explored map (s10 is UNVERIFIED either way; probes and travel do).
- No experience for scans and probes (s19).
- Not in the density chart because the game does not have them: destroyed ports (50), beacons (1), cloaked ships (0), nav hazard (21 per percent), unmanned ships (38), Scorpions, BattleCruisers, Dreadnoughts and Feds. Every Ferrengi counts as a manned ship (40).
- COMBAT_MODE legacy with INFO_MODE tw2002 still filters unaffordable toll sectors out of the warp list (the legacy toll gate is a legal-list rule there). The default COMBAT_MODE tw2002 hides it.
- The fighters' owner is not told a probe was destroyed (TWGS does not say; nothing to copy).
- Not built: planet scanner, psychic probe, port report delay, the TWGS probe and scanner settings, and any per-day cap on probes. The ether probe price stays 5,000 (s15).
- The observation's dead-end-pocket hint (`action_hint`, M4-12) still peeks at whether the one neighbour of a one-warp sector leads back only here. The original's course plotter knows the whole map's lanes too, so this stays.

## Seat brains

No brain change. N1, N2 and N3 never buy a scanner or a probe; the explore step's `scan` is only taken when the legal list allows it (it does not without a scanner). They lose the free view of adjacent ports. Rejected actions stay 0 in tw2002 on every seed (`test_seat_brains_stay_legal_with_and_without_scanners`, and the table below).

Acceptance bars, day 10, `prove_growth_replay`, net worth:

| seed | N1 legacy | N1 tw2002 | N2 legacy | N2 tw2002 | N3 legacy | N3 tw2002 | organics zeros N2 legacy / tw2002 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 250925 | 704,460 | 473,887 | 611,823 | 653,191 | 941,555 | 923,538 | [32] / - |
| 20260925 | 450,086 | 301,012 | 416,937 | 844,548 | 1,005,049 | 940,383 | [30] / - |
| 230923 | 542,089 | 273,637 | 542,161 | 934,930 | 1,117,426 | 992,565 | - / - |
| 99 | 312,760 | 331,693 | 825,877 | 785,986 | 894,474 | 921,876 | - / - |
| 31 | 503,250 | 483,147 | 505,426 | 480,717 | 1,127,135 | 979,102 | - / - |

Rejected actions: 0 in all 30 runs.

`test_seat_bot_n2.py::test_n2_day10_beats_n1_and_keeps_organics` is pinned to legacy INFO_MODE: its held organics zeros and per-seed tolerances are legacy-fog measurements. Under tw2002 N2 beats N1 on four seeds by a wide margin and has no organics zeros at all, but seed 31 lands at 99.5 percent of N1 (480,717 vs 483,147), under the bar's "strictly win" for that seed. Retuning is the bot-growth slice's business. The N1 and N3 bars pass under tw2002.

## Planted bugs

Each bug was planted alone in the finished code, `tests/test_scanners_hidden_info_v1.py` run, and the file restored byte for byte (sha256 checked). 21 of 21 caught.

| # | planted bug | where | caught by |
| --- | --- | --- | --- |
| 1 | wrong density number (4 per fighter) | handler | `test_density_numbers_follow_the_chart`, `test_density_scan_costs_no_turn_and_needs_a_scanner` |
| 2 | limpets do not count / no anomaly | handler | `test_density_numbers_follow_the_chart` |
| 3 | scan without the device offered in the legal list | legal list | `test_density_scan_costs_no_turn_and_needs_a_scanner` |
| 4 | scan without the device accepted by the handler | handler | `test_density_scan_costs_no_turn_and_needs_a_scanner`, `test_observation_only_carries_what_the_device_reveals[none]` |
| 5 | holo scan cost not charged | handler | `test_holo_scan_costs_a_turn_and_shows_who_is_there` |
| 6 | density scan charged a turn | handler + legal list | `test_density_scan_costs_no_turn_and_needs_a_scanner`, `test_holo_scan_costs_a_turn_and_shows_who_is_there`, `test_switch_defaults` |
| 7 | adjacent sectors filled live (legacy view leaks into tw2002) | observation | `test_a_pod_landing_reaches_only_the_pilot`, `test_holo_scan_costs_a_turn_and_shows_who_is_there`, `test_observation_only_carries_what_the_device_reveals[density]` and more |
| 8 | density reading shows holo contents | observation | `test_observation_only_carries_what_the_device_reveals[density]` |
| 9 | other traders' limpets shown in your sector | observation | `test_entering_a_sector_shows_traders_and_hides_foreign_limpets` |
| 10 | probe ignores hostile fighters | handler | `test_a_destroyed_probe_reports_nothing_beyond`, `test_hostile_fighters_destroy_a_probe_friendly_ones_do_not` |
| 11 | a destroyed probe keeps reporting | handler | `test_a_destroyed_probe_reports_nothing_beyond` |
| 12 | port report ignores hostile fighters | observation | `test_port_report_live_blocked_remembered` |
| 13 | port report live for unexplored sectors | observation | `test_port_report_live_blocked_remembered` |
| 14 | scanner kept on buy_ship | handler | `test_scanner_goes_with_the_ship` |
| 15 | scanner kept on death | handler | `test_scanner_goes_with_the_ship` |
| 16 | hull limit ignored (frigate gets a scanner) | legal list + handler | `test_hull_caps_and_scanner_shop` |
| 17 | experience for a scan | handler | `test_no_experience_for_scans_or_probes` |
| 18 | scan neighbours leaked through EVENT_FACTS | observation | `test_legacy_fog_is_unchanged` |
| 19 | toll shown before warping in | legal list | `test_warp_toll_not_shown_before_arrival` |
| 20 | legacy fog drifts (adjacent mines counted per deployment) | legacy | `test_legacy_fog_is_unchanged` |
| 21 | pod sector back in the Ship Destroyed summary (1fe17f2) | observation | `test_a_pod_landing_reaches_only_the_pilot` |

## Before / after match

`scripts/run_scripted_match.py --seats N3,N3,N2,N2,N1,H --seed 250925 --days 10`. Before: origin 73971b3 (today's fog). After: this slice, INFO_MODE tw2002 (default). Day-10 values; rejected is check / engine.

| Seat | NW before | NW after | Credits before | Credits after | Ship before / after | Planets before / after | Deaths before / after | Sells before / after | P/u before / after | Rejected before / after |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N3-P1 | 884,249 | 909,726 | 693,276 | 728,959 | cargotran / cargotran | 3 / 3 | 0 / 1 | 240 / 249 | 55.1 / 62.2 | 0/0 / 0/0 |
| N3-P2 | 758,742 | 743,996 | 587,421 | 567,403 | cargotran / cargotran | 3 / 3 | 0 / 0 | 235 / 249 | 55.3 / 53.1 | 0/0 / 0/0 |
| N2-P4 | 612,615 | 363,467 | 394,856 | 270,831 | cargotran / merchant_cruiser | 2 / 2 | 0 / 0 | 222 / 348 | 44.0 / 50.2 | 0/0 / 0/0 |
| N2-P3 | 545,084 | 425,776 | 356,143 | 288,084 | cargotran / merchant_cruiser | 2 / 2 | 1 / 0 | 236 / 346 | 40.2 / 49.3 | 0/0 / 0/0 |
| N1-P5 | 406,374 | 239,020 | 300,150 | 49,003 | merchant_cruiser / cargotran | 2 / 1 | 0 / 1 | 357 / 106 | 50.1 / 50.4 | 0/0 / 0/0 |
| H-P6 | 41,170 | 181,145 | 18,400 | 173,170 | merchant_cruiser / scout_marauder | 0 / 0 | 0 / 1 | 0 / 219 | 0.0 / 31.5 | 0/0 / 0/0 |

The brains no longer see ports next door for free, and none of them buys a scanner. N3 keeps the lead. The N2 seats never reach the CargoTran upgrade in this match and N1 lands one planet fewer. The heuristic seat H takes a different path (it trades this time, loses its ship once and ends in a Scout); its route choice reads `adjacent`, so a changed view changes its random walk. Not traced further. Rejected actions stay 0 for every seat.

## Tests pinned to legacy INFO_MODE

They test something else and used the free scan or the legacy-fog numbers: `tests/test_ship_combat_core_v1.py` (autouse fixture; scans burn turns), `test_observation_memory.py::test_scan_records_current_sector_but_not_neighbor_topology`, `test_parity_s3.py::test_observation_and_llm_message_carry_legality`, `test_turn_cadence_g4.py` hold-slot tests, `test_human_agent_phase_h0.py::test_replay_from_human_match_does_not_crash`, `test_seat_bot_n2.py::test_n2_day10_beats_n1_and_keeps_organics`. The browser cockpit tests' match host (`tests/_cu_host.py`, `CuHost`) runs INFO_MODE legacy while it is open and restores the mode on exit: those tests press S for the free scan and read today's adjacent view, and they test the UI, not the scanner rules. Media fixtures did not change (re-recorded byte for byte), so `scripts/media_record_fixtures.py` is not pinned.

## QC fixes (scanners QC fixes)

Independent QC of 29257a1. Tests: `tests/test_scanners_qc_v1.py` (the first three failed on 29257a1).

| # | Bug | Fix |
| --- | --- | --- |
| q1 | A free density scan (also what the cockpit S key sends with empty args) replaced the whole `scan_memory` entry and erased a prior holo reading of that sector. | Density refreshes density / warps / navhaz / anomaly and keeps any prior holo view (`has_holo`, `holo_day` / `holo_tick`). Observation reads holo contents via `has_holo`, not `tier == "holo"`. |
| q2 | A holo / probe view still listed the viewer's own limpets. Sources say limpets never show on holo or e-probe. | `sector_view` drops every limpet. |

Checked and left as is:
- Browser cockpit (live `web/bot.js`, not only `CuHost`): SCAN is disabled without a scanner; the button title and CU toast show the legal-list reason (`no long range scanner ...`). No crash or hang. CuHost stays on legacy for the UI tests that press S for the free scan.
- Pins to legacy INFO_MODE (observation_memory scan, parity_s3, human replay, N2 day-10 bar, ship-combat autouse, turn-cadence holds): unpinning them fails only on expected fog/scanner differences (scan not legal, N2 seed 31 at 99.5 percent of N1, organics zeros). No hidden regression.
- Recommendation on the N2 bar pin: **keep it on legacy** until the follow-up where bots buy scanners. Under tw2002 N2 already beats N1 on four seeds and has no organics zeros; seed 31 is a 0.5 percent fog effect, not a bot bug. Retune the bar in that follow-up against the new fog with scanners for sale on the ladder.
