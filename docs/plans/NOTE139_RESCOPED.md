# COMMANDER NOTE 139 (rescoped by NOTE 168)

Paste this to Cur. It replaces the earlier NOTE 139. The picture is `feature/grokbot-player` at `de930d09114a9e66d9871c0f6b0cb2ca7212c964` plus #93 (`track-i-note162` at `3aaf2b0ddf2e42d0e2b36ed18cb548fa00dd9659`). Branch from that #93 head once merge round 27 lands it. This file does not carry #93's code.

On that base the gap map is Match 69 + Match-behind-flag 81 = 150 of 171 (87.7%). A normal game matches 69 of 171 (40.4%). Still open: Partial 15, Different 4, Ben-decision 2. Missing is 0.

## Build

No row.

Every Partial or Different row on that base is named below. A track owns it, or it is a live measurement. Do not add a switch. Do not move a grade. Profile rows 230 through 239 stay unused.

## Leave these: Track G NOTE 167

These are the ruling rows. NOTE 167 owns them. 1.5 and 6.3 are Ben-decision, not Partial or Different, and they stay on that list too.

- **1.6** Terra colonists. Partial.
- **1.15** FedSpace fighter limit. Partial. #98 (NOTE 166) also has this, on the existing `FED_TOW_LIMIT_MODE` row 168.
- **2.5** Price scale vs ship cost. Different.
- **4.1** Genesis price. Partial.
- **5.14** Exp and alignment on death. Partial. #98 adds `SELF_DESTRUCT_ALIGN_MODE` row 204 for the button.
- **5.20** Combat in FedSpace. Partial. #98 keeps the existing `FEDSAFE_FIGHTER_CAP_MODE` row 167.
- **6.2** Class-table citadel costs. Partial.
- **9.8** Rob and steal caps. Partial. #98 regrades this to Match with no new switch.
- **10.1** Create a corporation. Partial. #98 regrades this to Match with no new switch.
- **11.11** Big Bang options. Partial.
- **12.3** Real-time movement. Different.
- **14.6** Ours-only systems. Different.
- **1.5** StarDock in sector 1. Ben-decision.
- **6.3** Class M population cap. Ben-decision.

## Leave these: live measurement

The number is not printed. Do not invent it.

- **2.15** Attack a port. Partial.
- **4.8** Armid price. Partial.
- **5.7** Ship versus ship. Different.
- **6.10** Planet killer. Partial.
- **12.4** Nightly Extern. Partial.

## Leave these: another track already has them

On the tip-plus-#93 map these two are still Partial. Track G owns them. They are not a second assignment.

- **8.1** Ferrengi odds. #96, NOTE 164, `FERRENGI_ODDS_MODE` row 200.
- **12.6** Times blown up. #96, NOTE 164, `TIMES_BLOWN_MODE` row 202.

#96 also adds `CORP_SHIP_DISBAND_MODE` row 201 on 6.11 and `FIGHTER_REPORT_MODE` row 203 on 13.4. Both rows are already Match-behind-flag on the tip. Do not grade either one again.

#89 owns NavPoints, `NAVPOINT_MODE` row 181. GAP 14.1 on the #93 head is Match-behind-flag through `CIM_MODE` row 186. Do not open a second computer-menu switch.

#93 owns the rows it already moved: 1.8 (`FEDERATION_HALL_MODE` row 182), 3.15, 3.20, 4.9, 4.10, 4.16, 5.6, 5.18, 6.12, 8.8, 10.2, 10.4, 10.6 (row 183), 10.7, 10.9, 11.7 (row 184), 11.9 (row 185), 13.1, 13.3, 14.1 (row 186), 14.5. The tip already has NOTE 163: 6.7, 6.11, 9.2, 9.5 (`BOUNTY_GOOD_MODE` row 187), 13.4.

## Gates

Hold these if a later edit adds a row under this note. They are the same gates as NOTE 162 and NOTE 163.

- New switches default to `legacy`. `V311_PROFILE=v311` turns the helper on. The string `1` does not. `TW2002_LIVE_PROFILE` does not.
- The first new profile row is 230. Rows 188 through 229 are not this note. 188 through 199 were the dropped NOTE 165 block. 200 through 204 are Track G.
- A new helper goes in `V311_PROFILE_HELPERS` and in `docs/plans/v311-profile-v1.md`. The heading stays `## The switch set (N helpers)` with N equal to that dict. On the #93 head, N is 138.
- Profile-off digests stay `24863a3d` (seed 250925) and `98a47c8a` (seed 4242), each 0/0 rejected and 0 exceptions.
- Bank pin `9b607d3dae940c0b1a69f6d7` holds.
- `/bot` stays unchanged: `web/bot.html`, `web/bot.js`, `web/bot-parity.js`.
- Each gap id is graded once. A second switch on a row that is already Match or Match-behind-flag does not move the count.

## Done when

Report that the build list was empty, no file under `src/` changed, and the helper count is the #93 count of 138.

## NOTE 169

Checked after the list above. No Partial row is still open outside it. 8.1 and 12.6 are the only Partial rows that are not a NOTE 167 ruling and not a live measurement, and #96 already has both. Profile rows 240 and up are not used. No engine change on NOTE 169.
