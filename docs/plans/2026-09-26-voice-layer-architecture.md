# Voice layer architecture — thin shell over an existing tool-calling agent

**Date:** 2026-09-26  
**Audience:** Ben’s product/dev team (shareable brief)  
**Scope:** Rebuild of the “Claw / Jarvis” pattern on **xAI Grok** — voice in, tools unchanged, voice out.  
**Repo note:** Starter code lives under `voice/` as an **isolated module**. It does not modify TW2K game code, `/bot`, or seat-bot plans.

---

## 1. Goal

Let a human talk to an existing tool-calling agent with **phone-call feel**:

- Hear the first syllable of the reply in **under ~800 ms** after they stop speaking (or on barge-in endpoint).
- Keep the **same tools** the text agent already has (calendar, repo, TW2K harness, email drafts, etc.).
- Treat voice as a **transport**, not a second brain.

One developer can ship a weekend MVP because the tool loop already exists; the new work is STT ↔ stream ↔ TTS plumbing and UX.

---

## 2. Three-piece loop (with overlap)

```
  Mic PCM ──► STT (partial + final) ──► Grok (stream tokens + tool calls) ──► TTS (stream audio) ──► Speaker
                 │                              │                                  │
                 │                              ├── tool_call ──► existing tools ──┤
                 │                              │         tool_result ─────────────┘
                 └──── live transcript UI ──────┴──── transcript / status UI ──────┘
```

**Overlap (why it feels fast):**

1. **STT** emits partial transcripts while the user is still talking (optional barge-in / end-of-utterance).
2. As soon as the utterance is final (or high-confidence end), start the **Grok** chat/completions stream with tools enabled.
3. As soon as Grok emits the first **speakable** text chunk (after any tool round-trips, or from early tokens if no tools), start **TTS** and play the first audio frame **before** the full model response finishes.
4. Later tokens keep feeding TTS; tool calls pause speech, run tools, then resume streaming speech on the continuation.

First-audio latency is dominated by: end-of-speech detection + STT finalization + TTFT (Grok) + TTS time-to-first-byte — not by waiting for the full answer.

---

## 3. Recommended providers (and why)

| Role | Primary | Why | Fallback |
|------|---------|-----|----------|
| **Brain** | **xAI Grok** (chat completions, streaming, tool/function calling) | Matches Ben’s stack; strong tool use; one API key path with existing agents | Keep tool schemas identical so swapping models later is config |
| **TTS** | **Cartesia** (streaming) or **ElevenLabs** (streaming) | Low TTFB, natural voice, chunked PCM/μ-law over WS/HTTP | Browser `speechSynthesis` only for demos (high latency, poor control) |
| **STT** | **Deepgram** (streaming) or **OpenAI Whisper** (batch / realtime where available) | Deepgram for sub-second partials; Whisper for quality / offline experiments | Web Speech API for zero-key prototypes only |

**Principle:** pick streaming endpoints everywhere. Batch “record whole utterance → one Whisper call → one Grok call → one TTS file” will miss the <800 ms budget.

---

## 4. Voice as a thin shell

```
┌─────────────────────────────────────────┐
│  voice/ (this module)                   │
│  browser mic + WS + STT + TTS playback  │
└──────────────────┬──────────────────────┘
                   │ text + tool_calls (same JSON schemas)
┌──────────────────▼──────────────────────┐
│  Existing agent / tool registry         │
│  (Claw tools, Grok Bot tools, TW2K…)    │
│  UNCHANGED implementations              │
└─────────────────────────────────────────┘
```

- The voice server **does not** reimplement business logic.
- It registers the **same tool definitions** the text agent uses (TODO hooks in `voice/server.py`).
- Auth, rate limits, and side-effect policy stay with the tool layer (e.g. draft email, don’t auto-send).

---

## 5. Latency budget (<800 ms first audio)

Rough target breakdown after end-of-utterance:

| Stage | Budget |
|-------|--------|
| STT finalize / endpoint | 100–200 ms |
| Grok time-to-first-token | 200–400 ms |
| TTS time-to-first-byte | 100–200 ms |
| Network / jitter buffer | ~50–100 ms |
| **Sum** | **~500–800 ms** |

**Levers:** streaming STT with eager endpointing; small “filler” or immediate ack only if product wants it (optional); flush TTS on sentence boundaries; keep tool round-trips minimal on the critical path (or speak a short “working on that” only when a tool will take >1 s).

---

## 6. Security

