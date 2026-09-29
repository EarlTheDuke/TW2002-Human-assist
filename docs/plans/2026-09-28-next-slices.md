# Next slices — ranked (2026-09-29)

Planning only. No product code from this list until Commander queues a slice. No paid API, no `:8031` / `:8032`. `cockpit-polish-v1` (`8675460`) already shipped the instrument bar, the side screen, port tint, the alert lamp, the route line, webp-with-png fallback, and Moments in the MFD.

## What was played

One short session on a test host (port 8033, seed 250925, heuristic P1, external P2, throwaway token). Default `/bot` in Chromium at 1440×900 and 1920×1080, the same page in Firefox at 1440×900, then `mode=cu` at 1280×800.

| Check | What happened |
|---|---|
| Chromium 1440×900 | Moments sat on a second tab row (y=402; the other four tabs were y=360). Ship, commander, and stage were clipped inside a 130 px text box (`merchant_cruiser`, `Commander (P2)`, `S1 Opening Trades`). Credits, sector, and day were whole. The scoreboard's own row overflowed. The map started under the video (video bottom 773, map top 787) and the map card was 931 px tall, so almost all of it was below the 900 px window. SCAN was ok. PROBE was disabled with a reason. Page itself was not wider than the window. |
| Chromium 1920×1080 | All five tabs were on one row. Ship, commander, and stage were still clipped in that same 130 px box. The scoreboard row still overflowed. The map still started under the video, near the bottom of the window. |
| Firefox 1440×900 | Moments wrapped the same way. The ship text was `merchant_cruiser`. |
| `mode=cu` 1280×800 | `scrollHeight` 800. |
| Moments | No rows. This host does not generate a custom clip, so Play was not on screen. The player code for Play only shows the still. |

Read for this pass: `docs/plans/2026-09-29-cockpit-design.md` (ideas 3, 4, 13, 14 were left for later) and the polish-v1 delivered note. The older Commander items (CLS about 0.73, stills to webp, Moments out of the debug column, Moments rows playable) shipped in polish-v1. Do not rebuild them. Play still shows a poster, which is the nit below, not a missing drawer.

## Already done

| Idea | Where |
|---|---|
| Page-load shift under 0.1 | polish-v1. Before was about 0.73. |
| Stills PNG to webp, png fallback | polish-v1. Manifest still names the pngs. |
| Moments out of the debug column | polish-v1, MFD Moments tab. |
| Moments rows have Play | polish-v1. Play shows the still. Replaying a real clip is nit 3. |

## Ranked backlog

Each row is one slice. Fog-safety means the screen may use only that seat's Observation and `/events`.

| # | Slice | Payoff | Size | Risk | Test idea | Fog |
|---|---|---|---|---|---|---|
| 1 | Five tabs on one row at 1440 | Moments is findable without a second line | S | A tighter tab can miss the 36 px hit size | At 1440×900, Chromium and Firefox, the five tab buttons share one y. MFD body height stays 420 | No new data |
| 2 | Ship name whole | The bar says `merchant_cruiser`, not `merchant_cr...` | S | Growing the cell can push the bar and revive CLS | At 1440 and 1920, `#sbShip` is not clipped. Credits, turns, day, sector, and alignment stay whole. CLS stays under 0.1 | Own ship class only |
| 3 | Moments Play uses the clip | A recorder row plays the picture that was recorded | S | A missing file must still land on the poster | A caption that has a clip starts the viewport video. A caption with only a still shows the poster. Reduced motion stays on the poster | Own moments only |
| 4 | Route line does not invent a point | A hop you cannot place is not drawn in the wrong spot | S | The current test expects a line for a neighbor with no map point | A path hop with no known coordinate and no existing stub is skipped. A path whose ends both have coordinates still draws `route-line` | `known_warps` and known-sector coordinates only |
| 5 | Local brackets | Who is already in this sector, one line under the video | S | Low | An occupant and a planet from this sector's observation render under the video. An empty sector renders nothing | Observation lists only. No extra occupants |
| 6 | Map top on the first screen | At 1440×900 the map starts at y=787, so the picture you just enlarged is below the fold | M | Fights "both big" if the video is simply shrunk away | At 1440×900 the map card's top is inside the window, the map stays under the video, and the video stays 16:9 | No new data |
| 7 | Warp ring on the window | The next hop sits on the glass, keys 1–9 unchanged | M | A second set of warp buttons can double-fire | The ring order matches `#warps button`. Key 1 still clicks the first warp. `mode=cu` has no ring | Sector ids already shown. Port tint stays remembered-only |
| 8 | Hull schematic | Holds, shields, fighters, and genesis as filled bars | M | A picture can disagree with the numbers | The bars match the ship card counts. The ship card stays | Own ship only |
| 9 | Computer page | A dense TradeWars readout behind a toggle | M | A second page can break `mode=cu` | Toggle shows sector, port, warps, holds, and turns from the same payload. `mode=cu` scrollHeight stays 800 | Same observation. No `/state` |

