# FX state machine — ship stage (P0)

Parent: [cockpit-ship-stage-p0.md](cockpit-ship-stage-p0.md).

The stills inventory is [stills/README.md](stills/README.md) (#344).

Six states. Triggers are actions and events that already exist. `EVENT_FACTS` in `src/tw2k/engine/observation.py` is the whitelist the cockpit is allowed to read. This sheet does not add keys. Where a later phase has to notice an event the cockpit ignores today, that is called out as cockpit wiring, not an engine change.

The left `#viewport` (`#vpStars`, `#sceneStill`, `#warpClip`, and the stills and videos `paintScene` / `TW2KMedia` put there) loses the job of showing motion. `#sectorText` is the sector report. It moves onto a text surface in P2 and is not an FX layer.

Precedence when two states want the same moment: combat, then warp, then mine-deploy, then planet-land, then port, then idle. A warp that also detonates mines plays the warp and then a short combat flash. States do not stack. Skip dismisses the current transient the way `#warpSkip` already dismisses a clip. Nothing here blocks the turn. `prefers-reduced-motion`, viewport mode `stills`, and `?mode=cu` hold the end frame and do not loop. Mode `off` shows the hull with no transient.

P2 maps the existing Live / Stills / Off control onto the stage: Live animates, Stills holds the canonical pose, Off skips transients. The control can leave `#viewport` with the node.

## Idle

Trigger. The resting state after a refresh, and after any transient ends. `paintShipView` already repaints from the observation.

On the model. Slow yaw and the fighter orbit, the shield bubble from `shields / shield_cap`, a short engine cone, the starfield already drawn inside `#shipSvg`. Empty shields leave the class accent in place (bible). The canonical three-quarter pose is yaw `0.82`, pitch `0.5`, which `shipPose` already uses when motion is held.

Retires from the viewport. `#vpStars`, and the deep-space stills `paintScene` picks when nothing else matches: `sector_deep`, plus `sector_fedspace`, `sector_nebula`, and `sector_hazard` as window dressing.

MVP. Drift, orbit, shields, engines, stars on the stage.

Later. A fedspace tint from `sector.is_fedspace`. A navhaz shimmer from `sector.nav_hazard_pct`. A cloak dim while `cloaks > 0`. None of these are required to remove the viewport.

## Warp

Trigger, already live. `playWarpClips` runs when `isRealMove` is true: event `warp` for this seat with `facts.from !== facts.to`, or event `autopilot` with `facts.executed` and `facts.hops_done >= 1`. The clip row comes from `web/media/warp-clips.json` for `ship.class` (10 SVG variants on each of the 17 hulls). Camera, stars, and exit are the existing set: cameras `side`, `chase`, `headon`, `top`, `gate`; stars `streaks`, `tunnel`, `nebula`, `sparse`, `gate`; exits `jump`, `fade`, `flash`, `fold`, `gate`. Duration is the row's `duration_ms`, otherwise the manifest's 2000. Linger is `WARP_LINGER_MS` (4000) so the other cockpit can still pause the clip.

Trigger, P2 cockpit wiring, not an engine change. `ship_transwarp` (`facts.from`, `facts.to`, `hops`, `ore`) and `planet_transwarp` (`facts.from_sector`, `facts.to_sector`) are real moves. `isRealMove` does not include them today. `retreat` carries `facts.from` and `facts.to` and can use a short warp. `warp_blocked` stays a refusal on the result line, with no flight.

On the model. The same `buildHullFaces` body, on the stage instead of inside `#viewport`. Plume length may follow the clip's `plume`. TransWarp magenta stays a property of the fitted drive, not of the clip. Fighters keep their outside orbit, scaled down or parked for the length of the clip so 500 markers are not fighting the camera. The end frame is the idle pose in the new sector.

Retires. `#warpClip` as a viewport child, the `move_warp` still, and the viewport's warp videos. The JSON, the bag shuffle, and the CSS camera grammar stay. They move with the stage.

MVP. Play the current procedural clip on the stage, Skip included, still-frame when motion is reduced.

Later. A bay-to-streak opening when the previous sector had a port. A longer plume when `hops` on a transwarp is high. File clips, if a row's `kind` is `file`, stay optional. The SVG hull remains the thing a pause can see, which `showWarpClip` already keeps under the video.

## Port land or takeoff

There is no dock event. A port is `sector.port` on the observation after a move. `paintScene` already treats a port whose name matches `/stardock/i`, or sector id 1, as StarDock, and any other port as `sector_port_` plus `class_id`.

Trigger, arrive. A real move (the warp triggers above) whose new observation has `sector.port`.

Trigger, leave. The next real move away from that sector. The warp state owns the flight. The port state is the held bay picture before that flight starts.

`trade` is not a flight. Opening the trade form can light the bay in a later pass. It does not change state by itself.

On the model. Nose slightly up, engines at idle, a plain gantry of two uprights behind the ship. The gantry is original geometry, not a traced station. Backdrop colour from the port. `PortClass` stores StarDock as 8. `stardock_class_label()` shows 9 while `port_class_live()` is on. The stage follows `paintScene`, which keys StarDock off the port name or sector id 1, not off that digit. Trade letters stay on the sector report. The stage does not paint BBS versus SSB.

| Where | Backdrop |
| --- | --- |
| StarDock, by name or sector 1 | Cool white bay, `#d7e4f5`, with a darker pit `#1c2430`. |
| Class 0, Federation | Blue-grey bay, `#24344a` on `#121820`. |
| Classes 1–7 and class 9 (built SSS) | One work bay, `#3a3428` with warm lamps `#e0b15a`. |

Takeoff is the warp state. MVP can cut. Later can fade the gantry out as the streaks start.

Retires. `sector_port_*`, `sector_stardock`, `docked_port`, and the `dock_port_*` videos in the viewport.

MVP. Backdrop plus the idle hull when `sector.port` is set. No new mesh beyond the two uprights.

Later. Per-class bay dressing. A buy-ship beat at StarDock when `buy_ship` lands. The orbiting spare from a refused trade-in is text today ("The new ship is in orbit") and stays text until a later note.

## Planet land

Trigger, down. Event `land_planet` for this seat. Facts: `planet_id`, `class`, `seized`. The cockpit already treats a landing as successful when the summary matches landed and does not match repelled (`surface = true` in the action handler). A fight that fails emits `combat` with `vs` `planet` and `exchange_kind` `planet_siege`, and does not set `planet_landed`. An empty bay turned away by shields is a refused action with no combat event. Either way the stage stays in space, with no surface.

`seized: true` still lands. If a `combat` with `vs === "planet"` or `exchange_kind === "planet_siege"` shares the turn, play the combat flash first, then the surface.

Trigger, up. Event `liftoff` (`facts.planet_id`). `surface` clears. Short climb, then idle. Liftoff does not also warp.

Class comes from `facts.class` on the event, and from the landed planet on the observation after that. Names are `PLANET_CLASS_NAMES`.

Backdrop is a procedural disc behind the hull. The ship rests in front of it, gear-down pose (nose up a few degrees, engines dark). No ground mesh is required for MVP.

| Class | Name | Backdrop |
| --- | --- | --- |
| M | Earth | Blue limb `#0c3a6e`, green `#1a6b3a`, white cloud band. Terra, when the report is the class M colonist source, uses this disc with no claim chrome. |
| K | Desert | Amber `#c47a2a` over rust `#6a3a14`. |
| H | Volcanic | Basalt `#2a1210` with lava cracks `#ff4a1a`. |
| O | Oceanic | Teal water `#0a6e78`, bright rim `#b8fff2`, no continents. |
| L | Mountainous | Grey-violet rock `#6e7380`, snow `#e8eef5`. |
| C | Glacial | Ice `#d7f4ff` over cold blue `#7eb8d4`. |
| U | Gaseous | Banded disc, amber `#c9a24a` and mauve `#6a3a78`. The ship dips into cloud. There is no ground line. |

`web/media/manifest.json` has stills for M, K, L, O, and U only. H and C have no still. MVP does not wait on bitmaps. A missing or unknown class uses the idle starfield.

Retires. `planet_own`, `planet_foreign`, `planet_land`, `planet_liftoff`, `planet_surface`, and the class stills as the thing the viewport shows. The generated stills may later sit, blurred, behind the disc. They are not the MVP.

MVP. Disc colour, gear-down pose, liftoff returns to idle.

Later. Citadel geometry when `citadel_level > 0`. A genesis flash on `genesis_deployed` (`facts.class`, `facts.name`) before the first land. Cabin ports lighting on the Colonial while colonists move. Those events already exist. They are elaboration.

## Mine deploy

Trigger. Event `deploy_mines` for this seat. Facts: `qty`, `kind`. Kind is `armid` or `limpet` for a mine that stays in the sector. An atomic deploy detonates immediately and emits `atomic_detonation` (`qty`, `port_destroyed`) instead of a sitting mine. Atomic is a combat flash, not this state.

On the model. A handful of mines drop aft of the ship and fall behind the fighter ring, then idle returns. Draw `min(qty, 6)` meshes and one numeral for `qty`. Armid is a small spiked ball. Limpet is a flat disc. Both are original and sit clear of the hull. Colour is a dim hazard amber, distinct from the red fighter dart.

Retires. The `combat_mine` still in the viewport.

MVP. The drop, the numeral, then idle.

Later. A persistent hint in idle while this sector's `mines` list is non-empty, using the count already printed on `#sectorText`. Deploy-fighters (`deploy_fighters`, facts `qty` and `mode`) can borrow the same drop language with red darts. It is not a seventh state.

## Combat

Trigger, this seat as actor or as the victim named in facts. Read what the engine actually emits:

| Event | Facts to branch on |
| --- | --- |
| `combat` | `exchange_kind` of `ship_vs_ship`, `ferrengi_vs_ship`, `alien_vs_ship`, `ship_vs_unmanned`, `planet_siege`. Or `vs` of `fighter_sector` or `planet`. Losses: `attacker_losses`, `defender_losses`, `shield_losses`, `planet_fighters_lost`, `planet_shields_lost`. |
| `photon_fired`, `photon_hit` | `target`. A hit also has `disabled_ticks`. |
| `mine_detonated` | `hits`, `damage`, `victim`. |
| `ferrengi_attack` | `victim`. |
| `ferrengi_encounter` | `victim`, `ferr_fighters`, `your_fighters`. |
| `ship_destroyed` | `victim`, `reason`. The next observation paint is the pod when this seat died. The flash does not draw a second hull. |

`web/redesign.js` also checks `exchange_kind === "offensive_clash"`. This tip's combat payload uses `vs: "fighter_sector"` for that clash. P2 should follow `vs`, which is on the whitelist. No new exchange kind.

On the model. One language for MVP: a short white-orange streak across the stage, the shield bubble flaring if shields were lost, fighter markers pulsing if fighters were lost. The hull then settles on the post-combat observation, scars included when shields are under 35%. A planet repel stays in the starfield. A successful siege then enters planet-land.

Retires. Viewport stills and clips `combat_alert`, `combat_hit`, `combat_incoming`, `combat_miss`, `combat_photon`, and the combat group in `TW2KMedia`.

MVP. One flash, then the resulting idle, planet, or pod paint.

Later. A different camera per `exchange_kind`. Incoming versus outgoing streaks from `attacker === self_id`. A photon specifically as a single bolt, using `photon_fired`. Quasar (`quasar_fire`) and interdict (`interdict`) as a screen shake on the stage. All of those events exist. They wait.

## What must still be true after the viewport is gone

- The sector report is still readable, including port class, planet class, mines, and the LANDED line.
- Warp Skip, reduced motion, and the CU still frame still work.
- A history batch on connect does not replay FX. `TW2KMedia.onEvents(..., { history: true })` already suppresses that. The stage hook keeps the same rule.
- `holdWarp` remains, so a paused clip can still be inspected. Moving the node does not drop that hook.
