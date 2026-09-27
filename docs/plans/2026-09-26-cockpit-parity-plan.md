# Cockpit parity plan — `/bot` vs API LLM observation pack (2026-09-26)

**Author:** Commander (voice ask from Ben). **Plan only** — no game/UI code in this slice.
**Branch context:** `feature/seat-bot-competitive` / PR #1 (S1–S4 + S6 ACK'd; S5 docs still open).
**North star:** When Commander (or a human) plays from the hosted `/bot` URL, every fog-legal fact an API LLM seat can use for decisions is visible in the cockpit — equal information, not equal chrome.

## Ground truth (important)

API LLM seats and `/bot` already share **one** fogged object: `build_observation(universe, pid)` (`src/tw2k/engine/observation.py`). Harness:

| Client | Request | Payload |
|--------|---------|---------|
| `/bot` | `GET /harness/v1/{seat}/observation?…&format=json` (+ `peek=1`) | Full `observation` JSON (`model_dump`) |
| API / Path-B brains | often `format=llm` or `format=both` | `llm_user_message` = `format_observation(obs)` string; optional same JSON |
| Both | `GET …/events?since=` | Fogged `event_view` rows (same `_event_visible_to` rule) |

So the API pack is **not** a richer Observation. Gaps are:

1. **Render gaps** — fields already in the JSON `/bot` receives but under-shows or hides.
2. **Twin gaps** — values that exist only in `format_observation` / `/rules` (e.g. `stage_hint`, `system_prompt`), not as top-level Observation keys.
3. **Presentation filters** — cockpit deliberately drops some event kinds from English surfaces.
4. **Hard ban (unchanged)** — never wire spectator `/state`, unfogged map, or other seats' private obs into `/bot`. That is cheating, not parity.

Closest prior plans: `docs/plans/2026-09-21-bot-human-parity.md` (S1–S2 mostly shipped), `docs/plans/2026-09-21-commander-parity-plan.md`. This plan is the remaining **decision-path** delta after seat-bot S1–S6.

---

## What each side actually consumes

### Observation keys (engine)

Match/self: `day`, `tick`, `max_days`, `finished`, `self_id`, `self_name`, `credits`, `alignment`, `alignment_label`, `experience`, `rank`, `turns_remaining`, `turns_per_day`, `ship`, `corp_ticker`, `planet_landed`, `scratchpad`, `goals`, `operator_directive`, `operator_directive_updated_*`, `operator_dialogue`, `alive`, `net_worth`, `deaths`, `max_deaths`.

Space/economy: `sector`, `adjacent`, `known_ports`, `known_warps`, `known_sectors`, `trade_log`, `trade_summary`, `owned_planets`, `orphaned_planets`.

Social/intel: `other_players`, `rivals`, `inbox`, `recent_events`, `alliances`, `corp`, `limpets_owned`, `probe_log`, `recent_failures`, `action_hint`, `legal_actions`.

### `format_observation` (API prompt twin) — `prompts.py` ~605–715

Includes: self block, **`stage_hint`**, goals, operator_*, scratchpad, sector, adjacent, owned_planets, other_players, rivals, orphaned_planets, alliances, corp, inbox[-10], **`known_ports_top` (15)**, known_warps, trade_log[-25], trade_summary, recent_failures, recent_events[-30], **compact** `legal_actions` `{legal[], blocked{}}`, action_hint.

**Omits vs full JSON:** `known_sectors`, full `known_ports`, full `legal_actions` params, `limpets_owned`, `probe_log`, `finished`. Cockpit is already ahead on those when it renders them.

### `/bot` request/render path

- Poll: `refresh` / `watchLoop` → `format=json` only (`bot.js` ~1071, ~1095). Never asks `format=both` / `llm`.
- Render: `applyStatus` → `renderObservation` → panel helpers (`bot.js` ~873+).
- Events: separate `fetchEvents` → `renderEvents` (`bot.js` ~942–975).
- Thoughts: `renderLastResult` **strips** `agent_thought` and `llm_usage` (`bot.js` ~914).
- Raw escape hatch: `#rawObs` JSON drawer (`renderAdvisor`).

