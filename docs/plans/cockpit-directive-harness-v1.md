# Cockpit directive harness v1

A commander layer for Grok cockpit players. The seat keeps playing on its own. Ben can drop a structured directive into that seat's inbox, and the next turn's prompt carries it next to the cockpit the seat already sees.

This does not add a server route. It does not widen fog. It does not add a cheat sheet. The cloud agent that lands this change does not open a live game port and does not touch `wt_live`.

## North star

The player is a cockpit seat:

- Computer-use: `/bot?seat=Pn&mode=cu&token=...` (the same link a person opens).
- Or the four harness reads the cockpit already uses (`observation`, `reference`, `events`, `status`) and `POST .../action`, with that seat's bearer token.

The core loop stays autonomous. Each seat also has a directive inbox Ben can write. A directive is structured text, not a hidden map:

| Field | Required | Meaning |
| --- | --- | --- |
| `goal` | yes | What Ben wants, in words. |
| `target` | no | A trader, planet, commodity, or `quasar`, as named on the cockpit. |
| `sector` | no | Sector id the goal is about. |
| `priority` | no | Higher runs first. Default 0. |
| `id` | no | A short name Ben can recognize in the log. |
| `expires` | no | ISO-8601 instant, a bare day number, or `day:N`. The seat drops the row at that instant, or after that game day. |
| `expires_day` | no | Same day rule, as its own field. The row is still active on that day. |

Two examples Ben asked for:

- "finish level 3 citadels and add colonists for quasars"
- "scenario test: attack Trader X in sector Y"

Those strings are goals. The sector and the trader are fields, not something the harness parses out of the sentence and not something it looks up off the map.

## What this is not

- Not a new privileged API. `/api/ai-directives` stays the in-process LLM operator route. External and computer-use seats do not gain a sibling of it. Ben's text never enters the universe object.
- Not a cheat sheet. The block added to a turn says the goals are not extra map data, then lists them. It does not paste verb tables, prices, or win conditions.
- Not extra fog. The state beside the directive is the observation or the rendered page the seat already had. A scripted step may use `legal_actions`, the current sector, and names already on that observation (`rivals`, `other_players`, occupants). It does not pathfind through sectors the cockpit did not list, and it does not read another seat's observation.
- Not a second brain. If a model is configured, the model chooses. The harness only refuses a proposal the cockpit does not list as legal. If no model is configured, the harness may take one unambiguous legal step toward the top directive and otherwise leaves the existing heuristic or scripted trader alone.

## Inbox

One directory, one file per seat, plus a private folder the harness owns:

```
runs/directives/
  P3.json                 Ben's file for P3
  P4.json                 Ben's file for P4
  P3/
    inbox.json            optional second drop for P3 (loaded with P3.json)
    recovery.json         harness only; written when the seat is stuck
    ESCALATE.json         harness only; Ben's signal to look
    turns.jsonl           prompt, response, outcome
    heartbeat.json        last status heartbeat
```

`P3.json` is the file Ben drops. `recovery.json` is not a place to edit by hand; the next progress deletes it. `ESCALATE.json` stays until Ben deletes it.

A file may be one object, a list, or `{"directives": [ ... ]}`. A row with no `goal` is skipped. A file that is not JSON is skipped so one bad drop does not kill the seat. `scripts/drop_directive.py` is stricter: it refuses to write a file with no goal.

Active rows are those that have not expired. Sort is priority descending, then the order they were read. Ben's file is read before `inbox.json`, then `recovery.json`.

Recovery uses priority 90. The checked-in examples use 10 and 20, so a recovery outranks them until the seat makes progress. A directive with priority 100 stays above recovery.

Seat ids are a single token (`P3`). A value with a slash, a dot, or any other path character is rejected so an inbox path cannot escape the directory.

## How Ben drops one

Edit a copy of an example, then copy it into the inbox. This writes `runs/directives/P3.json` and does not call the server:

```
python3 scripts/drop_directive.py \
  --inbox runs/directives \
  --seat P3 \
  --file examples/directives/citadel-quasars.json
```

Or copy the file yourself to `runs/directives/P3.json`.

Point the player at that directory. The seat id comes from the cockpit URL (`seat=P3`). Do not aim these commands at a live game from a cloud VM; pass a base URL or seat link you already run locally.

Computer-use (rendered `mode=cu` page):

