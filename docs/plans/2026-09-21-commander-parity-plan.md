# Commander plan: info/tool parity for Grok Bots + humans (2026-09-21)

**Author:** Commander (independent of Fable). Do not treat this as the build spec until it is merged with `docs/plans/2026-09-21-fable-parity-plan.md`.

**North star:** Several Grok Bots (and a human at `/bot`) can sit in the same hosted match as TinyBox LLM seats and compete with the **same fogged observation, the same rules text, and the same legal verbs**. Success is not "the UI can warp." Success is a Grok Bot seat that can trade, plot, scan, and fight from the same facts Qwen sees over the API.

**Out of scope:** xAI / `api.x.ai` as the Grok Bot brain. TinyBox as Commander. Rewriting the engine.

---

## What we just proved

Hosted `/bot` + localhost.run URL + computer use can connect, wait for Qwen, and submit warps without 403. That is a **control-path** win. It is not **decision-path** parity.

## Two paths (keep both)

| Path | Who | How they decide | How they act |
|------|-----|-----------------|--------------|
| A. Cockpit | Humans + computer-use Grok Bots | What `/bot` shows | Buttons / taps |
| B. Harness brain | Competitive Grok Bots | `GET /harness/v1/{pid}/observation?format=both` + `GET /rules` (same object LLM seats get) | `POST .../action` |

Path A is how we test the product and how a person plays. Path B is how a Grok Bot actually competes with Qwen. Forcing every competitive thought through screenshots will always lose to an API seat that sees `known_ports`, prices, and `action_hint`.

A Grok Bot can use both: pull the full observation to think, then either POST the action (precision) or click `/bot` (UX proof). Multi-bot seats should default to Path B once Path A shows the same fields.

---

## Gap vs LLM API seats (grounded in live `/bot` + Observation)

`/bot` today shows: credits, sector, turns left, day/tick, cargo free, ship class, foggy rivals, whose turn, port **code + buys/sells names** (no stock, no prices), `action_hint`, warp chips, SCAN, WAIT, sell-all / buy-first, last_result JSON, short log.

**Missing from the Observation every LLM seat already gets:**

- You: net worth, alignment, experience, rank, deaths
- Ship: holds, cargo by commodity, fighters, shields, mines, genesis, probes, missiles, cargo cost basis
- Here: port stock/current/max/price/side, planets, occupants, fighters/mines/ferrengi, FedSpace
- One hop: `adjacent[]` (port code, fighters, planets, occupants, known)
- Memory (this is the big one): `known_ports[]`, `known_warps{}`, `trade_log` + `trade_summary`, `recent_failures[]`, owned/orphaned planets
- Prompt twin: `GET /rules` `system_prompt` + `format=llm` `llm_user_message`

**Missing verbs (34 on `/rules`; `/bot` exposes ~4):**

warp, scan, wait, crude trade. Not exposed: plot_course, probe, haggle `unit_price`, buy_ship, buy_equip, deploy fighters/mines, attack, photon, genesis, planet land/claim/cargo/citadel, hail/broadcast, alliance, corp.

Server-side player memory already exists. Grok Bots do not need a second map database if they consume Observation. Humans need that memory **drawn**.

---

## Product principles

1. One observation object. `/bot` is a renderer of `Observation`, not a second game.
2. Only legal verbs light up (same preconditions the engine already enforces).
3. English first for humans; JSON last-result is a drawer, not the main line.
4. One Grok Bot chat per external seat. Do not share one brain across P3/P4/P5.
5. Unattended external seats idle-WAIT (already default). A competitive match sets `-ExternalSeats P3,P4,P5` only when those bots are actually attached.
6. Tokens stay on VENGEANCE; never commit. Tunnel URL is not the long-term home — Tailscale is.

---

## Phases (build after merge)

### E0 — Dual plans, then merge (this loop)

Commander writes this file. Fable writes `docs/plans/2026-09-21-fable-parity-plan.md` independently. Commander merges into `docs/plans/2026-09-21-bot-human-parity.md` and queues E1.

### E1 — Info parity on `/bot` (read-only)

Surface the Observation a competitive player needs, still fogged:

- Ship tape: cargo by commodity, holds, fighters, shields, probes
- Port tape: code, each commodity side/qty/price/stock
- Adjacent strip: warp targets with port code + known flag (not just a number)
- Map memory: known_ports table + known_warps count / simple list
- Trade: last trades + `trade_summary` P&L
- Failures: `recent_failures` so we stop retrying dead moves
- Last result in one English sentence; raw JSON collapsed
- Optional "API twin" drawer: pretty-printed observation + `action_hint` (already shown)