---

## Gap list (field-by-field)

Legend: **R** = render gap (data already in `/bot` JSON). **T** = twin/request gap. **F** = filter. **N** = not a gap / cockpit ahead. **X** = out of scope (god-state).

| # | Item | API LLM sees? | `/bot` today | Kind | Notes |
|---|------|---------------|--------------|------|-------|
| G1 | `stage_hint` {stage,label,reason,next_milestone} | Yes (in `llm_user_message`) | No | **T** | Computed in `format_observation`; not on Observation model. Fix: `format=both` + panel, or add optional `stage_hint` on obs (engine change — prefer client twin first). |
| G2 | `operator_dialogue[]` | Yes (last 8) | Markup stub only (`bot.html` empty `data-obs="operator_dialogue"`; JS never fills) | **R** | Directive string shows; dialogue thread does not. |
| G3 | `operator_directive_updated_day/tick` | Yes (nested) | Spans present, not populated | **R** | Tiny. |
| G4 | `other_players` non-corpmates | Yes (fog-limited) | **Filtered out** — only `is_corpmate` (`bot.js` ~464) | **R** | Same-sector rivals with ship_class disappear from UI while LLM still sees them. |
| G5 | Corpmate `alignment` on `other_players` | Yes | Not shown | **R** | |
| G6 | `owned_planets[].origin` | Yes | Not shown | **R** | S1 engine field; S5 docs pending. Critical for genesis vs claim. |
| G7 | `owned_planets[].colonists` / `colonists_total` | Yes | Not shown | **R** | Ferry sizing. |
| G8 | `owned_planets[].stockpile` | Yes | Not shown | **R** | |
| G9 | `owned_planets[].id` | Yes | Not shown in row (sector/name only) | **R** | Needed for assign_colonists etc. |
| G10 | `recent_events` incl. `agent_thought` summaries | In prompt feed | Event footer via `/events`; thoughts **hidden from last-result**; may appear as `kind` rows if filter=all | **F/R** | Toggle "show thoughts" or system filter chip; do not invent god events. |
| G11 | `llm_usage` events | Sometimes in fogged stream | Stripped from last-result; noisy in log | **F** | Keep off by default; optional System filter. |
| G12 | `llm_user_message` twin | Primary prompt | Not requested | **T** | Drawer: "API twin" for CU debug / equality proof. |
| G13 | `GET /rules` → `system_prompt` + verb list | Once per seat | Not fetched | **T** | Collapsible "Rules the LLM seats see". |
| G14 | Compact vs full `legal_actions` | Compact in prompt; full in JSON if `format=both` | Full list drives verb pad (good) | **N** | Cockpit richer. Show blocked reasons more prominently (partially in `#verbReasons`). |
| G15 | `known_ports` full list | Top 15 only in prompt | Full table | **N** | |
| G16 | `known_sectors` map | Omitted from prompt | Map rendered | **N** | |
| G17 | `limpets_owned` / `probe_log` | Omitted from prompt | Cards exist | **N** | |
| G18 | `rivals` last_seen_* | Yes | Shown | **N** | S6 brain uses; UI OK. |
| G19 | `orphaned_planets` | Yes | Shown (thin) | **R** (minor) | Add shields if present. |
| G20 | `action_hint` / goals / scratchpad | Yes | Shown | **N** | |
| G21 | Port stock/prices / ship / trade_* | Yes | Shown | **N** | Prior E1/S2. |
| G22 | Spectator `/state`, other seats' obs | N/A (cheat) | Must stay absent | **X** | Hard ban. |
| G23 | Streaming LLM tokens in bottom dialog | N/A on harness seats | Does not exist on `/bot` | **X** | Copilot chat is `/play`. Out of scope for fog parity. |
| G24 | Inbox / alliances / corp | Yes | Shown | **N** | |
| G25 | `sector.occupants` ids | Yes | Chips | **N** | Cross-link to other_players row when G4 lands. |
| G26 | Deadline / whose-turn / lobby | Status endpoints | Shown | **N** | |