```
python3 scripts/ai_cockpit_player.py \
  --url 'http://127.0.0.1:8050/bot?seat=P3&mode=cu&token=...&layout=redesign' \
  --provider grok \
  --directives runs/directives \
  --run-dir runs/ai-cockpit/P3
```

Cockpit seat (the harness routes the page calls, still that seat's token):

```
AI_COCKPIT_SEAT_MODE=tw2002 python3 scripts/run_cockpit_seat.py \
  --base-url http://127.0.0.1:8027 \
  --seat P3 \
  --tokens-file tokens.json \
  --days 10 \
  --directives runs/directives
```

Grokbot mailbox or heuristic, one process, many seats, each with its own inbox file and log:

```
python3 scripts/grokbot_seat_client.py \
  --seats P3,P4 \
  --policy mailbox \
  --directives runs/directives
```

Remove `P3.json` to clear Ben's goal. Set `expires_day` or `expires` to let it age out. Delete `P3/ESCALATE.json` after you have looked.

## Turn prompt

On a model turn the directive block is part of the user prompt, next to cockpit state.

Computer-use (`scripts/ai_cockpit/providers.py`) appends the block to the existing screen prompt: step, visible controls, visible text. The system playbook is unchanged. A mock or live provider sees the goals. The scripted trader does not read prompts; it still plays the screen, and the log still records the goals that were active.

The cockpit LLM hook (`llm_prompt_payload` in `cockpit_seat.py`) adds a `directives` field to the small JSON it already sends (sector, day, turns, credits, legal kinds). It does not attach the in-process one-screen cheat sheet.

The grokbot mailbox pending file gains `directives` (the same block) and `directive_list` (the structured rows). The observation in that file is the one `GET /observation?format=both` already returned. Rules text is still sent once, as it was before this harness; this change does not extend it.

The block itself is:

```
Operator directives for this seat. They are goals from Ben, not extra map data.
Use only what this cockpit shows. If a directive is not legal from the screen,
do not invent a move; take the best legal step or leave the goal for a later turn.

1. priority 20 id scenario-attack
   goal: scenario test: attack Trader X in sector Y
   target: Trader X
   sector: 42
   expires day: 5
```

If the previous proposal was refused locally, the next prompt adds one line: `The last proposal was not submitted: ...`. After an escalation it adds one line that Ben has been flagged and the seat must stay on legal cockpit moves.

## Validation before submit

A proposal is submitted only when the cockpit says it is legal.

Harness and grokbot seats (`legal_actions` on the observation):

- The kind must be listed and `legal: true`. A missing kind, or a kind with a reason, is not posted.
- The cockpit seat also requires the kind to be one `CockpitSeat.post_action` already accepts. A kind outside that list is "not a cockpit action" even if some other surface would allow it.
- Warp and plot targets must be in `params.target.choices` when that list is present, otherwise a warp target must be in `sector.warps_out`.
- Attack targets must be in the cockpit's target or ferrengi choices when those lists are present.
- Trade commodity and quantity must sit inside the buy/sell choices and the quantity cap when the envelope has them. A haggle price is not a reason to refuse.
- Any other argument whose envelope has a non-empty `choices` list must be one of those choices.

The first illegal proposal on a turn is not posted. The reason is logged and put on the next prompt. The second illegal proposal on that same turn becomes `wait` when wait is legal. If wait is not legal either, the seat does not invent a move; after four refusals it writes `ESCALATE.json` and keeps polling.

Computer-use keeps the check it already had: a click, type, or press must name a control on the screen (`reject_reason`). A click that is not on the screen becomes a wait and is logged. That is the legal state of `mode=cu`.

## One scripted step

When no model key is set, `directive_step` may replace the heuristic for a single action. It returns nothing unless `validate_proposal` accepts the result.

- A recovery directive: warp to the first legal target, unless the last action was already a warp. Otherwise scan, lift off, or wait, skipping the kind just tried.
- A sector, and the ship is not there: warp if that sector is a legal target. Otherwise `plot_course` with `execute: true` when the cockpit lists that as legal and the target is an allowed choice. No search through the rest of the map.
- On site, only when the goal text asks for it and the envelope is unambiguous:
  - attack, if `target` equals a legal id or a name already on the observation whose id is a legal choice
  - `build_citadel`, if the cockpit names exactly one planet
  - colonists: `assign_colonists` when the from/to pools are a single legal choice (a pool named in the goal wins, including `colonists`), else `terra_colonists` take up to the cockpit cap, else `buy_equip` colonists up to that cap

"Finish level 3 citadels and add colonists for quasars" therefore builds when `build_citadel` is legal, and moves colonists when that form is legal. It does not invent a quasar cannon verb. The model, if one is configured, still sees the full sentence and chooses.

## Heartbeat and reconnect

A dropped session must not burn the turn.

The server already treats `GET /harness/v1/{seat}/status` and `GET .../observation` as presence (`note_harness_poll`, `touch_client`). The harness uses that status GET as the heartbeat. It also writes `heartbeat.json` in the seat folder at most every 5 seconds so Ben can see the last chip, day, and sector without reading the game.

Reconnect is client-side:

- HTTP 502, 503, and 504, and connection timeouts, are retried with backoff (0.5s, doubling, capped at 8s). A 409, 422, or 429 is not retried as a transport error. A 429 during a directive-seat retry means the post already landed; the client does not send a second action.
- Between tries the client hits status again, which refreshes presence, and then repeats the same read or the same post. It does not advance `turn_seq` on its own.
- Computer-use already reloaded a blank page once. With `--directives`, a failed reload is tried four more times. The step counter does not move, so a blip does not spend the action budget. The seat URL, including the token, is the same link.

Without `--directives`, the grokbot client and the cockpit seat keep their previous error behavior. The inbox is what turns the harness on.

## Per-seat logs

`runs/directives/<SEAT>/turns.jsonl` is one JSON object per attempt:

```
{"at", "seat", "prompt", "response", "outcome"}
```

`outcome.submitted` is false when the proposal was refused locally. Tokens are removed before the line is written: the seat token, `token=` query values, `Bearer ...`, `sk-...`, and `xai-...`. The computer-use player also keeps its existing `player.log` redaction.

Logs, recovery, escalation, and the heartbeat for P3 never open P4's directory.

## Stuck detection

Progress is the cockpit fingerprint: game day, sector, net worth, and owned-planet citadel level plus colonists. A rendered page uses day, sector, and net worth from the screen.

The same fingerprint `stuck_after` times (default 6) writes `recovery.json` and counts a recovery. The same fingerprint `stuck_after * 2` times writes `ESCALATE.json` and sets `escalated` on the run report. A changed fingerprint deletes `recovery.json`. `ESCALATE.json` stays for Ben.

The fingerprint is taken after the action, from the next observation when the cockpit seat has one, or from a fresh screen read on the computer-use page. A warp that changes sector clears the streak.

## Where the code sits

| Piece | Role |
| --- | --- |
| `scripts/ai_cockpit/directives.py` | Inbox, prompt block, validation, stuck watch, reconnect, logs. No engine import. |
| `src/tw2k/agents/cockpit_directive.py` | Re-export so the seat and the grokbot client share that file. |
| `scripts/ai_cockpit/providers.py` | Puts the block on the computer-use user prompt. |
| `scripts/ai_cockpit/runner.py` | Loads the inbox, heartbeats, reconnects, logs, stuck-detects. |
| `src/tw2k/agents/cockpit_seat.py` | Optional `directives=` on `run`. Gates posts. Retries dropped calls. |
| `src/tw2k/agents/pathb_client.py` | Same gate, heartbeat, and mailbox fields for grokbot seats. |
| `scripts/drop_directive.py` | Ben's copy into `<inbox>/<SEAT>.json`. |
| `examples/directives/*.json` | The two example goals. |

`run` without `directives` does not wrap HTTP and does not gate. Existing cockpit games stay on the heuristic.

## Tests

`tests/test_cockpit_directive_harness_v1.py` covers expiry and priority, seat isolation, redaction, legal-action refusal, the scripted step, stuck recovery and escalation, reconnect, the computer-use prompt, the drop script, a cockpit seat that posts the directive warp and refuses an illegal one, and a grokbot seat that does not submit an illegal mailbox action. The rendered player still refuses to import `tw2k`.

## Out of scope

- Flipping `AI_COCKPIT_SEAT_MODE` or starting a match.
- Editing `/api/ai-directives` or the in-process cheat sheet.
- Teaching the scripted screen trader to follow prose without a model.
- Any port Ben is already playing.
