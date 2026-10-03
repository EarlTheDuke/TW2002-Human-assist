# TW2002 reference library (local copies)

Saved 2026-10-03 so we stop re-fetching. These are community write-ups. We do NOT have the official EIS manual or the game itself.

Target rule set (Commander's default, Ben can veto): Trade Wars 2002 v3.x as run by TWGS 3.11 (Planet Handbook v1.01 + Cabal Formulas).
Tie-break when TWGS and MBBS disagree, or sources conflict: the MBBS value when both write-ups agree on it; otherwise write the conflict down and keep a constant.

Files:
- S1_planet_handbook_v1.01.html  (Planet Handbook v1.01, Paladyne)
- S2_cabal_formulas.html         (Cabal "Formulas")
- S3_tw2002_bible_v1.htm         (TradeWars 2002 Bible, 1993, v1 only - older rules)
- S4_breakintochat_wiki.html     (overview)
- S6_wikipedia2007.html          (overview)
- S7_softdocs_slice-10.txt       (original docs excerpt)


---

## Addendum 2026-10-03 - extra reference sweep (TWGS 3.11 / MBBS focus)

All files below were fetched with curl from public pages. No binaries, installers or game archives were downloaded and nothing was executed.
Subfolders sit next to the older S1..S7 files above. Note: S3_tw2002_bible_v1.htm is byte-identical in size (680,426) to the 2007 TWGS-edited Bible
(stardock_manuals_and_text_docs\Bible_TWGS_edit_2007_Clme.htm), so S3 is probably the 2007 Clme TWGS update, not the 1993 v1 text; S1 = cabal planets.html, S2 = cabal formulas.html, S7 = Slice-10.

### Is original TW2002 / TWGS source code public? (short answer)
No. No source code for Martech's TW2002 (Turbo Pascal) or for EIS's TWGS has been publicly released. EIS (John Pritchett) owns the rights since 2000 and distributes only compiled TWGS/TW2002 builds.
The Museum's v1 release notes quote the line count and say the source is 881,484 bytes, which confirms it exists, but not that it is available.
What IS public: (a) source for the older TradeWars II / QuixPlus BASIC+Pascal lineage (TW2.PAS etc., e.g. SourceForge "tradewarsc" original source, tmcbbs TWSRC.ZIP) - a different, much older game; (b) clean-room clones (twclone etc.); (c) TWX Proxy / Mombot helper source, which only parses the game text. Rules for TW2002 therefore have to come from docs, changelogs and empirical testing. No decompilation write-up of TW2002.EXE was found.
MBBS version (HVS, Major BBS) source is also not public; HVS licensed it from Martech.

### Ranked list (best first)
1. cabal_strategy_site\formulas.html  <- https://www.thestardock.com/files/Site%20Caps/TWCabal/formulas.html (also planets.html, haggling.html, economy1-3.html, twgs.html, fleeing.html, pods.html, creating_planets.html)
   Best single source of exact numbers: order of events entering hostile sector / landing, fig & shield odds, planet pop/production/citadel costs, Q-cannon formulas (Classic/TWGS vs MBBS/Gold), exp+align gain formulas, hold cost formula, rob/steal formulas, density values, trader-flee rule. Covers TWGS (classic and Gold) and MBBS. No licence (fan site, 2005).
2. eis_tw2002_v3_docs\*.html  <- https://classictw.com/2002v3Docs/ (TradeWars.html, MainMenu, PlanetMenu, CitadelMenu, HardwareMenu, StarDockMenu, ShipyardMenu, CorporateMenu, CompDisplays, Tactical, GlobalCommands, SysOpNew/Updated, GeneralNew/Updated ...)
   Official EIS/Martech TW2002 v3.x in-game help/manual in HTML. Menu-level behaviour and text, not formulas. v3.05-era wording. Copyright EIS.
3. classictw_museum_wiki\tw-attac_TW2002_v3_revision_history_to_v3.11.html (<- http://www.tw-attac.com/tw2002revision.html) and TWGS_v2_Revision_History.html (<- https://wiki.classictw.com/index.php?title=TWGS_v2_Revision_History)
   Authoritative changelogs by the author: every behaviour change v3.00 -> v3.11 (TWGS 1.01) and TWGS v2.00-2.21/TW 3.14-3.35. Use these to decide what 3.11 actually does (port regen 1-200%/day std 5%, 2 pods/day limit, MBBS compat mode list, planet/port limits, Q-cannon atmos fix, etc.). Copyright EIS.
4. stardock_manuals_and_text_docs\Bible_TWGS_edit_2007_Clme.htm  <- https://www.thestardock.com/files/manuals/Trade_Wars_2002_Bible.htm
   TW2002 Bible updated for TWGS (2007): default ship/planet charts, ports, combat, citadels. Plus original v1x text TWBible_original_v1x.txt. TWGS-ish. Community text.
5. stardock_manuals_and_text_docs\Someguy_MBBS_manual.txt (+ addendum, TWINSTR) and classictw_museum_wiki\TradeWars_2002_v2_HVS_MBBS_Sysop_Documentation.html
   MBBS (HVS Major BBS) manual + sysop doc: the MBBS side of the differences (fixed settings, rob/steal, MCIC behaviour). Cross-check vs item 1's MBBS sections.
6. stardock_manuals_and_text_docs\Gypsy_Big_Dummies_Guide.html + Gypsy_Chapter1..13 + Iago_War_Manual.txt + Slice-10_Slice_War_Manual.txt
   Large player guides (mechanics detail on combat, ports, planets, ships, corps). Era/version of each not verified - check against 1-3 before trusting numbers.
7. stardock_manuals_and_text_docs\TWFAQ_*.txt, OldBBS_*.txt, Misc_*.txt (<- thestardock.com/files/manuals/TWLinksManuals/ and /files/Old BBS Files/TW Player Docs/)
   Small primary-ish notes: Ferrengi ship specs (FERRSPEC), ship odds, fig/shield price equation (Hekate: price=(160+40)+sin(day/87*2pi)*40), alignment->exp loss at extern (1/4 of least extreme alignment), megarob, evil functions, 2002SHIP.TXT, planet FAQs, JPhints (John Pritchett). Mixed versions - check date in each header.
8. stardock_modernmanual\*.md  <- https://www.thestardock.com/files/ModernManual/ (core/ships, planets, ports, trading; advanced/economy, planet-creation, twgs-settings; strategy/combat; reference/pod-mechanics)
   Stardock site 'ModernManual' (files are HTML-wrapped markdown, dated 2026-01-25, author 'System'): condensed ship table with all stock TWGS ships (TPW, odds, max figs/shields, holds, transwarp). Looks like a modern rewrite of older guides, so treat as secondary; compare with ship pages in classictw_docs_wiki and Bible chart.
9. classictw_docs_wiki\*.html  <- https://docs.classictw.com/index.php/... (Big_Bang, Creating_Games__Big_Bang_, TEDIT, Combat, Citadel, Alignment, ship pages incl. Ferrengi, TransWarp_Drive, Turns_Per_Warp, Busted, Ship_Destroyed ...)
   Official-ish docs wiki. Big Bang/TEDIT pages list every sysop setting (useful for the configuration surface of TWGS). Ship pages are thin (holds/TPW/figs/shields). Content (c) EIS / wiki.
10. github_selected_files\rdearman__twclone\  <- https://github.com/rdearman/twclone (C server + PostgreSQL + JSON protocol; release v1.0.0)
   Only complete open-source TW2002-style server with readable rules code (combat, citadel, ports, planets, banking, corps, Ferengi AI). Saved: README, LICENSE, docs (CANONICAL_COMPARISON, FEATURE_PARITY_ANALYSIS, PLANET_FIGHTER_PRODUCTION, GALACTIC_ECONOMY, SHIPTYPE_RESTRICTIONS, V2_GAMEPLAY_SYSTEMS_CONTRACTS), src/db/repo/repo_combat.c, repo_citadel.c, repo_port_rules.c.
   CAUTION: NOT an exact copy - it states ~85-90% 'parity', uses real-time 10-min production ticks, dynamic pricing, its own fighter production model. LICENCE CONFLICT: LICENSE file is GPL-2.0 (GitHub detects gpl-2.0) but README says new code is MIT. Do not copy code into a closed project without resolving that; use as a design cross-check only.
11. github_selected_files\mosleymr__TWX30\  <- https://github.com/mosleymr/TWX30 (+ mosleymr/mombot, TW2002/twxp, TW2002/mombot, mrdon/twist)
   TWX Proxy 3.0 (C#), Mombot, Zedbot: encode in-game prompts/text and ship/planet parsing. Saved: Source/MERCH_PORT_PRICE_FORMULAS.md (EMPIRICAL regression: organics ~ 24.2+0.734*|MCIC|+0.213*pct, equipment ~ 31.34+1.227*|MCIC|+0.554*pct; author states these are estimates, not the server formula), docs/haggle-modes.md, TW2002/twxp README+LICENSE+ships.cfg+planets.cfg (sample game config), TW2002/mombot planetneg/planet.ts (planet-trade negotiation logic) and ship stats scripts, mrdon/twist docs port-menu.md/port-port.md (port screen text).
   Licences: TW2002/twxp and TW2002/mombot = GPL-3.0 (twxp README says MIT, LICENSE file is GPLv3); mrdon/twist = Apache-2.0; mosleymr/TWX30 = no licence file detected (GitHub API shows none) - read only.
12. Not saved (for Ben to decide): other clones are not rule-faithful - ripred/tradewars-ansi-p2p (twansi, original design), mschandr/space_wars_3002 (Laravel remake, config/game_config.php), brianseitel/node-wars, leonard4/SectorWars (stub), pypi terminal-space.

### Not downloaded on purpose
- Any .zip/.exe/.msi: TW2002 v3.09 door zips, TWGS exes, TWXP msi installers (game binaries; TWSYSOP.DOC is inside those zips). Official source for these: https://eisonline.classictw.com (download page, requires accepting EIS licence).
- tw-cabal.navhaz.com mirror (timed out from here; the same pages were taken from thestardock.com 'Site Caps').
- guardiansworlds.com 'Trading formulas' thread (Cloudflare challenge), classictw.com forum threads (not static docs).
- Old TradeWars II source (TW2.PAS, tw40-source.7z) - different game, not TW2002.

### Known gaps still open
- Exact combat damage RNG / per-round formula: only the odds (1:1, 2:1, 3:1, 20:1 shields) and 1.25x offensive-wave rule are documented; no source for the random factor.
- Exact port price algorithm (haggle acceptance and MCIC curve): only empirical tables (cabal economy2.html, haggling.html) and regressions.
- Ferrengi/alien AI movement and attack odds beyond TEDIT settings; Gold aliens are a TWGS add-on.
- Planet production per colonist and exact daily growth: planets.html + Planet Handbook have the tables, but verify against the 3.11 revision notes.

### Saved file index
cabal_strategy_site\            18 html (Cabal's Secret Hideout, 2005)
eis_tw2002_v3_docs\             26 html (official v3 help)
classictw_museum_wiki\          6 html (revision histories, HVS/MBBS sysop doc, v1 notes, TWGS app page, Bible page)
classictw_docs_wiki\            43 html (docs.classictw.com wiki pages)
stardock_manuals_and_text_docs\ 42 files (Bible, Gypsy, Iago, Slice, Someguy, FAQs, Misc notes)
stardock_modernmanual\          18 md (HTML-wrapped)
github_selected_files\          26 files, per-repo subfolders
