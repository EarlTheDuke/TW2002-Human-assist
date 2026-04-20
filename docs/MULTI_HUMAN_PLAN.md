# Multi-human multiplayer plan (Phase H6.5)

> Status: **PLAN ONLY**. Noted for a later phase; we want to finish
> polishing single-human + copilot first.
> Last updated: 2026-04-20.

## Goal

Today, a `tw2k serve --human P1 --human P2 …` match can already seat
N human slots at the engine level — `HumanAgent` is per-player, the
scheduler round-robins through them, and `/api/match/humans` lists
them. What's missing is the **cockpit UX**: everyone opens `/play` and
the UI auto-binds to the first human slot, there's no cross-player chat,
voice channels collide (every tab listens on the same mic), and the
copilot is siloed per-player with no way to broadcast a shared plan
("Team: we're running ore from 42 to 101").

Phase H6.5 closes that gap.

## Target UX

1. User opens `/` (spectator) or `/play` → sees a **slot picker**:
   > *"You have 4 human slots open: P1 (waiting), P2 (Alice),
   > P3 (waiting), P4 (you — resume)"*.
2. Choosing a slot binds that browser session to that player. A cookie
   or `localStorage` key remembers the binding so a refresh doesn't
   lose it. Other browsers cannot steal an already-bound slot unless
   the first one releases it (soft lock: "kick?" prompt).
3. Every human's `/play` shows the same cockpit but with a new
   **Team panel**:
   * Roster with status (current sector, turns left today, credits,
     copilot mode, "speaking/typing" indicator).
   * Team chat channel — text only, fast, everyone's by default.
   * "Relay to team" toggle on the copilot chat so one player's
     natural-language request (e.g. "meet me at sector 88") can be
     shared as a read-only note in everyone else's feed.
4. Voice is **per-slot**. Each browser tab listens to its own mic and
   transmits to its own copilot. Cross-slot voice chat is optional and
   deferred to a later phase (WebRTC is significantly more work than
   WebSocket text relay).

## Engine + scheduler

The engine is already multi-human-ready:

* `agent_kind="human"` creates a `HumanAgent` that submits actions via
  `/api/human/action`.
* `MatchScheduler` rotates through all agents in order; human slots
  just block on `await agent.act(obs)` while the rest of the turns
  continue (off-turn submissions queue).

Deltas needed:

* **Per-slot presence tracking.** `runner.state` gains a
  `dict[str, SlotBinding]` keyed by player_id, carrying the WS
  connection id + last-heartbeat-ts. The `/api/match/humans` response
  surfaces `bound_by: "<client_id>" | null`, `last_seen_s_ago: int`.
* **Soft lock.** New endpoint `POST /api/human/claim` returns
  `{ ok: true, token }` when the slot is free; the `/play` page sends
  that token back on every state read as a session cookie. Mismatch →
  402 Payment Required (jokingly; really 409).
* **Release / takeover.** `POST /api/human/release`, and
  `POST /api/human/kick` (the already-bound client gets a WS message
  `{ kind: "kicked" }` and the new client takes over). This is the
  same pattern Star Citizen / Colyseus use.

## Voice & copilot scaling

* **Per-slot `CopilotSession`** is already the design; no work here.
* **Cross-slot broadcast.** A new copilot mode or command
  `team broadcast: "..."` sends a chat event to the other sessions'
  feeds (rendered as read-only "P1 said: …" entries). Memory is NOT
  shared — each human keeps their own prefs.
* **Always-on listener collision.** In `autopilot` mode we currently
  run a `SpeechRecognition` instance listening for interrupt words.
  With two browsers on the same machine that creates mic contention.
  Mitigations:
  * Detect multiple concurrent instances via `BroadcastChannel`; if
    two tabs bind different slots on the same machine, only one keeps
    the always-on listener active (the one with focus / the most
    recent interaction).
  * Document: "for two human seats at the same desk, use one browser
    tab and alt-tab between headsets."
* **Shared-observer WS channel.** The existing `/ws` already
  multicasts engine events to everyone. We add
  `/ws?player_id=P1&team=true` so players opt into a per-team sub-feed
  carrying the relay messages above.

## UI sketch

