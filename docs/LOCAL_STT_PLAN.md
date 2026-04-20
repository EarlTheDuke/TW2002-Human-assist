# Local speech-to-text plan (Phase H6.2)

> Status: **PLAN ONLY**. No runtime code yet. Checked-in so the next
> implementation pass has a concrete target.
> Last updated: 2026-04-20.

## Why this exists

Phase H3 shipped push-to-talk voice via the browser's `SpeechRecognition`
Web Speech API. On Chrome that endpoint calls out to Google's cloud
service — which is free for prototypes but leaks every utterance off the
user's machine, dies the moment the browser goes offline, and has no
tuning knobs for game-specific jargon ("warp to Terra", "scan port
class 8", "BBS", "FedSpace", sector numbers like "forty-two thousand
six hundred").

H6.2 replaces that cloud hop with a **local STT engine** the user can
run on their own box. Benefits:

* **Privacy** — voice never leaves the machine.
* **Offline-capable** — works on a plane, on a flaky connection, or in a
  permissions-restricted browser.
* **Vocabulary biasing** — we can feed the decoder a fixed list of
  sectors, commodities, and copilot keywords so "warp to forty two" is
  recognised as "warp to 42" without a round-trip through ChatGPT to
  clean it up later.
* **Latency floor** — typical real-time-factor (RTF) of 0.1x on CPU for
  small models means a 3-second utterance transcribes in ~300ms, which
  is faster than the current cloud round-trip under typical network
  jitter.

## Engine comparison

| Engine | Language | Perf (tiny/base) | Pkging | Vocab biasing | Notes |
|---|---|---|---|---|---|
| **[`faster-whisper`](https://github.com/SYSTRAN/faster-whisper)** | Python | RTF ~0.1x CPU, <0.02x CUDA | `pip install faster-whisper` | Via `initial_prompt` + `hotwords` | CTranslate2 backend, int8/fp16, multilingual. **Recommended.** |
| **[`whisper.cpp`](https://github.com/ggerganov/whisper.cpp)** | C/C++ | RTF ~0.15x CPU | Binary + py wrapper (`pywhispercpp`) | Via grammar-based sampling (`--grammar`) | Extremely portable, runs on a Pi. Adds a compile step. |
| **[`Vosk`](https://alphacephei.com/vosk/)** | Kaldi+Python | RTF ~0.3x CPU, streaming | `pip install vosk` | Via runtime grammar list | True streaming (partials) out of the box. Accuracy a step below Whisper on general speech. |
| Browser WebGPU (`whisper-webgpu`) | JS/WASM | RTF ~0.2-0.4x on modern GPU | Bundled in page | Via prompt | No server round-trip needed; bigger download (~80MB), spotty Safari/Firefox support. |

### Recommendation: **`faster-whisper`**

Why:

1. Matches the accuracy of OpenAI Whisper (it IS Whisper, just a faster
   runtime) — demonstrably better than Vosk on short command-style
   utterances with numbers.
2. Pure `pip install` on Windows / macOS / Linux. Users already have
   Python 3.11 from TW2K install.
3. `initial_prompt` takes a plain-English bias string, which maps 1:1
   to the vocabulary we want to boost.
4. Int8 models on CPU: tiny.en = ~40MB, base.en = ~75MB, small.en =
   ~240MB. All three run realtime on a mid-range laptop.
5. Same engine ships across desktop and eventually mobile PWA
   (CTranslate2 has WASM builds in progress), so we don't rewrite the
   client twice.

Runner-ups:

* **whisper.cpp** if we want a truly static single-binary distribution
  for a non-Python user. Revisit if we ever ship a "just double-click"
  installer.
* **Vosk** for streaming partials if the UX becomes "show a running
  transcript while the user is still speaking" and push-to-talk isn't
  responsive enough. Current H3 push-to-talk is "speak → release →
  transcribe" which Whisper handles fine without streaming.

## Architecture

```
┌────────────────────────┐      WS: /ws/stt      ┌───────────────────────┐
│ Browser (play.js)      │ ──── pcm frames ───►  │ FastAPI stt_ws        │
│ ────────────────────── │                       │ ─────────────────────│
│ MediaRecorder (16kHz)  │ ◄── json {partial,    │ faster_whisper.       │
│ push-to-talk button    │      final, text}     │   WhisperModel.       │
│ or continuous autopilot│                       │   transcribe(pcm)     │
│                        │                       │                       │
│ falls back to          │                       │ hotwords from         │
│ Web Speech API if STT  │                       │ build_bias_prompt()   │
│ server not configured  │                       │                       │
└────────────────────────┘                       └───────────────────────┘
```

### Server side — new module `src/tw2k/stt/server.py`

```python
class LocalSttServer:
    model: WhisperModel
    def __init__(self, *, model_size="base.en", device="auto", ...): ...
    async def transcribe(
        self, pcm: bytes, *, hotwords: Sequence[str] | None = None
    ) -> SttResult: ...
```

* One `WhisperModel` loaded at process start (ffi call is ~1s), then
  shared across all WebSocket connections via an `asyncio.Semaphore`
  whose concurrency is pinned to `CTRANSLATE2_CPU_THREADS or 1` — keeps
  GIL contention predictable.
* Input frames are 16-bit mono PCM at 16kHz, the canonical Whisper
  input. Browser-side conversion described below.

### WebSocket endpoint — `GET /ws/stt?player_id=P1`

Lifecycle:

1. Client opens WS, sends one JSON handshake frame:
   `{ "op": "start", "lang": "en", "hotwords": ["warp","sector 42",...] }`
2. Client streams binary PCM frames (ArrayBuffer) as it records.
3. Client sends JSON `{ "op": "stop" }` on push-to-talk release.
4. Server concatenates the buffered frames, runs
   `model.transcribe(..., initial_prompt=..., vad_filter=True)`, and
   replies with `{ "op": "final", "text": "..." }`.
5. For streaming partials (future work), the server can re-run every
   400ms on the growing buffer and emit `{ "op": "partial", text }`.

### Hotword / prompt construction

A tiny helper already exists as `build_voice_grammar_hint()` in
`web/play.js`; we lift it server-side into
`src/tw2k/stt/hotwords.py::build_prompt(observation, memory)`:

* Sector numbers in `observation.adjacent`, `observation.known_ports`,
  `observation.self.sector_id` — every number the user is likely to
  say right now.
* Commodity names (`fuel ore`, `organics`, `equipment`).
* Port classes (`BBS`, `SBB`, `BSB`, etc.) spelled out phonetically.
* Copilot modes (`manual`, `advisory`, `delegated`, `autopilot`).
* Interrupt words (`stop`, `hold`, `pause`, `cancel`).
* Memory keys the player has personally stored (`favorite commodity`,
  `route to Alpha Centauri`, …).

Whisper's `initial_prompt` is capped at ~224 tokens, so we truncate to
the 50 most likely terms using an observation-local heuristic.

### Client side — `web/play.js`

A new `STT` module behind a feature flag:

```js
const sttMode = localStorage.getItem("tw2k_stt_mode") || "web-speech";
// "web-speech" | "local-ws" | "auto"
```

* `auto` probes `GET /api/stt/info` on page load — returns
  `{ available: true, model: "base.en", sample_rate: 16000 }` when the
  local server is running, else `{ available: false }`.
* When local is chosen, push-to-talk opens `MediaRecorder` with
  `{ mimeType: "audio/webm;codecs=opus" }` and pipes decoded PCM
  frames over `/ws/stt`. We do the decode in-browser via
  `AudioContext.decodeAudioData` so the server only sees Whisper-ready
  PCM (no ffmpeg dep on the server box).
* Fallback to Web Speech API is unchanged when local is not configured
  — guarantees the feature doesn't regress for existing users.

### CLI + config

New optional CLI command:

```
tw2k stt-serve --model base.en --device auto --host 127.0.0.1 --port 8001
```

…but the likely default is to run it inside the same `tw2k serve`
process, guarded by `--enable-local-stt`. That keeps the cockpit a
single-port experience.

New `pyproject.toml` extra:

```toml
[project.optional-dependencies]
stt = [
  "faster-whisper>=1.0",
  "numpy>=1.26",
]
```

Opt-in: `pip install "tw2k-ai[stt]"`.

### UX copy for settings panel

Tiny three-way radio in the cockpit voice-settings popover:

* Browser (Google) — default, cloud.
* Local Whisper — recommended, private.
* Off — push-to-talk disabled.

### Testing strategy

* Unit: `build_prompt()` snapshot tests across representative
  observation fixtures (same pattern as `test_prompts.py`).
* Integration: `test_stt_ws_loopback.py` — spin up the FastAPI app
  with a stubbed `LocalSttServer` that returns canned transcripts,
  drive the WebSocket from an `httpx.ASGITransport` client, assert the
  chat endpoint receives the expected utterance.
* Real-model smoke (opt-in via `TW2K_REAL_STT=1`): pipe a checked-in
  16kHz WAV clip ("warp to sector 42") through the real model and
  assert `"warp"` + `"42"` appear in the transcript. Skipped in CI
  unless the marker is set, because model download is slow.

### Open questions deferred to implementation

* GPU detection on Windows — `faster-whisper` uses CUDA 12 by default;
  fallback path for AMD / Apple Silicon users needs a smoke pass.
* Model caching directory — settle on `~/.cache/tw2k/models/` or honour
  `HF_HOME` if set (most folks already have it for transformers).
* Encrypted microphone permissions on macOS Sonoma — the system hooks
  are per-app, so the user will see a one-time dialog the first time
  the server process touches the mic. Document it.
* Combining local STT with the existing **autopilot always-on listener**
  (H4) — probably want to keep Web Speech for the lightweight
  interrupt-word detector (it returns partials incrementally) and use
  local Whisper only for deliberate push-to-talk, so we don't pay
  60x/minute for 0.5-second "was that a stop word?" wake-word checks.

## Milestones

| Step | Description | Estimated effort |
|---|---|---|
| H6.2.a | Add `stt` optional dep, scaffold `src/tw2k/stt/` with `LocalSttServer` + `build_prompt`, unit tests with stub model | Small |
| H6.2.b | `/ws/stt` WebSocket + `/api/stt/info`, browser-side PCM conversion, settings radio | Medium |
| H6.2.c | Real-model smoke test, model-download UX, docs | Small |
| H6.2.d | Streaming partials (`op: "partial"`) using incremental transcribe calls | Medium (deferred) |

Total: 1-2 days of implementation once we greenlight. The plan
deliberately stays under the axis where local Whisper runs fast enough
to be "felt instant" on mainstream hardware; if we ever need sub-100ms
latency we revisit **Vosk** or a streaming Whisper fork.
