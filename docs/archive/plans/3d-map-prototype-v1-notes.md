# 3d-map-prototype-v1

Throwaway page only. It is not in the spectator and not in the cockpit. The live games were not used.

The page is `prototype/3d-map/map.html`, with `galaxy-40.json` (40 sectors, 108 links) and `galaxy-1000.json` (1,000 sectors, 2,700 links, 7 markers). Drag orbits, the wheel zooms, and a click names the sector. One-way links have an arrow. Ports are three letters. The height is a small fake jitter so a flat graph can tilt. No three.js.

The cockpit switch throws away every sector outside a short known list and draws a dashed stub for each cut link. The stub's direction comes from the missing sector's number, not from that sector's coordinates. The drawing function never receives the sectors that were thrown away.

## What the page actually did

Opened in a browser on a spare local port, then closed.

The 1,000-sector picture drew in about 1.0 to 1.4 milliseconds. Eight frames were all in that band. At the opening zoom it drew 0 labels. The shape is a spiral of dots and crossings. You can see that it is a galaxy. You cannot read a sector number or follow one lane.

The 40-sector picture draws every number, and the numbers in the middle sit on top of each other. Orbiting spreads a few of them. It does not become a chart.

With the cockpit switch on, the 1,000-sector set became 25 sectors, 25 links, and 123 stubs, in about 0.2 milliseconds. The outer numbers and port letters can be read. The sectors near the middle still pile up. That is the only view that is partly readable, and it is a neighborhood, not the whole map.

## Recommendation

No. Do not put this in the spectator, and do not put it in the cockpit.

The canvas is fast enough. A heavier library would not fix the reading problem. The 2D maps stay the maps. A later build, if Ben asks for one, should be a neighborhood of the sector you are in, and it still has to take only the sectors that seat already knows.