```
┌──────────────────── cockpit ──────────────────────┐
│ ┌─ slot picker (top banner) ─────────────────┐   │
│ │ You are P2 · Team: P1 Alice (s42) ·        │   │
│ │ P3 waiting · P4 waiting · [swap slot]      │   │
│ └────────────────────────────────────────────┘   │
│                                                   │
│ ┌─ action panel ─┐  ┌─ copilot panel ─────────┐   │
│ │ ...            │  │ ...                     │   │
│ └────────────────┘  └─────────────────────────┘   │
│                                                   │
│ ┌─ team panel (new) ───────────────────────────┐  │
│ │ Roster: P1 s42 15c 2200c · P3 s101 0c 5000c  │  │
│ │ Chat: [P1 said] meet at 88?                  │  │
│ │       [me]     on my way                     │  │
│ │ [type here…]  [ ] relay my copilot replies   │  │
│ └──────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
```

New endpoints:

* `GET  /api/match/slots` — roster summary (public, cachable).
* `POST /api/human/claim { player_id }` → `{ token }`.
* `POST /api/human/release` (body carries token).
* `POST /api/team/chat { player_id, text, kind: "chat"|"relay" }`.
* `GET  /api/team/chat/history?limit=50` — paginated.

New WS events:

* `team_chat` — relayed text chat.
* `team_roster` — periodic (every 2s) roster updates.
* `slot_bound` / `slot_released` / `slot_kicked`.

## Copilot changes

* `CopilotRegistry.broadcast_to_team(from_player, message)` — writes
  an ephemeral `CopilotMessage { role: "relay", from_player, text }`
  into every other session's chat feed. No memory updates. No
  auto-act on other sessions (privacy).
* New tool `team_broadcast(message)` with a strict character cap and a
  1-per-5-second rate limit, gated behind advisory+ mode (so manual
  players can't accidentally spam teammates).
* Safety: team relays are **never** executed as actions on other
  sessions. They're read-only UI events. Any autopilot logic that
  wanted to follow up would still need the recipient's explicit
  confirmation.

## Scheduler fairness under latency

Current round-robin waits indefinitely for a human slot to submit. In
team play this becomes a DoS vector: if P1 AFKs at turn start, P2-P4
block for minutes until P1 times out. Mitigations:

* Per-slot turn timer, default 60s, surfaced in the roster as a
  progress bar.
* On timeout, auto-insert a `wait` action and advance. Configurable
  via `MatchSpec.human_turn_timeout_s`.
* Timed-out slot gets a "your turn was skipped" toast next time they
  submit; no stat penalty.

## Testing strategy

* Scheduler stress: 4-human match with scripted `submit_action`
  injections from four `HumanAgent` stubs; assert no deadlock, all
  turns advance.
* Claim/release: two clients race for `/api/human/claim P1`; assert
  only one wins and the loser gets 409.
* Team chat: broadcast from session A lands in session B's WS feed
  within 500ms end-to-end.
* Copilot isolation: `remember` on P1 does NOT appear in P2's memory
  snapshot.

## Milestones

| Step | Description | Estimated effort |
|---|---|---|
| H6.5.a | Slot picker + claim/release/kick endpoints, cookie session, docs | Medium |
| H6.5.b | Team chat relay (text only), WS sub-channel, team panel UI | Medium |
| H6.5.c | Per-slot turn timers + auto-wait | Small |
| H6.5.d | Copilot `team_broadcast` tool with safety gating | Small |
| H6.5.e | Voice-channel collision detection (BroadcastChannel) | Small |
| H6.5.f (deferred) | WebRTC voice channel between humans | Large |

Total ship: 2-3 days without WebRTC. WebRTC adds another 3-5 days and
changes the ops profile (STUN/TURN servers, NAT traversal), which is
why it's carved off as a separate phase.

## Open questions

* **Persistent accounts?** Right now a human slot is just a `P1`…`PN`
  string. To stabilise "Alice always plays P2" across match restarts
  we'd need a lightweight account layer (magic-link email or
  passphrase). Probably not needed for round-1 multiplayer.
* **Cooperative vs adversarial?** Corporations already exist in the
  engine (`player.corp_ticker`); team chat should respect corp
  membership by default (your corp sees your relays, others don't).
  Spectator `/` keeps seeing everyone's public actions as today.
* **Moderation.** Any public chat feature needs a kick/mute path for
  abuse. For a self-hosted tool this is low priority but should be
  considered before a public demo server is stood up.
