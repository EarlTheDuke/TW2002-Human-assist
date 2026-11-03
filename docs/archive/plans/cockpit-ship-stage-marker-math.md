# Fighter marker math — ship stage

Parent: [P0 pack](cockpit-ship-stage-p0.md). Finder: [sheet index](cockpit-ship-stage-INDEX.md).

Planning only. Surveyed `feature/grokbot-player` @ `5714c733`. This sheet records the shared 100:1 count the ship-stage pack already uses. It does not change the engine, the cockpit, the meshes, or the warp clips. Dart shape, ring clearance, and per-hull looks stay in the P0 pack.

## Formula

Onboard fighters `n`. The P0 pack treats this count as already decided.

- `n = 0` shows no markers.
- `n ≥ 1`: marker count = `max(1, ceil(n / 100))`.

Fleet order writes the same rule as `n < 1 → 0`, else `max(1, ceil(n / 100))`. Each marker stands for 100 fighters. The last marker may be a partial hundred and is not given its own numeral. The stat line keeps the exact bay. The legend is `each marker = 100 fighters`.

| Bay `n` | Markers |
| --- | --- |
| 0 | 0 |
| 1–99 | 1 |
| 100 | 1 |
| 101 | 2 |
| 1,000 | 10 |

`ceil(100 / 100)` is 1, so a full hundred is still one marker. `101` is the first bay that draws two.

Render-memo checks: 30 → 1, 2,500 → 25, 50,000 → 500. P1's done-when uses the same 25 and 500, plus a measured 1,000-marker case for the later Interdictor. Fleet order states that case as 1,000 markers at 100,000 fighters. The Scout is the one cap that moves a count between tables: base 150 → 2 markers, live 250 → 3.

If 1,000 separate SVG paths miss the frame, the render memo's fix is one group updated by a transform, or one canvas layer for markers only. It is not a silent change to `ceil(n / 100)`. The count formula does not gain a silent cap.

Live markers orbit outside the hull body.

## Stills

CU-seat and reduced motion keep the markers as a static count. `body.cu-seat` and `?mode=cu`, `prefers-reduced-motion`, and viewport mode `stills` hold the end frame and do not loop. The render memo and the fleet order require a phone still, a reduced-motion still, and a `body.cu-seat` canonical still, with no loop on those three.

Live idle is the state that runs the fighter orbit. A still draws the count in the table and holds the pose. The orbit does not run.

## Read next

- [Sheet index](cockpit-ship-stage-INDEX.md) — product order and the pack.
- [P0 pack](cockpit-ship-stage-p0.md) — sticky rule, legend, and the phased done-when.
- [Render decision](cockpit-ship-stage-p0-render.md) — spike marker checks and the frame-time bar.
- [FX state machine](cockpit-ship-stage-p0-fx.md) — idle orbit, and the held pose when motion is off.
- [Fleet order](cockpit-ship-stage-p1b-fleet-order.md) — the same formula on the other 15 hulls.
