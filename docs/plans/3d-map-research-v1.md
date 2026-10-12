# 3d-map-research-v1

Plan only. No feature code in this slice. Commander and Ben review this before any build.

Ben asked for a 3D galaxy map on the spectator dashboard, and later in the player cockpit. He also said it may be hard or impossible. This note agrees with the hard part, and it is not the graphics.

## What the game already draws

The spectator page (`web/app.js`, `buildMap`) draws every sector the server sent on the opening snapshot. That list is the whole universe. It is an SVG: one line per warp, one circle per sector, pan and zoom. Sector positions come from the generator (`_compute_layout` in `src/tw2k/engine/universe.py`). Sector 1 is pinned at the center. Everyone else starts on a spiral. Sixty passes pull linked sectors toward a rest length of 40. Repulsion is turned off, because a real push-apart of 1,000 sectors was already too slow at generation time. The picture is a flat hairball with a center.

The cockpit (`web/bot.js`, `renderKnownMap`) draws a different picture on purpose. It uses only `known_sectors` and `known_warps` from that seat's observation. A warp whose far end has no known coordinate is a short dashed stub around the sector the seat does know. The stub does not use the real coordinate of the unknown sector. Clicking a node fills a plotted course only when the engine says `plot_course` is legal.

A default game is 1,000 sectors, about 2.7 warps each, and about 15 percent of those warps one-way. That is on the order of 1,000 dots and 2,000 to 2,700 lines. Seven players are seven markers on top of that.

## Feasibility

Drawing 1,000 points and a few thousand lines in 3D is easy on a current PC. A phone browser can do it. The part that may be impossible is a map a person can read.

The links are the map. In the flat view they already cross. A third axis hides a crossing behind another crossing. One-way arrows, port letters, FedSpace, and "you are here" all need to stay readable while the picture turns. At 1,000 labeled sectors they will not. The useful view is a neighborhood: the sector you are in, the lanes out of it, and the ports you remember. The whole galaxy is a picture of the generator, not a chart you navigate from.

There is also no real height. The generator stores x and y only. Any z is invented. A force layout in three axes would be a new picture, not a view of the one the 2D maps already use. Recomputing positions would move every dot the current pages depend on. That is an engine change, and it is out of this plan.

## Four options

### 1. WebGL force-directed graph (three.js)

Build a new 3D layout in the browser. Nodes repel, links attract, the user orbits.

Cost: a new dependency, a layout that runs in the page, and a second implementation of one-way arrows, port colors, and click-to-plot. A few seconds of layout jank on 1,000 nodes is likely unless the forces stay as cheap as the generator's (attraction only). The result will not match the 2D map, so a player cannot use both and recognize a sector.

Performance of the draw itself is fine. Readability is worse than the SVG we have. Fog risk is high if the layout is handed the full link list in order to look stable.

### 2. Isometric or layered canvas (2.5D)

Keep the current x,y and draw them with a fixed tilt, thicker lanes, and a fake floor.

Cost: one canvas painter, no new library. It looks more expensive than the SVG and answers the same questions. Warp crossings get harder, not easier. Labels still collide. This is a skin.

### 3. Rotatable projection of the current layout

Keep the generator's x and y. Set z to 0, or to a tiny stable jitter so stacked dots separate when you tilt. Project with a normal canvas (no three.js). Drag to orbit, wheel to zoom. Draw the same nodes and edges the SVG already has.

Cost: one throwaway page first, then, only if that page is readable, a canvas next to the existing SVG. No engine change. No new coordinates. The 2D maps stay.

Performance: 1,000 circles and ~2,500 lines on a 2D canvas is a single frame well under a refresh, including seven ship markers. The slow part of today's spectator map is SVG DOM, not the shape of the data. A canvas is lighter than the SVG, not heavier. The cockpit's known set is much smaller than 1,000 until late in a game.

Readability: orbiting a flat graph lets you unstick one crossing. It does not make 1,000 labels legible. The prototype below is the test. If the labels fail, this option stops.

### 4. Keep the 2D maps and add depth cues only

Leave `buildMap` and `renderKnownMap` as they are. Add a softer far-zoom, thicker lanes near the selected sector, and fade for distant links. No rotation.

Cost: small, and it cannot leak a new field. It also does not answer Ben's request for a 3D map. It is the fallback if option 3 fails the readability check.

## Fog of war

The cockpit must be physically unable to draw a sector it was not given.

- The renderer takes a node list and an edge list. It does not accept a universe, a websocket snapshot, or the spectator `sectors` array.
- Cockpit nodes are `known_sectors` only. Edges are `known_warps` only. An unknown far end stays a stub placed around the known end. The stub must not be given that sector's real x,y. Those coordinates exist, and using them would show where an unvisited lane sits in the galaxy.
- Other seats' ships, planets the seat has not seen, and port letters the seat has not traded are not in this list today. A 3D view does not add them.
- The spectator page may keep the full snapshot. It is the god view. It must not be iframed into the cockpit, and the cockpit must not open the spectator socket.
- Honest limit of the current 2D map, which a 3D view would inherit: a known sector is drawn at the coordinate the generator computed from the whole graph. The gaps between known dots are shaped by sectors the seat has not visited. The cockpit already ships those x,y values. This plan does not widen that. It also does not claim the coordinates are free of layout information.

## How it would sit in the pages

Spectator: `web/app.js` already has the full node list and the warp list inside `buildMap`. A later canvas would read that same list. The SVG stays until a review says the canvas replaces it.

Cockpit: `renderKnownMap` already decides the nodes, the edges, and the stubs. A later canvas would sit in the same card and consume that same decision. Click-to-plot stays behind the engine's `plot_course` legality, the same as today.

No new action, no new flag, and no new observation field are required for a projection of data the pages already hold. A flag would matter only if a later slice changed the engine or the default view. That slice is not this one.

## Risks

- The map is unreadable at 1,000 labels. This is the risk that should stop the work.
- A shared "map component" that sometimes receives the spectator list and sometimes the cockpit list will eventually receive the wrong one. The prototype should show the cockpit path refusing coordinates it was not passed.
- One-way arrows and port letters are the actual TW2002 information. A pretty cloud that drops them is not a map of this game.
- three.js is not in the repo. Adding it for a graph that is already flat is a dependency the canvas projection does not need.
- Rebuilding layout in 3D changes every saved picture and every test that looks at sector x,y.
- Live games are not a place to try this. The prototype uses fake numbers only.

## Recommendation

Do option 3 as a throwaway, and do not put it in the cockpit or the spectator until that throwaway is readable. Option 1 is buildable and a worse map. Option 2 is a skin. Option 4 is what we already ship, and it remains the map if the prototype fails.

The thing to protect is the cockpit's node list, not the choice of WebGL.

## Throwaway prototype

A separate worktree. Not this branch. No engine checkout changes, no server, no port, no live game.

One HTML file and a few fake JSON blobs:

- Forty sectors with the same kind of links, so a person can tell whether an orbit helps.
- One thousand sectors, about 2,700 links, seven colored markers, so a person can see frame time and whether any label survives.
- A cockpit switch that deletes every node not in a short "known" set and draws stubs for the cut links, with no access to the deleted coordinates.

Drag to turn, wheel to zoom, click a dot to show its id. Record whether the labels can be read and whether a frame of the large set stays smooth. If the labels fail, write that in the prototype note and stop. Do not add three.js unless the canvas projection itself is too slow, which is unlikely at this size.