**Bottom line:** Equal information is mostly **unhiding and labeling** fields already on the wire, plus **`format=both` + `/rules`** for the two prompt-only twins (`stage_hint`, `system_prompt`). Do not expand fog.

---

## Proposed Cursor slices (one PR-able unit each)

### CP0 — Audit harness (optional, 30 min)
Add a tiny script or test that diffs `Observation.model_fields` vs keys rendered in `bot.html` `data-obs` / `bot.js` `obs.` reads, and vs keys in `format_observation` payload. Locks this plan. No UI change.

### CP1 — Empire planet tape (G6–G9, G19)
**Files:** `web/bot.js` `renderPlanets`, maybe `bot.html` column hints.
Show `id`, `origin`, `colonists_total` (and per-pool on expand), `stockpile` summary, orphan shields.
**Done when:** human at `/bot` can size a ferry without opening Raw obs.
**Tests:** DOM/unit or Playwright asserting planet row contains origin + colonists when fixture obs has them.

### CP2 — Other players full fog list (G4–G5, G25)
Stop filtering to corpmates; render non-mates with alive/corp/sector/ship when present; mark corpmates.
**Done when:** same-sector non-corp occupant visible in Rivals/Others panel, matching JSON.

### CP3 — Operator dialogue + directive meta (G2–G3)
Render `operator_dialogue` as a short transcript; show updated day.tick when directive set.
**Done when:** dialogue entries from fixture obs appear under notes.

### CP4 — Prompt twins (G1, G12, G13)
- Switch cockpit polls to `format=both` (keep using `observation` for panels).
- Drawer: `stage_hint` chip on scoreboard + `#llmTwin` pre with `llm_user_message`.
- Once per connect: `GET /harness/v1/rules` → show `system_prompt` in a details drawer.
**Done when:** CU can answer "what stage_hint / system prompt would an LLM seat see?" from `/bot` alone.
**Ban:** do not POST or decide from spectator routes.

### CP5 — Event thought toggle (G10–G11)
Event filter chip `thoughts` (off by default) OR include `agent_thought` in last-result only when chip on. Keep `llm_usage` default-hidden.
**Done when:** toggling shows own thought text from fogged `/events` without exposing other seats' private thoughts beyond existing fog rules.

### CP6 — Docs pass
Update `docs/GROK_BOT_PLAYER_GUIDE.md` + short note in `docs/GROK_BOT_CONNECTOR.md`: same Observation; cockpit render checklist; hard ban on `/state` for seat play; pointer to this plan. Coordinate with open **S5** seat-bot docs (do not duplicate conflicting text).

**Suggested order:** CP1 → CP2 → CP3 → CP4 → CP5 → CP6 (CP0 anytime). Independent enough to land one-at-a-time on PR #1.

---

## Non-goals

- Mid-match brain patches for the live mixed match.
- Merging `/bot` and `/play` copilot chat.
- Adding unfogged galaxy data "so Commander can catch up."
- Replacing Path-B mailbox with cockpit clicks as the competitive brain.

## Acceptance for the whole track

A Commander computer-use session on `/bot` can, without Raw JSON or spectator:

1. Read stage + operator dialogue the LLM would see.
2. See every fog-visible other_player and full owned_planet colonist/origin/stockpile facts.
3. Optionally inspect `llm_user_message` and `system_prompt`.
4. Still cannot see another seat's private observation or god `/state`.

---

## Mailbox note

Plan authored by Commander. After Ben/Commander ACK, queue **CP1** (or finish seat-bot **S5** docs first — both are docs/UI; S5 is seat-brain docs, CP6 is cockpit docs).
