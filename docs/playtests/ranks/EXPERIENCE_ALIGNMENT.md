# Experience, alignment and rank

Rules table first, then what the engine does. Sources are the files under `docs/reference/tw2002/` (gap map rows 1.16, 3.11, 3.20, 5.14, 5.20, 6.12, 8.4, 9.2 to 9.9, 10.3 and conflicts 12, 14 and 16). The target is TWGS 3.11; MBBS breaks ties. Marks: CONFIRMED (a source prints it), SOURCE-CONFLICT (sources disagree, the reading is given), UNVERIFIED (no source prints it; the value here is chosen and says so).

Today's build (before this slice, kept as `RANK_MODE = "legacy"`): 9 ranks from experience alone (Civilian 0 to Fleet Admiral 250,000) and 9 alignment tier names (Terrorist to Saint). Experience: +1 per trade, +1 per warp, haggle bargain (cap 10), 200 per player kill, 20 x aggression per Ferrengi, 100 per Genesis planet, 75 per claimed planet, 50 x level per citadel, 25 per alliance. Alignment: Ferrengi kill +10, atomic warhead -50, planet destroy -50, FedSpace attack attempt -200, FedSpace photon -100. The Imperial StarShip needs 2,000 alignment. No combat at all in FedSpace. Other seats see nothing of your rank or alignment (corp-mates see your exact alignment).

## Rules table

