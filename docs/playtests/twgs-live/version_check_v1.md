# NOTE 130 version check

NOTE 129 measured TWGS v2.20b / TW2002 3.34b (game "TW Test Game 2", 19 Oct 2026). Those screens are not a v3.11 source. This note checks the five rows that differed from our copy against the v3.11 docs in `C:\Users\sugar\tw2002_reference`: S1, S2, S3, S4, S6, S7, and `GAP_MAP.md`. There is no file named S5 in that tree. The EIS v3 command menus are included because GAP_MAP cites them for these same screens. No engine change in this note.

A v3.11 source that does not print the number is `unknown`. A number that already matches the copy is `leave as is`. A v3.11 sentence that disagrees with the copy is `change engine under V311_PROFILE`.

| Row | v3.11 value | 3.34b value | Source | Verdict |
| --- | --- | --- | --- | --- |
| StarDock menus and prices | EIS StarDock menu: C CinePlex, G Bank, H Hardware, P Police, S Shipyards, T Tavern, `!` help, Q leave. S3's Levy TradMenu list is the same displayed set except L is "Return to your ship and leave", and the undisplayed keys are `+` Library console and U Underground. No singles bar, and L is not a library. Announcement is 100 credits (S3). Drink, food, shield, and fighter prices are not printed. | Displayed L is Libram Universitatus. Undisplayed B is the singles bar (balance 140 to 93, no price printed). Drink 80, food 24, shields 131, class 0 fighters 218. Announcement 100. | EIS `StarDockMenu.html`. S3 bible, "Using the StarDock to its fullest" and "The Lost Trader's Tavern" (announcement 100). GAP_MAP 1.8 and 11.8. Captures: `stardock-menus.txt`. | leave as is |
| 100-cr name change | The Underground lets you change your name. No price, and no "total unknown" rate. | "Seems you're a total unknown, this'll be cheap." "We can give you a new identity for 100 credits." Experience 1, alignment 0. Declined. | S3 bible, "The Underground". GAP_MAP 11.7 (name change not built). Capture: `name-change.txt`. | unknown |
| Cineplex 100 | CinePlex Videon Theatres. S3: a nominal amount of credits to watch an ANSI. No number. | "You'll LOVE \"Vulcan Thunder\" hehheh100 Credits Please". Declined. | EIS `StarDockMenu.html` (C). S3 bible, "The CinePlex Videon Theatres". | unknown |
| Opening fuel 11/27, organics 31/66, equipment 56 | Not printed. GAP_MAP 2.5 samples about 47 cr per equipment at a sell port and about 130 at a buy port, and marks that unverified. S2's worked example is a -65 MCIC port, not these opening quotes. The economy2 100% chart behind our copy is fuel 15/35, organics 28/71, equipment 49/128 per hold (MCIC +50 full sell, MCIC -50 empty buy, experience 0). | Fuel sell 11 / buy 27, organics sell 31 / buy 66, equipment sell 56. The 66 was at 94% of max, not 100%. The screen did not print MCIC. | GAP_MAP 2.5. S2 cabal formulas (MCIC -65 example). Capture: `price-scale.txt`. | leave as is |
| Computer B = Begin Self Destruct | Computer B is Begin Self-destruct Sequence. `<` is Return to Previous Sector, marked new for version 3. The unshifted comma backtrack was discontinued as of v3.05. | Computer B: "Begin Self Destruct", then "ARE YOU SURE CAPTAIN? (Y/N) [N]", then "Self Destruct Aborted...". `<` plotted the course back to the previous sector and asked to engage the autopilot. Declined. | EIS `CompMisc.html` (B). EIS `MainMenu.html` (`<`, and the v3.05 comma note). Capture: `computer-b.txt`. | change engine under V311_PROFILE |

## How the verdicts were read

StarDock. The 3.34b letters are not the v3.11 menu. L as a library and B as a singles bar are 3.34b. S3 puts the library on `+` and does not list a singles bar. Announcement 100 is already `TAVERN_ANNOUNCE_COST`. Drink 80 and food 24 are not in these docs (`TAVERN_DRINK_COST` and `TAVERN_FOOD_COST` stay 20). Shields 131 is not printed. Class 0 fighters 218 sits inside the copy's 160-239 day wave, and these docs do not print a different fighter price. None of that is a reason to retune the dock.

Name change. S3 and GAP_MAP 11.7 confirm the service and do not print 100 credits. `UG_NAME_CHANGE` stays false until a v3.11 source prints a price.

Cineplex. S3's "nominal amount" is not 100. `CINEPLEX_COST` stays 0.

Opening quotes. 11/27, 31/66, and 56 are one 3.34b port that was not at the chart's 100% and did not show its MCIC. GAP_MAP's equipment sample (about 47 sell, about 130 buy) is the same chart our anchors already use (49 and 128). Do not replace those anchors with the 3.34b screen.

Computer B. The copy's Computer list labels B "Backtrack", and the computer key handler calls `backtrack()`. v3.11 puts self-destruct on Computer B and puts the return to the previous sector on `<`, which this cockpit already does from the main prompt. A later change belongs under `V311_PROFILE`. This note does not make it.