Commander has already grouped rows 1–4 as `cockpit-polish-v2`. Build that as one slice. Rows 5–9 wait.

## Top of the list, specced

### 1. Five tabs on one row

**Payoff.** At 1440×900 the Moments tab wraps under Ship. Firefox did the same. The column is about 315 px and the five labels need about 366 px, so the wrap is the width, not the font.

**Change.** Layout only. All five tabs share one row at 1440×900 and at 1920×1080. Keep a readable hit target. Do not change the 420 px MFD body, and do not move the map.

**Accept.**
- Playwright, Chromium and Firefox, 1440×900: the five `[role=tab]` boxes share one y, and each is at least 32 px tall.
- Switching tabs does not change `.mfd-body` height.
- `mode=cu` scrollHeight stays 800. Digits and S are unchanged.

**Fog.** Display only.

### 2. Ship name whole

**Payoff.** The ship readout is the class string, and `merchant_cruiser` is clipped at both 1440 and 1920. The text box measured 130 px. Commander and stage clip for the same reason. Credits, day, and sector were already whole.

**Change.** The ship value is fully visible. The fixed scoreboard height stays, so CLS stays under 0.1. Later readouts (rank, spool, lives) may stay on the horizontal scroll of the bar. Commander and stage should show more if that does not clip the ship or the first six instruments.

**Accept.**
- At 1440×900 and 1920×1080, `#sbShip` text is `merchant_cruiser` and `scrollWidth <= clientWidth`.
- Credits, turns, day, sector, and alignment are not clipped.
- The polish CLS check still asserts `window.__cls < 0.1`.

**Fog.** Own ship class. No new field.

### 3. Moments Play uses the clip

**Payoff.** Play calls `showFallback` with the still for that caption. A row that has a real clip never plays it. Reduced motion already stays on the poster, and that should remain.

**Change.** If the caption has a clip in the manifest, Play runs that clip in the viewport, same as a live moment. If the only asset is a still, or the file fails, show the poster. Reduced motion does not start video.

**Accept.**
- A moment whose caption maps to a clip with a video source ends with a viewport video pointed at that clip.
- A caption with only a still shows the poster and no video.
- `prefers-reduced-motion` shows the poster even when a clip exists.

**Fog.** The row is this seat's own moment. No other seat's media.

### 4. Route line does not invent a point

**Payoff.** When a path id has no known-sector coordinate and no existing stub, the map places a point near the previous node (`prev.x + 8`, `prev.y + 6`) and draws through it. That is a guessed sector, not a remembered one.

**Change.** Skip that hop. Draw `route-line` only through points that already exist (known coordinates or the stub the map already uses for an unvisited warp). Do not add a new coordinate. A one-hop exit with no point draws no line.

**Accept.**
- A plotted neighbor that is absent from `known_sectors` and has no stub does not produce `[data-testid=route-line]`.
- A path whose sectors all have coordinates still draws one polyline through those points.
- No new harness call. The fog test that another seat's port does not tint this seat stays green.

**Fog.** `known_warps` plus this sector's `warps_out`, and coordinates already on `known_sectors`. Nothing from the live adjacent port.

## After the nits

Local brackets are the smallest new cockpit idea: one line under the video for occupants and planets the observation already lists. The warp ring, the hull schematic, and the computer page are the three leftovers from the design doc; each is a medium slice and each must leave `mode=cu` and the current keys alone. The map-below-the-fold note is real (map top at y=787 inside a 900 px window) and it is also the riskiest, because polish-v1 was just accepted with the map large and under the video. Do not shrink that map until Commander asks.

## Needs Ben

- A paid video or image call, or a new live clip.
- A match on `:8031` or the pilot host on `:8032`.
- API keys.

## Not in this list

Do not redo the instrument bar, port tint, alert lamp, Bridge badge, webp fallback, or the Moments move. Those are in `8675460`. The 20-per-minute Bridge cap and "pending includes taken" stay as they are.