| # | rule | original | mark and source | this slice (RANK_MODE tw2002) |
| --- | --- | --- | --- | --- |
| **Experience** | | | | |
| x1 | Trading | Experience comes from trading and from haggling. Gap row 9.2 lists trade; the economy slice keeps +1 per successful trade. A good counter earns more (HAGGLE.md). | CONFIRMED for trade in shape: gap row 9.2, Bible ("you can gain experience as well as gain credits"), `HAGGLE.md` ("ordinary 1 point for any successful trade"). CONFIRMED for haggling: `S7_softdocs_slice-10.txt`. | Built: +1 per successful trade, plus the haggle gap capped by `K.PORT_HAGGLE_XP_CAP` = 10. |
| x2 | First dock at an unused port | +1 experience. | CONFIRMED: Bible ("For finding this unused port you receive 1 experience point(s)"), gap row 9.2. | Built: the first trade anyone makes at a port gives +1. |
| x3 | Midnight login | The first login after midnight gives +1 experience and +1 alignment. | CONFIRMED: `cabal_strategy_site/formulas.html` table ("Login in first time each day +1 / +1"), `cabal_strategy_site/glossary.html` and `classictw_docs_wiki/Glossary.html` ("log in after Midnight gain one point of Experience and one point of Alignment"). | Built: the day tick gives every living player +1 / +1. |
| x4 | Moving | No experience for a warp. | UNVERIFIED (absent from every list). | Built: no experience for a warp. |
| x5 | Scans and probes | No experience. | Lined up with `docs/playtests/scanners/SCANNERS_HIDDEN_INFO.md` s19. | Unchanged (already 0 under INFO_MODE tw2002). Also 0 here under INFO_MODE legacy. |
| x6 | Creating a planet | +25 experience. Alignment +10 if good, 0 if neutral, -10 if evil. | CONFIRMED: `formulas.html` table (Good +10 / +25, Neutral 0 / +25, Evil -10 / +25), `classictw_docs_wiki/Alignment.html` ("Creating a planet gives you 10 alignment and 25 experience"). | Built for `deploy_genesis`. |
| x7 | Destroying a planet | +50 experience, -1 alignment, any alignment. | SOURCE-CONFLICT 14 (today's build -50). The sources agree: `formulas.html` ("Destroying a Planet (Any Alignment) -1 / +50") and both glossaries ("Each cycle of creation and destruction will get you 75 exp" = 25 + 50). | Built: -1 alignment, +50 experience when the planet is removed. Legacy keeps -50. |
| x8 | Capturing a planet | Not in any list. | UNVERIFIED. | 0 (legacy 75). |
| x9 | Citadel levels | Not in any list. | UNVERIFIED. | 0 (legacy 50 x level). |
| x10 | Alliances | Not in any list. | UNVERIFIED. | 0 (legacy 25). |
| x11 | Destroying a port | +50 experience, -50 alignment. | CONFIRMED: `classictw_docs_wiki/Alignment.html`, `formulas.html` table. | Built: +50 experience when an atomic detonation destroys a port. The atomic warhead's own -50 alignment each (a verb of this game) stays, so a destroyed port already costs at least -150. |
| x12 | Experience from ship combat | Your fighters lost / 15 against the other colour, / 35 against your own colour, / 25 when either side is neutral (0). | CONFIRMED: `formulas.html` "GOLD or MBBS Player vs Player" (one formula for both). | Built for every attack on a trader, under COMBAT_MODE tw2002 and legacy. |
| x13 | Experience from a kill | Pod or Ship Destroyed: the killer gains 10 percent of the victim's experience. | CONFIRMED: `formulas.html` ("If you pod them: Gain 10% of their experience", worked example 12,000 -> +1,200), `cabal_strategy_site/pods.html`. | Built, from the victim's experience before the loss. Replaces the flat 200. |
| x14 | Experience from sector fighters | Gold/Classic: your fighters lost / 15 against the other colour, / 35 same colour. | SOURCE-CONFLICT 16: MBBS prints no fighter formula, Gold/Classic does (`formulas.html` "GOLD or Classic Player vs Figs"). TWGS is the target, so Gold. The neutral divisor is not printed: / 25 (UNVERIFIED, from x12). | Built for attacks on owned sector fighters. |
| x15 | Aliens and Ferrengi | Bible: an alien of the other alignment gives half its experience, the same alignment a quarter; alignment moves with theirs. Feds pay a bounty. | CONFIRMED in shape: Bible ("you will get one half of their experience"), gap row 8.4. | Not changed: Ferrengi here carry no experience or alignment, so the kill keeps +10 alignment, 20 x aggression experience and the bounty. Row 8.4 belongs to the Ferrengi work. |
| **Alignment** | | | | |
| a1 | Ship combat against a trader | Alignment moves by (your fighters lost / 1000) x (enemy alignment x 0.2): hitting a red raises yours, hitting a blue lowers it. | CONFIRMED: `formulas.html` "GOLD or MBBS Player vs Player" and its example (10,000 fighters lost against -100,000 gives +200,000). | Built: change = -(fighters lost x enemy alignment) / 5000, rounded toward zero. |
| a2 | A kill | Pod or Ship Destroyed: the killer gains 50 percent of the victim's alignment with the sign that suits it (podding a -100,000 red gave the blue +50,000). | CONFIRMED: `formulas.html`. | Built: killer alignment -= victim alignment / 2 (victim's alignment before the loss). |
| a3 | Sector fighters | Gold/Classic: (owner alignment / 5000) x fighters lost against the other colour, / 10000 same colour. Corp fighters use the corp alignment. | SOURCE-CONFLICT 16 (see x14). | Built with the owner's personal alignment. This game has no corp alignment. |
| a4 | Robbing and stealing ports | Red-only verbs; a bust costs experience. | CONFIRMED: `formulas.html`, `classictw_docs_wiki/Glossary.html` ("Busted"). | Not built (no rob or steal verb). |
| a5 | Feds and FedSpace | Attacking a Fed: -10 alignment and you are podded. Attacking a fedsafe trader in FedSpace calls Captain Zyrain. | CONFIRMED: `formulas.html` ("Attacking a Fed -10, but you get podded"), Bible (Captain Zyrain). | No Fed ships here. Today's refusal and penalty (-200 attack, -100 photon) stay, now only against a fedsafe target (u1). |
| a6 | Rewards, bounties, taxes, colonists, corps, tavern | Reward on a red +1 per 1,000 credits; bounty on a blue -1 per 250; taxes and port upgrades raise it; jettisoned colonists -1 each (good only, once a day); breaking into a corp -1; swearing at the Grimy Trader -1 / -1 exp. | CONFIRMED: `formulas.html` table, `Gypsy_Big_Dummies_Guide.html`, `classictw_docs_wiki/Alignment.html`, `stardock_modernmanual/alignment/good-path.md`. The reward price is SOURCE-CONFLICT (1,000 in Gypsy and cabal, "nnn" in the wiki). | Not built (no such verbs). |
| a7 | Atomic warheads | This game's verb. | No source. | Unchanged: -50 each. |
| **Ranks** | | | | |
| r1 | Good ladder | 22 titles, doubling: Private 2, Private 1st Class 4, Lance Corporal 8, Corporal 16, Sergeant 32, Staff Sergeant 64, Gunnery Sergeant 128, 1st Sergeant 256, Sergeant Major 512, Warrant Officer 1,024, Chief Warrant Officer 2,048, Ensign 4,096, Lieutenant J.G. 8,192, Lieutenant 16,384, Lieutenant Commander 32,768, Commander 65,536, Captain 131,072, Commodore 262,144, Rear Admiral 524,288, Vice Admiral 1,048,576, Admiral 2,097,152, Fleet Admiral 4,194,304. | CONFIRMED: `Gypsy_Big_Dummies_Guide.html`, `stardock_modernmanual/alignment/good-path.md` (same numbers). | Built: `K.GOOD_RANKS`. |
| r2 | Evil ladder | 22 titles, same thresholds: Nuisance 3rd, 2nd, 1st Class, Menace 3rd, 2nd, 1st Class, Smuggler 3rd, 2nd, 1st Class, Smuggler Savant, Robber, Terrorist, Pirate, Infamous Pirate, Notorious Pirate, Dread Pirate, Galactic Scourge, Enemy of the State, Enemy of the People, Enemy of Humankind, Heinous Overlord, Prime Evil. | CONFIRMED: `Gypsy_Big_Dummies_Guide.html` (the one source that prints it; EIS `CompDisplays.html` confirms the two lists exist). | Built: `K.EVIL_RANKS`. |
| r3 | Below 2 experience | No title printed. | UNVERIFIED. | "Civilian" on both sides (today's rank-0 name), level 0. |
| r4 | Which ladder | Zero or more alignment is blue (good ladder), negative is red (evil ladder). | CONFIRMED: both glossaries ("zero or more alignment (i.e. a blue)"), Gypsy (E and G lists by sign), `classictw_docs_wiki/Alignment.html`. | Built. |
| r5 | Your own numbers | You see your experience, your alignment and your title. | CONFIRMED: Gypsy <I> Ship Information ("Rank and Exp"). | Own observation: `experience` and `alignment` exact, `rank` title. Commission and fedsafe follow from those two numbers (u1, u2); the original prints neither as a flag, so no new field. No tier names such as "Saint" exist in the original (UNVERIFIED: none printed), so `alignment_label` becomes Good, Neutral (0) or Evil. |
| r6 | What others see | The sector display names a trader with the title ("Chief Warrant Officer Fooman"). List Trader Rank shows every trader by experience with the title or the experience value, the corporation and the ship type. The colour shows good or evil. No source shows another trader's alignment number. | CONFIRMED: `stardock_manuals_and_text_docs/Misc_shipodds.txt`, Gypsy <L>, EIS `CompDisplays.html` ("Titles of the players or their Values in Experience points"). | Built: `rivals` carry `rank`, `side` and `experience` (the List Trader Rank). A trader in your sector carries `rank` in `other_players`. Alignment numbers stay hidden from non-corp seats (corp-mates already see them, unchanged). |
| r7 | Rank and combat | No source gives experience a combat effect. Experience sets haggle skill and rob limits. | UNVERIFIED (no combat effect printed); CONFIRMED for haggling (gap row 9.8). | No combat effect. Prices already read experience; unchanged. |
| **Unlocks and blocks** | | | | |
| u1 | Fedsafe | Zero or more alignment and 999 experience or less: other players may not attack you in FedSpace. Reds are never fedsafe. | CONFIRMED: both glossaries ("Fedsafe"), Bible ("protected in FedSpace until you have 1000 experience points"; Captain Zyrain for "positive alignment and Experience Point value of under 1000"), Gypsy ("0-999 experience ... stay overnight in fedspace"). | Built: an attack or photon in FedSpace is refused (with today's penalty) only when the target is fedsafe; anyone else may be fought there. Deploying fighters, mines or Genesis in FedSpace stays forbidden. |
| u2 | Federal Commission | 1,000+ alignment is commissioned automatically; 500+ may apply at the Police HQ and is raised to 1,000. Lost below 1,000. | SOURCE-CONFLICT 12 with today's build (2,000). Sources agree: `classictw_docs_wiki/Imperial_StarShip.html`, Gypsy, both glossaries. | Built: automatic at 1,000 (`is_commissioned`). Applying at 500 is not built (no Police HQ verb). |
| u3 | Imperial StarShip | Needs a commission. "A limited number of Starships available." Falling below 0 alignment in one gets it repossessed. | CONFIRMED: `Imperial_StarShip.html`, Gypsy FedPolice menu, gap row 3.20. | Built: buying needs 1,000 alignment (legacy 2,000). One per game stays. Repossession not built. Found on the way: today's build bars an evil trader from every hull (a hull without `min_alignment` reads it as 0). Fixed in tw2002; legacy keeps it. |
| u4 | TransWarp into FedSpace | Commissioned traders may transwarp straight into FedSpace. | CONFIRMED: `Imperial_StarShip.html` ("lose this ability any time they fall below 1,000"), Gypsy. | Not built: this game has no ship TransWarp drive (only `planet_transwarp`, which stays barred from FedSpace). |
| u5 | StarDock, Police Station, Underground | Alignment decides whether you may safely enter the Police Station (not negative) or the Underground (red). StarDock itself is open. | CONFIRMED in shape: `classictw_docs_wiki/Alignment.html`; thresholds UNVERIFIED. | Nothing to gate: no Police or Underground verbs. |
| u6 | Same-side corporations | Joiners must match the CEO's side. | CONFIRMED: gap row 10.3. | Not built (corporation work). |
| **Death losses (built by the pods slice)** | | | | |
| d1 | Podded | -10 percent experience, no alignment. | `docs/playtests/combat/DEATH_ESCAPE_PODS.md` d8. | Not duplicated: the pods code is the one place. The killer's share (x13, a2) is new here and reads the victim's numbers before the loss. |
| d2 | Ship Destroyed | -50 percent experience and -50 percent alignment. | DEATH_ESCAPE_PODS.md d9. "Toward zero": `formulas.html` says "loose ... 50% of your alignment", which for a blue can only mean toward zero. For a red no line covers Ship Destroyed; the nearest, `classictw_docs_wiki/Alignment.html` self-destruct ("their negative alignment will be halved"), also reads toward zero. So: CONFIRMED for blues, UNVERIFIED (by that analogy) for reds. | Not duplicated. The pods code halves toward zero; this table agrees. |
| d3 | Self-destruct | Wiki: a blue goes to -10 alignment and 0 experience; a red to 0 experience and half its negative alignment. MBBS manuals: 50 percent of experience. | SOURCE-CONFLICT (DEATH_ESCAPE_PODS.md d13). | Not built (no verb). |
| d4 | Mixed corps at Extern | Each member loses min(abs(lowest red), highest blue) / 4 experience. | UNVERIFIED (gap row 9.9; `formulas.html`, `Misc_Alignment_to_exp_changes_twgs.txt`). | Not built. |

### Deliberate differences

- Ferrengi kills keep today's reward (x15): the engine's Ferrengi have no experience or alignment to take a share of.
- No Fed ships: the FedSpace refusal plus -200 / -100 stands in for Captain Zyrain (a5, u1).
- Commission by application at 500 and ISS repossession are not built (u2, u3).
- Atomic warheads keep -50 each (a7).
- Sector-fighter alignment uses the owner's personal alignment; there is no corp alignment (a3).
- Results of the formulas are whole numbers, rounded toward zero.

## What the engine does (RANK_MODE tw2002)

- `K.RANK_MODE` defaults to `tw2002`. `legacy` is today's ladders, awards and ISS floor, unchanged: `test_legacy_is_unchanged` compares observation and prompt digests recorded on 29257a1.
- Experience: +1 per trade, no warp; first trade at an unused port +1; day tick +1 experience and +1 alignment; Genesis +25 (+10 / 0 / -10 alignment by side); planet remove +50 / -1; atomic port remove +50; combat awards as x12/x13/x14; Ferrengi kill as today. Death losses stay in the pods code.
- Alignment from combat as a1/a2/a3. Atomic warheads keep -50 each.
- Ranks: 22 good and 22 evil titles. Own observation carries `experience`, `alignment`, `rank` (title) and `alignment_label` (Good / Neutral / Evil). `rivals` carry `rank`, `side`, `experience`. A same-sector trader carries `rank` in `other_players`. Alignment numbers stay off non-corp seats.
- FedSpace: only a fedsafe trader is shielded. ISS needs 1,000 alignment. An evil trader may buy ordinary hulls (legacy still bars them).

## Delivered

- Rules table, RANK_MODE switch, planted bugs, seats legal, and the scripted match before and after. See the commit message and the parent report.

## Seat brains

Rejected stays 0 under both modes. Day-10 net worth under RANK_MODE tw2002 (seed matrix, no warp experience) sits below the RANK_MODE legacy band the acceptance tests measure, mainly because warps no longer farm experience and combat / fedsafe change the path. The N2 / N3 / economy bars therefore pin `RANK_MODE = "legacy"`, matching the scanners INFO_MODE pin. Measured under both modes (seed, legacy nw, tw2002 nw, rejected):

| brain | seed | legacy | tw2002 | rejected |
| --- | ---: | ---: | ---: | ---: |
| N1 | 250925 | 473,887 | 388,835 | 0 / 0 |
| N1 | 20260925 | 301,012 | 369,902 | 0 / 0 |
| N1 | 230923 | 273,637 | 398,699 | 0 / 0 |
| N1 | 99 | 331,693 | 298,710 | 0 / 0 |
| N1 | 31 | 483,147 | 380,196 | 0 / 0 |
| N2 | 250925 | 653,191 | 395,920 | 0 / 0 |
| N2 | 20260925 | 844,548 | 334,067 | 0 / 0 |
| N2 | 230923 | 934,930 | 398,831 | 0 / 0 |
| N2 | 99 | 785,986 | 564,280 | 0 / 0 |
| N2 | 31 | 480,717 | 366,415 | 0 / 0 |
| N3 | 250925 | 923,538 | 679,387 | 0 / 0 |
| N3 | 20260925 | 940,383 | 714,167 | 0 / 0 |
| N3 | 230923 | 992,565 | 741,611 | 0 / 0 |
| N3 | 99 | 921,876 | 602,442 | 0 / 0 |
| N3 | 31 | 979,102 | 722,434 | 0 / 0 |

## QC (experience alignment QC fixes)

| bug | where | test |
| --- | --- | --- |
| RANK_MODE legacy: observation ship hints listed hulls an evil trader cannot buy (ship_min_alignment(spec, -1e9) vs legality default 0); blocked_by said 
eeds None | observation.py affordable/next-up hints; legality.py blocked_by | 	est_legacy_evil_ship_hints_match_empty_buy_ship_list |
| LEGACY_GOLDEN digests refreshed for the hint fix (B evil seat) | 	ests/test_experience_alignment_v1.py | 	est_legacy_is_unchanged |