Done when a human at `/bot` can answer "what can I sell here, at what price, and which known BBS port is closest" without opening the harness.

### E2 — Verb pad (legal-only)

Add gated controls with `data-testid` (CU + human):

- Trade: commodity + qty + optional haggle price (replace sell-all/buy-first as the only trade)
- Plot course: target sector from known_warps (execute)
- Probe: target + confirm 5k
- Attack / hail when occupants exist
- StarDock cluster only in sector 1: buy_ship, buy_equip
- Planet cluster only when landed / orphan listed

Keep SCAN / WAIT / WARP. Do not dump all 34 verbs on one screen; group by context.

Done when a CU bot can complete a buy-then-warp-then-sell loop from the UI.

### E3 — Human cockpit (same data, kinder)

- Known-space sketch (sectors you have warps for; you are here)
- Keyboard: 1–9 warp, S scan, W wait
- Event log in English (not only event_seqs)
- Notes field local to the browser (human memory the API seats fake with scratchpad)
- Spectator link already exists; add "open this seat in spectator"

### E4 — Multi-bot ops

- Hosted script already supports `-ExternalSeats P3,P4,P5`
- Lobby page or `/bot` seat chips: three URLs, three token slots, whose-turn across seats
- Wire existing `TW2K Grok Bot turn_due` webhook so each seat's bot wakes on its turn (Path B)
- Docs: one Grok Bot agent per seat; do not drive three seats from one CU session
- Prefer Tailscale for overnight; localhost.run is fine for a session

Done when three Grok Bots can take turns in one match without stalling on an empty seat.

### E5 — Competitive brain (Path B default for Grok seats)

- Small attended client (or Commander-on-VENGEANCE loop) that long-polls observation `format=both`, decides, POSTs action
- Feed `system_prompt` once per match (same rules Qwen gets)
- Keep `/bot` open as the human/CU view of the same seat (read-only spectator of your own bot optional)
- This is how we "play to win" against Qwen. CU stays the UX test.

---

## Ideas (not committed)

- Corp / alliance later; first competitive loop is trade + plot + scan.
- Shared "captain's notes" file per seat on disk for AFK Grok Bots (scratchpad_update already exists on Action).
- Human "recommend move" button: server returns `action_hint` plus top-3 legal actions scored by a tiny heuristic (not a second LLM).
- Don't add chat between Grok Bots that Qwen cannot hear unless we also expose hail/broadcast in the Qwen prompt (it already has those verbs).

## Risks

- Growing `/bot` into a second engine. Mitigation: render Observation only.
- Three CU browsers fighting one desktop. Mitigation: Path B for extra seats.
- Cloudflare 403 on datacenter browsers. Mitigation: localhost.run or Tailscale; never CF quick tunnel for CU.
- Info leak: never show unfogged map on `/bot`.

## First Cursor task after merge (not now)

E1 only. No E2–E5 code until Commander queues it.
---

## Future wish list — immersive cockpit (deferred, protect the architecture now)

The eventual product is a complete human game interface, not merely a bot debug page. The cockpit should make TW2K feel excellent to play while remaining accessible to computer-use bots.

Future experiences:
- Short video clips for major moments: entering a sector, docking, combat, planet founding, citadel completion, destruction/respawn, day rollover, victory.
- Still images / illustrated cards for ports, StarDock, planets, ships, Ferrengi, hazards, corporations, transmissions, and notable sectors.
- Cockpit ambience: sector backdrop, ship HUD, alerts, comms, action feedback, optional sound.
- Event-directed media: engine emits semantic event keys; the UI chooses an asset. Never infer game truth from a video and never put game rules in the asset layer.
- Media is optional, skippable, cached, low-bandwidth friendly, and never blocks the turn timer or hides required text.
- Accessibility / bot parity: every visual event also has text, stable DOM state, `data-testid`, reduced-motion mode, captions, and an instant-skip control.
- Asset manifest / theme packs later so art can evolve without rewriting engine or cockpit.

Architecture guardrail now: build the human cockpit from structured Observation + event data, with a presentation layer where media can be added later. Do not implement clips/images in E1–E2, but do not hard-code the UI so they require a rewrite.