- **No raw audio retention** by default: process in memory / ephemeral WS frames; do not write WAV/MP3 to disk in MVP.
- **Transcripts:** optional short-lived in-memory ring buffer for the session; redact before any log ship.
- **Keys:** `XAI_API_KEY`, TTS key, STT key only in env / secret store — never in git (see `voice/.env.example`).
- **Browser:** serve over localhost or HTTPS; mic requires a secure context.
- **Tools:** voice channel inherits the same confirmation rules as text (no “spoken send” bypass).

---

## 7. Sequence — one turn (text diagram)

```
User                 Browser              Voice server           STT         Grok          TTS         Tools
 |                      |                      |                  |            |            |           |
 |-- hold mic --------->|                      |                  |            |            |           |
 |   PCM frames ------->|---------- WS ------->|----------------->|            |            |           |
 |                      |<-- partial text -----|<-- partial ------|            |            |           |
 |-- release / EOU ---->|                      |                  |            |            |           |
 |                      |                      |<-- final text ---|            |            |           |
 |                      |<-- final transcript -|                  |            |            |           |
 |                      |                      |--- stream chat + tools ------>|            |           |
 |                      |                      |                  |  tool_call |            |           |
 |                      |                      |------------------------------------------->| run      |
 |                      |                      |<-------------------------------------------| result   |
 |                      |                      |--- continue stream ---------->|            |           |
 |                      |                      |  tokens ----------------------|----------->|           |
 |                      |<-- audio chunks ------|<-----------------------------|-- PCM -----|           |
 |<-- play audio -------|                      |                  |            |            |           |
 |                      |<-- more audio / done -|                  |            |            |           |
```

---

## 8. Weekend MVP (one developer)

**Already exists:** tool-calling agent + schemas.  
**Build:**

1. `voice/index.html` — mic capture, WS, transcript, `<audio>` / AudioWorklet playback.  
2. `voice/server.py` — WS hub, STT stream, Grok stream + tool loop stubs, TTS stream.  
3. Wire **one** real tool (e.g. `get_time` or an existing Claw tool) end-to-end.  
4. Measure time from mic-up to first audible sample; tune endpointing.

**Out of scope for weekend:** multi-room, long-term audio archive, fine voice cloning, TW2K `/bot` integration (separate track).

---

---

## 9. Remote access (desk, conference room, phone)

Run the **voice server on the Claw host** (or another machine on the same floor / subnet as the tools). STT, Grok, and TTS stay co-located with the tool registry so tool round-trips never hairpin across the internet.

Every other device is a **browser-only thin client**:

- Desk PC, conference-room machine, or phone opens the hosted `voice/` page (same idea as opening hosted `/bot`).
- Reach it through the **existing tunnel pattern** already used for TW2K: localhost.run / Cloudflare quick tunnel, Tailscale, or an internal HTTPS URL — see `docs/HOSTING_GROKBOT.md` for the operational playbook.
- **Only compressed audio** (and small JSON control/transcript frames) crosses the network: mic uplink + TTS downlink. The heavy loop (STT decode, Grok + tools, TTS synthesize) never leaves the host's floor, which keeps the &lt;800 ms first-audio budget realistic.

```
  Phone / desk / conf PC          Tunnel / Tailscale           Claw host (same floor as tools)
  [browser mic + speaker] ----->  https://.../ or ts.net -----> voice/server.py
       compressed audio <------------------------------------- STT -> Grok -> tools -> TTS
```

### Securing the tunnel

- Prefer **private** reachability (Tailscale / LAN) over a semi-public quick tunnel when Claw tools can take real actions.
- If a public tunnel is required, gate with **token auth** (bearer or one-time session token on connect) — same spirit as harness seat tokens / spectator tokens on `/bot`. Do **not** expose Claw tool endpoints directly on the public URL; only the voice WS + static UI should be reachable, and the server alone holds tool credentials.
- Rotate tunnel URLs and tokens after demos; never commit `.env` keys or tunnel URLs.
- Mic still requires a **secure context** (HTTPS or localhost) in the browser.


## 10. Section index

1. Goal  
2. Three-piece loop (with overlap)  
3. Recommended providers  
4. Voice as a thin shell  
5. Latency budget  
6. Security  
7. Sequence diagram  
8. Weekend MVP  
9. Remote access  
**Companion code:** `voice/README.md`, `voice/server.py`, `voice/index.html`, `voice/requirements.txt`, `voice/.env.example`.
