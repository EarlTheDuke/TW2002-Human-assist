# TW2K viewport clips: production plan (planning only)

**Date:** 2026-09-26 PT. **Author:** Grok Bot for Ben. **Status:** PLAN ONLY. No videos generated, no paid API calls made.
**Companion:** `PHASE_PLAN.md` (cockpit viewport, manifest v2, phases V0–V8).
**Research date:** every price and feature below was read from the cited page on 2026-09-26 unless marked otherwise. **UNVERIFIED** means I couldn't confirm it on a primary (vendor) page. Prices change, so re-check before any spend.

---

## 1. What we need to produce

- **Pilot set (PHASE_PLAN V3):** 14 clips. 2 ambient loops (8 s, seamless), 3 dock, 3 warp, 2 attack-hit, 2 attack-miss, 2 incoming-fire. Event clips end up 2–4 s long after trimming.
- **Base library v1:** the pruned variable matrix for dock/warp/combat/ambient (§6.1), about 48 clips.
- **Later waves:** StarDock, weapons, planets/Genesis, landing/liftoff, ship purchase, death/escape pod, and so on (about 70 more clips).
- **Live custom moments (optional):** generated on demand in the background (§8).

Non-negotiables that come from the cockpit: consistent art direction across every clip (same universe, lighting, palette, same camera "window" point of view), silent 16:9 clips at ≤540p for delivery, first-frame posters, loops that are seamless, fog-safe content, and **no dependence on generation speed for gameplay**.

## 2. Tool research (2026-09-26)

### 2.1 xAI Grok Imagine (primary candidate)

| Item | Finding | Source |
|---|---|---|
| Models | `grok-imagine-video-1.5` (aliases `-preview`, `-2026-05-30`; the recommended video model) and classic `grok-imagine-video`. Images: `grok-imagine-image-2.0`, `grok-imagine-image-quality`, `grok-imagine-image`. | https://docs.x.ai/docs/models , https://docs.x.ai/developers/models/grok-imagine-video-1.5 |
| Endpoints | `POST https://api.x.ai/v1/videos/generations` → `{request_id}`; poll `GET /v1/videos/{request_id}` → `status: pending/done/expired/failed`, `video.url`. Edit: `/v1/videos/edits`. Extend: `/v1/videos/extensions`. Images: `/v1/images/generations`, `/v1/images/edits`. Python `xai_sdk` and Vercel AI SDK are supported. | https://docs.x.ai/developers/model-capabilities/video/generation , https://docs.x.ai/docs/guides/video-generations |
| Duration / resolution / aspect | 1–15 s. `480p` (default), `720p`, `1080p` (1080p only on 1.5 for text/image-to-video; **reference-to-video is capped at 720p**). Aspect 16:9 (default), 9:16, 1:1, 4:3, 3:4, 3:2, 2:3. Image-to-video defaults to the input image's aspect. | video generation doc (above) |
| Consistency features | **Image-to-video** (the image becomes the first frame). **Reference-to-video** (`reference_images`, which guide the subject without locking frame 1). **First & last frame pin** (`image` + `last_frame`: interpolate between two exact frames, which makes perfect seamless loops when first = last). **Keyframes** (up to 4 interior pins on a 1/3 s grid). Video edit and extend. Up to 5 source images for image edits. Classic `grok-imagine-video` rejects `last_frame`, `keyframes`, and image+reference combos. No `seed` parameter is documented (**UNVERIFIED** whether one exists). | https://docs.x.ai/developers/model-capabilities/video/reference-to-video |
| Max reference images | "one or more" in xAI docs. fal's listing says 1–7 (**secondary source, UNVERIFIED on docs.x.ai**). | https://fal.ai/models/xai/grok-imagine-video/v1.5/image-to-video |
| Audio | Audio track by default. `generate_audio: false` gives silent output (documented for 1.5). Whether silent output changes the price is **UNVERIFIED**. | video generation doc |
| Price, 1.5 | xAI docs: **$0.080/sec** (model page; x.ai/api says "480p/720p/1080p from $0.08/sec"). Image input **$0.01/img**. Per-resolution split **$0.08 (480p) / $0.14 (720p) / $0.25 (1080p) per sec** comes from secondary sources (fal, ofox, wavespeed, creeta), **not confirmed on a docs.x.ai page I could read. Treat 720p/1080p as UNVERIFIED-secondary.** | https://docs.x.ai/developers/pricing , https://x.ai/api , fal / https://ofox.ai/blog/grok-imagine-video-api-pricing-by-resolution/ |
| Price, classic | **$0.05/sec 480p, $0.07/sec 720p**. Image input $0.002/img, video input $0.01/sec. | https://x.ai/api (pricing table) |
| Image prices | image-2.0 $0.04/img, image-quality $0.05, image $0.02. | https://docs.x.ai/developers/pricing |
| Rate limits | 10 requests/sec for both video models. Batch API is supported (media is billed at standard rate, no discount). Regions us-east-1, us-west-2. | model pages above, pricing page |
| Turnaround | "typically takes up to several minutes". SDK default poll timeout 10 min. **No p50/p90 published (UNVERIFIED).** Output URLs are **temporary**, so download immediately. | video generation doc |
| Moderation cost | "When your request is deemed to be in violation … we will still charge for the generation." That matters for combat/explosion prompts: keep violence stylized and vehicle-only. | pricing page |
| Licensing | Enterprise API terms: Customer "owns all right, title, and interest in the Output … SpaceXAI hereby assigns to Customer". SpaceXAI "will not use any User Content to train". Consumer terms add attribution/brand guidelines when using xAI marks. | https://x.ai/legal/terms-of-service-enterprise , https://x.ai/legal/terms-of-service |
| Quality | Vendor page claims #1 on the Artificial Analysis text-to-video ranking (vendor-cited, dated 2026-01-28). **Not independently verified**; the lookdev bake-off (§10) will judge. | https://x.ai/api/imagine |

### 2.2 Runway (API "Runway Dev")

| Item | Finding | Source |
|---|---|---|
| Models | `gen4.5`, `gen4_turbo`, `aleph2`, plus third-party models on the same API: `veo3.1`, `veo3.1_fast`, **`grok_imagine_1_5`**, `seedance2*`, `hailuo3`, `wan3`, `gemini_omni_flash`, and others. Image models include `gen4_image` (with references). | https://docs.dev.runwayml.com/guides/models/ |
| Endpoints | `POST https://api.dev.runwayml.com/v1/image_to_video` / `text_to_video`, header `X-Runway-Version: 2024-11-06`, task polling. `promptImage` can be `[{uri, position: first\|last}]` (first/last frame), or use a `references` array (the two modes are mutually exclusive, per Runway's own skill doc). | https://docs.dev.runwayml.com/guides/using-the-api/ , https://github.com/runwayml/skills/blob/main/skills/rw-api-reference/SKILL.md |
| Duration / res | Gen-4.5: 2–10 s (changelog). Ratios are pixel-based, e.g. `1280:720`. | https://docs.dev.runwayml.com/api-details/api_changelog/ |
| Price | $0.01/credit. **gen4.5 = 12 credits/s ($0.12/s)**, gen4_turbo = 5 ($0.05/s, image required), `grok_imagine_1_5` 720p = 16 ($0.16/s) + 1/ref, veo3.1_fast no-audio = 10 ($0.10/s), `gen4_image` 5–8 credits/img. | https://docs.dev.runwayml.com/guides/pricing/ |
| Rate limits | Tiered concurrency: Tier 1 = 1 concurrent video / 50 per day; Tier 2 (after $50 purchase) = 3 / 500; Tier 3 (after $100) = 5 / 1,000. Over-concurrency tasks queue as `THROTTLED`. No RPM limit. | https://docs.dev.runwayml.com/usage/tiers/ |
| Turnaround | Tier doc's worked example *assumes* ~15 s per video "using some approximations". **Not an SLA; real latency UNVERIFIED.** | tiers page |
| Licensing | "does not claim ownership of any of your Inputs or Outputs … does not restrict your commercial use of your Outputs". **But** Inputs and Outputs "may be used by the Company to train and improve its AI models" (broad license back). | https://runway.com/terms-of-use , https://help.runwayml.com/hc/en-us/articles/18927776141715-Usage-rights |

### 2.3 Google Veo 3.1 (Gemini API)

| Item | Finding | Source |
|---|---|---|
| Models | `veo-3.1-generate-preview`, `veo-3.1-fast-generate-preview`, `veo-3.1-lite-generate-preview` | https://ai.google.dev/gemini-api/docs/pricing |
| Price (paid tier, audio always on) | Standard **$0.40/s** (720p/1080p). Fast **$0.10/s 720p**, $0.12 1080p. Lite **$0.05/s 720p**, $0.08 1080p. Charged only on success. Paid-tier data is "not used to improve our products". | pricing page |
| Duration | 4, 6, or 8 s. **Must be 8 s with reference images, extension, 1080p or 4k.** | https://ai.google.dev/gemini-api/docs/veo |
| Consistency | Up to **3 reference images** (Veo 3.1 only), first + last frame (`lastFrame`), extension (+7 s up to 20×, 720p only), `seed` "doesn't guarantee determinism, but slightly improves it". Whether Lite supports reference images is **UNVERIFIED**. | veo doc |
| Turnaround | **Documented: min 11 s, max 6 min at peak.** | veo doc |
| Other | SynthID invisible watermark. Server keeps videos for 2 days. Audio always generated (we'd strip it). | veo doc |
| Licensing | "Google won't claim ownership over that content … Google may generate the same or similar content for others". | https://ai.google.dev/gemini-api/terms |
| Rate limits | Not read (**UNVERIFIED**). | — |

### 2.4 Kling (Kling AI Open Platform)

| Item | Finding | Source |
|---|---|---|
| Models | Kling 3.0 Turbo, 3.0, 3.0 Omni, O1, 2.6, 2.5 Turbo | https://kling.ai/document-api/guides/capability-map/video.md |
| Duration / res | 3–15 s. 720p/1080p (4K on 3.0/Omni) | capability map |
| Consistency | First/last frame (3.0, Omni; **not Turbo**). **Element Control** (multi-image subject elements: a frontal image plus 1–3 more views, referenced as `@id` in prompts) on 3.0/Omni. Multi-shot. | capability map; https://dev.pika.art/llms/kling/kling-3.0/omni-video (element fields) |
| Price | Unit-based, 1 unit = $0.14 list, **requires buying a unit package**. Kling 3.0 no-audio **$0.084/s 720p**, $0.112/s 1080p. With audio $0.126/s 720p. | https://kling.ai/document-api/pricing/base/video.md |
| Turnaround / rate limits | **UNVERIFIED** | — |
| Licensing | API paid-service terms: IP in output belongs to you if you hold input rights; "use of the AI-generated content for commercial purposes is not restricted". (Consumer terms differ: attribution needed for non-members.) | https://d7umqicpi7263.cloudfront.net/eula/bnnS6kHpgYZjD9bEjd9jvcq1ySl-XxS7ST1-H_YGHec , https://kling.ai/docs/user-policy |

### 2.5 Luma (Agents API, `ray-3.2`)

| Item | Finding | Source |
|---|---|---|
| Features | Text/image-to-video with `start_frame`/`end_frame`, multi-keyframe (up to 64 anchors), edit, extend, reframe, **native `video.loop`** (seamless loop), HDR/EXR. 540p/720p/1080p, **5 s or 10 s** only. | https://docs.agents.lumalabs.ai/guides/model/index.md |
| Price | `type: video` 720p **$0.30 per 5 s** (= $0.06/s), $0.90 per 10 s; 540p $0.15/5 s; 1080p $1.20/5 s. | https://docs.agents.lumalabs.ai/guides/pricing |
| Subject reference images | **UNVERIFIED** (not seen in the pages I read) | — |
| Turnaround / rate limits / licensing | **UNVERIFIED** (not read) | — |
| Note | Luma's newest Ray3.14 is web-only, not on the API (per their FAQ). | https://lumalabs.ai/learning-hub/ray3-faq |

### 2.6 Pika
Pika's developer platform (`dev.pika.art`) lists **Kling 3.0 Omni** as a resold model ($0.068/s 720p no audio on its page). I did **not** assess Pika's own models, pricing, or terms (**UNVERIFIED**, out of scope).

### 2.7 Comparison (720p unless noted; pilot-relevant features)

| | xAI Grok Imagine 1.5 | Runway Dev (gen4.5) | Google Veo 3.1 Fast | Kling 3.0 | Luma ray-3.2 |
|---|---|---|---|---|---|
| Quality | Vendor claims top rank (unverified); judge in bake-off | Unverified; bake-off | Unverified; bake-off | Unverified; bake-off | Unverified; bake-off |
| Same ship / style tools | Image-to-video, reference-to-video, **first+last frame**, 4 keyframes, edit/extend | First/last frame **or** references; `gen4_image` refs for stills | ≤3 refs (forces 8 s), first+last, seed (weak) | Elements (multi-view subject), first/last | Start/end frame, 64 keyframes, **native loop** |
| Seamless loop | Yes (first = last pin) | Yes (first/last) | Yes (first/last) | Yes (first/last) | Yes (`loop`) |
| $/s | $0.08 (480p, docs); $0.14 (720p, secondary) | $0.12 | $0.10 (audio always on) | $0.084 (package) | $0.06 (5 s blocks) |
| Clip length | 1–15 s, any integer | 2–10 s | 4/6/8 s (8 with refs) | 3–15 s | 5 or 10 s |
| Turnaround | "up to several minutes" (docs) | ~15 s example (not an SLA) | 11 s–6 min (docs) | Unverified | Unverified |
| API / limits | REST+SDK, 10 RPS | REST+SDK, tiered concurrency, auto-queue | REST+SDK, limits unverified | REST, packages | REST, limits unverified |
| Commercial / ownership | Assigned to customer (enterprise terms); no training | Yours, commercial OK; **Runway may train on I/O** | Google won't claim ownership; paid tier not used for training | Commercial not restricted (API terms) | Unverified |
| Repeatable pipeline | Yes | Yes (one API also reaches Veo and Grok) | Yes | Yes (package purchase friction) | Yes |

### 2.8 Recommendation

- **Primary: xAI `grok-imagine-video-1.5`** (image model: `grok-imagine-image-2.0`).
  - Pinning first and last frame gives mathematically seamless ambient loops, and dock/warp clips that start on a locked reference frame. That fixes the biggest consistency risk.
  - Any integer duration from 1 to 15 s means we don't pay for seconds we trim.
  - The 480p price is the lowest confirmed on a primary page ($0.08/s), and 480p→540p delivery is enough for the viewport.
  - Ownership of output is clean, with no training on our content.
  - It's Ben's existing stack (the xAI key is already used for LLM seats, voice layer, and stills), and 10 RPS is plenty.
- **Fallback: Runway Dev API.**
  - One integration reaches `gen4.5`, `veo3.1_fast`, and even `grok_imagine_1_5`, so if xAI has an outage or rejects a shot, the same shot list can be retried on a different model without a new integration.
  - Clear commercial rights, and documented concurrency with auto-queueing.
  - First/last frame and references are both supported.
  - **Caveat:** Runway's terms grant it training rights on inputs and outputs. If Ben objects, use **Google Veo 3.1 Fast directly** as the fallback instead (paid tier not used for training, documented 11 s–6 min latency; downsides are the forced 8 s with references and audio always generated).

## 3. Art bible (style guide), locked before any video spend

A single markdown file (`media/artbible/ARTBIBLE.md`) plus locked reference images. Built by extending the existing `web/media/prompts/*.txt` language ("dark navy + amber lights, no readable text, no logos, 16:9").

- **Palette:** deep navy/ink blacks (#05070F–#0E1428, matching `bot.css` panel colors), amber/sodium accent (trade, docking lights), cyan-white (warp), red-orange (combat), sickly green (Ferrengi). 5 swatches, with each hex tagged by use.
- **Camera language (the window rule):** everything is seen **from inside our cockpit looking out** through a fixed 16:9 window, or as a short exterior "establishing" shot only for docking and warp exits. Locked lens feel: 35 mm equivalent, slow push-ins, no handheld shake except under incoming fire (short, ≤0.5 s), no whip pans, horizon roughly level.
- **Lighting:** a key light from a distant star (warm, upper left), cool fill, practical lights on stations. Consistent across clips. No lens-flare spam (photosensitivity).
- **Ship design sheet:** 4 hull families (hauler, light, heavy, capital; see PHASE_PLAN §4.2), each with 3 locked views (front ¾, side, rear ¾), generated with `grok-imagine-image-2.0` and refined by image edits. Cockpit-interior frame per family (for the CSS overlay). Opponents: Ferrengi raider, generic rival trader, fighter swarm.
- **Environment sheet:** standard port (small/large), Federation port, StarDock, 7 planet classes grouped into looks, warp tunnel, deep-space and nebula backdrops.
- **Do/don't:** no readable text, no logos, no human faces (avoids likeness issues), no gore, destruction limited to vehicles and debris, ≤3 flashes/sec.
- **Locking:** every approved reference image gets a stable ID (`REF-HULL-HAULER-F34-v2`) and a SHA-256, stored in `media/artbible/refs/`. Prompts reference IDs, never ad-hoc images.

## 4. Prompt template

Kept in `media/shots/templates/*.j2` and filled from the shot list. Fields:

```
[SHOT_ID] S-DOCK-STD-HAULER-01        [KEY] dock.port   [VARIANT] std.hauler.a
[MODE] image_to_video | first_last | reference
[FIRST_FRAME] REF-DOCK-STD-START-v1   [LAST_FRAME] REF-DOCK-STD-END-v1 (optional)
[REFERENCES] REF-HULL-HAULER-F34-v2, REF-STATION-STD-v1 (reference mode only)
[DURATION_S] 5   [RES] 480p|720p   [ASPECT] 16:9   [AUDIO] false
PROMPT:
"{camera}. {subject_action}. {environment}. {lighting}. {style_suffix}"
  camera          = "Locked view from inside our cockpit window, slow push-in"
  subject_action  = "docking clamps extend and lock onto our hull as we glide into the bay"
  environment     = "{station_look} orbital trading port, cargo crates, amber bay lights"
  lighting        = ART_BIBLE.lighting
  style_suffix    = ART_BIBLE.style_suffix  # "cinematic retro space-trader concept art, dark navy and amber, no readable text, no logos, no people"
NEGATIVE (as prose, since the API has no negative field): "no text, no logos, no faces, no flashing strobes"
```

## 5. Generation pipeline (script design, not built)

`tools/clipgen/` (Python, runs on Ben's PC or the box, **never on the game server hot path**):

1. `shotlist.yaml` lists the shots: `shot_id, key, variant tags, mode, refs, duration, res, takes, priority`.
2. `clipgen plan` resolves templates, prints the prompts and a **cost preview** (seconds × price table from `prices.yaml` with source URL and date), and refuses to run if the preview exceeds `--budget`.
3. `clipgen run` does the following for each take:
   - POST `/v1/videos/generations` (or the Runway adapter), and store `request_id`.
   - Poll with backoff (5 s → 30 s), timeout 15 min.
   - Download `video.url` immediately (the URL is temporary).
   - Write `out/<shot_id>/take_<n>/raw.mp4` plus `meta.json` with prompt, template hash, ref IDs and SHA-256s, model, model alias resolved, params, request_id, timestamps, latency, billed seconds, cost estimate, and moderation flag.
   - Concurrency limit is configurable (default 4). It retries on `service_unavailable`/`internal_error` and does **not** retry `invalid_argument` (moderation).
4. `clipgen sheet` builds a static HTML contact sheet (poster grid plus inline players, side by side with reference stills) for review.
5. Everything is idempotent: a take already present with the same `(template hash, refs, params)` is skipped.

Adapters: `xai.py` (primary), `runway.py` and `veo.py` (fallback), all behind one `generate(shot) -> raw file + meta` interface, so the fallback is a config switch.

## 6. HYBRID GENERATION MODEL

Two tiers. (1) A **pre-rendered, human-reviewed base library** covers the common actions and plays instantly. (2) A **background custom queue** handles rare or truly custom moments: it may produce a clip in time, but gameplay never waits for it. §7 folds both into the end-to-end workflow.

### 6.1 Pre-rendered base library

**Templated variables.** Each common action is a template with variables:
- `hull`: own ship family. Only matters in **exterior** shots (dock approach, warp exit).
- `destination`: port class look (`std_small`, `std_large`, `fed`, `stardock`), planet look, or sector look (`deep`, `nebula`, `fedspace`, `port_near`).
- `faction`: the **opponent** in combat (`ferrengi`, `rival_ship`, `fighter_sector`). Own alignment (good/evil) is handled as a CSS tint on the cockpit frame, not as a re-render.
- `outcome`: `hit`, `miss`, `incoming`, `witnessed`.

**Choosing and pruning the matrix:**
1. **The camera rule prunes first.** The viewport is first-person, so own hull is invisible in interior shots (combat, ambient) and is supplied by the per-hull cockpit-frame overlay. That removes `hull` from combat and ambient entirely.
2. **Collapse raw engine values into visual looks.** 10 ship classes → 4 hull families. 9 port classes → 4 station looks (BSS…BBB differ only in trade direction, which is invisible). 7 planet classes → 3–4 looks.
3. **Weight by real frequency.** Mine the recorded matches (`tw2k-replay`, turn logs) for counts of `(event kind × hull family × station look)` among self events. Render every cell that covers the top ~90% of occurrences, and give the top cells 2–3 variants (for no-repeat variety). Every other cell falls back.
4. **Fallback chain for missing cells** (the manifest resolver already does this; PHASE_PLAN §4.1): exact `(hull, destination, faction)` → drop faction → drop hull (`*`) → generic key → poster still. So an unrendered combination is **reused, not blank**.
5. **Re-evaluate after each wave** using the client counters from PHASE_PLAN V4 (poster-fallback count per key shows which cells are missing).

**Why pruning matters (dock alone).** Unpruned: 10 ship classes × 9 port classes × 3 factions = 270 cells. At 5 s, 2.5 takes, and $0.14/s that's 270 × 5 × 2.5 × 0.14 = **$472.50** for docking only. Pruned: 4 hulls × 3 station looks = 12 cells.

**Base library v1 matrix (dock/warp/combat/ambient):**

| Key | Cells | Variants | Clips | Gen length |
|---|---|---|---|---|
| `dock.port` | 4 hull × 3 looks (std_small, std_large, fed) = 12 | 1 each, plus 1 extra on the top 4 cells | 16 | 5 s |
| `warp.out` | 4 hull | 2 | 8 | 5 s |
| `combat.{hit,miss,incoming}` | 3 outcomes × 3 opponent factions = 9 | 2 | 18 | 5 s |
| `combat.witnessed` | 1 | 2 | 2 | 5 s |
| `ambient.*` | deep, nebula, fedspace, port_near | 1 (seamless loop) | 4 | 8 s |
| **Total** | | | **48** | |

**Cost math (sourced prices, generation seconds, not delivered seconds):**
- Seconds per full take round: 44 clips × 5 s + 4 × 8 s = 220 + 32 = **252 s**.
- Takes: assume an average of **2.5 generations per approved clip**, since style is locked after the pilot. That's an assumption, not a vendor figure. So 252 × 2.5 = **630 s**.
- xAI 1.5 @ 480p, $0.08/s (docs): 630 × 0.08 = **$50.40**.
- xAI 1.5 @ 720p, $0.14/s (UNVERIFIED-secondary): 630 × 0.14 = **$88.20**.
- Image inputs: 48 × 2.5 gens × 2 images × $0.01 = **$2.40**.
- Reference stills for the full sheet: about 80 images × $0.04 (image-2.0) = **$3.20**.
- **Base v1 total ≈ $56 (480p) to $94 (720p).** Cross-check at Runway gen4.5 $0.12/s: 630 × 0.12 = $75.60. At Luma 720p $0.30 per 5 s: 44 × 0.30 + 4 × 0.90 = $16.80 per round, × 2.5 = $42.00 (subject-reference support unverified).

**Naming and manifest keys:** clip key `dock.port`, variant tags `{station: std_small, hull: hauler}`, variant id `dock_port_std_small_hauler_a`, file `dock_port_std_small_hauler_a.<hash8>.webm` / `.mp4` / poster `.webp`. Shot IDs (`S-DOCK-STDS-HAUL-01`) link manifest provenance back to `out/<shot_id>/take_<n>/meta.json`.

**Generation batches:** batch 0 is lookdev (§10). Batch 1 is the pilot's 14 clips. Batch 2 fills the rest of base v1. Each later wave is its own batch. Each batch has a budget line in `prices.yaml`, a `--budget` hard stop, and one contact-sheet review session.

**Approval:** full human review (§9) by Ben or a delegate. Only approved takes get promoted.

**Storage / CDN:**
- Masters (raw MP4 plus meta) live **outside git**: the box's `/workspace` or Ben's PC, plus a cloud-drive backup.
- Delivered renditions of the base v1 set are about 48 × (350 KB WebM + 450 KB MP4 + 50 KB poster) ≈ **41 MB**. That's fine under `web/media/clips/` for the pilot (14 clips ≈ 12 MB). Past about 50 MB, move to Git LFS or an object store/CDN with hashed immutable URLs, and put the base URL in the manifest (`"base": "https://…"`). Pick the CDN later; no vendor prices were researched.
- Cache headers are `immutable` (PHASE_PLAN §4.5).

**Instant playback:** posters load eagerly. P0–P2 base clips for the **current context** (the hull you fly, the station looks nearby, opponent types present) are idle-preloaded into a blob LRU (12 MB cap). The first frame is identical to the poster, so the swap from poster to video is invisible even if decode starts late.

### 6.2 Background custom queue (rare or truly custom moments)

**When it's used:** only for triggers flagged `custom: true` in the manifest (e.g. Genesis on a rare planet class, first kill of a named rival, citadel level 5, own death in a specific sector look). Never for dock, warp, or ordinary combat; those always come from the base library.

**Flow:**
1. **Event arrives at the server** (not the browser). A small hook subscribes to `Universe.emit` in the FastAPI process, filters `custom` kinds, and builds the prompt **per seat** by passing the event through `_event_visible_to(event, pid)` and `event_view()`. Only whitelisted fog-legal `facts` plus that seat's own Observation fields (own hull family, own sector look) go into the prompt. No names of players this seat can't see, no god-state.
2. **Dedupe/cache:** `prompt_hash = sha256(template_id + normalized fields + ref IDs + model + params)`. If `clips/custom/<hash>.webm` exists and is approved (or auto-passed; see §6.3), reuse it instantly. If a job with that hash is in flight, attach to it.
3. **Enqueue** to a separate worker process (asyncio task queue, or a subprocess with a SQLite job table: `hash, seat, match_id, status, created, deadline, cost_est`). The game loop only does an O(1) insert; **no network I/O happens on the game thread.**
4. **Limits:**
   - xAI's 10 RPS is not the constraint; cost is. Default caps: **$1.00 per match and $5.00 per day**, ≤1 in-flight job per seat, and ≤3 custom jobs per match.
   - Jobs use 480p, 4 s, `generate_audio: false`. Cost per job on 1.5 = 4 × $0.08 + $0.01 image = **$0.33**, so the $1/match cap allows 3 jobs.
   - Classic `grok-imagine-video` 480p would be 4 × $0.05 + $0.002 = $0.202, but it can't pin first/last frames.
   - Job timeout 10 min (the SDK default), then mark `expired`.
5. **Placeholder, shown at once in the browser:** the client resolves the same trigger to its `placeholder` key from the base library. That's a generic style-matched loop, like a hyperspace shimmer, a static/scan-line "sensor reconstruction" overlay, or the key's poster still with a slow push-in plus the event caption ("Genesis torpedo detonating…"). It's always local and instant.
6. **Swap rule:** the server notifies the seat via its fogged event stream (a lightweight `media_ready` note keyed by the original event seq, visible only to that seat) or via polling `GET /media/custom/<hash>`. The client swaps the custom clip in **only if** no newer self action or P0/P1 event has happened since the triggering event and the placeholder is still showing. Otherwise it does nothing. **Gameplay is never blocked.**

### 6.3 When the custom clip doesn't land in time

- **Keep what's showing:** the placeholder, or the nearest base-library variant, finishes normally and returns to ambient.
- **The late clip isn't wasted:** it's stored as `custom/<hash>` with status `late`. It's (a) offered in an optional **post-turn / replay reel** ("Moments" drawer on `/bot`, and the replay viewer, only for the seat that was entitled to see it), and (b) queued for **human review**. If approved, it gets promoted into the base library as a new variant (tags from the prompt fields), so the next identical moment plays instantly from cache.
- **Different trust levels:**
  - The **base library** is fully human-reviewed (§9) and labeled `trust: reviewed`.
  - **Live custom clips** are **auto-checked only**: the provider's moderation flag (`respect_moderation`), an automated style check (poster frame compared against art-bible reference embeddings, plus a palette histogram distance threshold), duration and resolution sanity, and a flash-rate check (frame-luma delta count ≤3/s). Clips that pass are labeled `trust: auto` and shown with a small "live-generated" badge. Clips that fail are discarded, since the placeholder already covered the moment.
  - `trust: auto` clips never enter the reusable library without human approval.
- **Fog:** the prompt builder is the enforcement point (per-seat, `event_view` facts only). The cache is keyed by prompt hash, so two seats share a clip only when their fog-legal prompts are identical. Sharing then reveals nothing new. The replay reel follows the same per-seat visibility as `/events`.

**Expected custom latency and realism:**

| Tool | Documented / known latency | Source |
|---|---|---|
| xAI Grok Imagine | "typically takes up to several minutes"; no p50 published (UNVERIFIED) | https://docs.x.ai/developers/model-capabilities/video/generation |
| Google Veo 3.1 | min 11 s, max 6 min at peak | https://ai.google.dev/gemini-api/docs/veo |
| Runway Dev | worked example assumes ~15 s/video (illustrative, not an SLA; UNVERIFIED) | https://docs.dev.runwayml.com/usage/tiers/ |
| Kling, Luma | UNVERIFIED | — |

**Is custom-in-time realistic?** Mostly **no**.
- LLM seats act every few seconds, so the clip will essentially never land before their next action.
- Human and CU seats sometimes deliberate 30 s to several minutes (CU seats get a 600 s external timeout per the grokbot-player plan G4), so a fast render can sometimes land.
- Design assumption: in-time is a **bonus**, and the late path (reel plus library growth) is the main value.
- Measure real p50/p90 during lookdev (§10) with a handful of timed 4 s/480p jobs before turning on V8.

### 6.4 Acceptance for the custom queue (PHASE_PLAN V8)
- A timing test shows the game loop's `emit` → next-turn latency is unchanged with the queue on (the job insert only, no network I/O on the game thread).
- The placeholder appears in the same poll as the triggering event. A custom clip that lands after a newer self action is **not** swapped in (tested with a fake slow provider).
- The per-match and per-day caps are enforced by unit test (the 4th job in a match is refused, and the refusal is logged).
- A repeat of an identical fog-legal prompt hits the cache (no second provider call).
- Fog test: a prompt built for seat A never contains facts that `_event_visible_to` hides from A (property test over fixture events).
- Late clips show up in the per-seat reel only, labeled `trust: auto`, and never enter the base library without human approval.

## 7. End-to-end workflow (with the hybrid model folded in)

```
Art bible + locked refs ─► shotlist.yaml (base matrix, pruned by frequency) ─► clipgen plan (cost preview, budget gate)
      │                                                                        │
      │                                                                        ▼
      │                                                     clipgen run (xAI primary, Runway/Veo fallback)
      │                                                                        │ raw.mp4 + meta.json per take
      ▼                                                                        ▼
Contact sheet review (§9) ──reject──► re-prompt / new take (versioned) ◄───────┘
      │ approve
      ▼
Post-process (§8): trim, loop, scale, encode WebM+MP4, poster, (SFX)
      ▼
Promote: hash names, copy to web/media/clips|posters (or CDN), write manifest v2 variant + provenance, run validator
      ▼
Cockpit plays base library instantly  ◄──── later promotion of reviewed late custom clips
      ▲
Live custom queue (V8, optional): server event ─► fog-safe per-seat prompt ─► hash cache ─► worker job (caps, timeout)
      │        client shows placeholder at once; swap only if the clip lands before the next action;
      └─────── otherwise late ─► auto-checked, stored, shown in reel ─► human review ─► base library
```

## 8. Post-processing (ffmpeg recipes to standardize; not run)

1. **Normalize:** scale/crop to exactly 16:9 (secondary sources show xAI 720p output as 1280×704 at 24 fps, **UNVERIFIED**; always crop-to-fit): `-vf "scale=960:540:force_original_aspect_ratio=increase,crop=960:540,fps=24"`.
2. **Trim** event clips to the action beat (2–4 s) with a 4–6 frame fade from the poster at the start and a fade to ambient at the end.
3. **Loops:** ambient generated with first = last frame pin needs only a check. Otherwise, crossfade the tail into the head (`xfade` 0.5 s) and verify frame 0 ≈ frame N (SSIM > 0.97).
4. **Encode:**
   - WebM VP9: `-c:v libvpx-vp9 -b:v 0 -crf 36 -row-mt 1 -an`
   - MP4 H.264: `-c:v libx264 -crf 26 -preset slow -profile:v high -pix_fmt yuv420p -movflags +faststart -an`
   - Also produce a 640×360 rendition.
   - Enforce the size caps (PHASE_PLAN §6), and step CRF up until the clip fits.
5. **Poster:** frame 0 exported as WebP q80 (≤60 KB), plus a JPEG fallback.
6. **Flash check:** script counts luma spikes; reject if >3/s.
7. **Audio (optional, V7+):** strip generated audio. Add SFX as separate `.opus` files per key (mixed at −18 LUFS), and play them only if Sound is on.
8. **Record** final bytes, duration, and hashes into the promote step.

## 9. Review and approval

**Checklist per take (in the contact sheet):**
1. Reads correctly at 560 px wide in under 1 s (docking reads as docking).
2. On-model: hull, station, and opponent match the locked refs; palette matches the art bible.
3. The window rule holds: camera, lens feel, horizon.
4. No text, logos, faces, or gore; ≤3 flashes/s.
5. Loop seam is invisible (ambient).
6. The first frame works as a poster.
7. Nothing implies hidden information (fog), e.g. no specific rival markings unless the key is a visible-opponent variant.
8. File within budget after encode.

**Rejection codes** (recorded in `meta.json` → `review`): `OFF_MODEL`, `STYLE_DRIFT`, `WRONG_ACTION`, `ARTIFACT` (warping geometry, flicker), `TEXT_OR_LOGO`, `FLASH`, `LOOP_SEAM`, `FOG_RISK`, `TOO_BIG`, `MODERATION`.

**Versioning:** takes are immutable (`take_<n>`). A re-prompt bumps the template version (`tmpl_v`), and refs are versioned (`-v2`). The manifest variant carries `shot_id`, `take`, `tmpl_v`, `model`, `approved_by`, `approved_at`, and content hash. Replacing a clip means a new hash, so a new URL, so there are no cache problems. Keep the previous approved take for rollback.

## 10. Budget: first set, with the math shown

**Batch 0, lookdev bake-off (optional, before the pilot):** 5 identical test shots (dock, warp, hit, incoming, ambient loop) on xAI 1.5 at 480p, 5 s each: 25 s × $0.08 = **$2.00**. The same 5 shots on Runway gen4.5 (25 × $0.12 = **$3.00**) and Veo 3.1 Fast (5 × 8 s × $0.10 = **$4.00**). **Total ≈ $9** to pick the primary on real quality, and to time custom latency (p50/p90).

**Pilot set (N = 6 action/event keys + 1 ambient key; 14 final clips):**

| Line | Math | xAI 1.5 480p ($0.08/s, docs) | xAI 1.5 720p ($0.14/s, secondary) |
|---|---|---|---|
| Event clips: 12 clips × 5 s × 3 takes | 180 s | $14.40 | $25.20 |
| Ambient loops: 2 × 8 s × 3 takes | 48 s | $3.84 | $6.72 |
| Image inputs: 42 gens × 2 imgs × $0.01 | 84 imgs | $0.84 | $0.84 |
| Reference stills: 60 imgs × $0.04 (image-2.0) | 60 imgs | $2.40 | $2.40 |
| **Pilot total** | | **$21.48** | **$35.16** |

- Takes = 3 per approved clip for the pilot. That's an **assumption** (the style isn't locked yet), not a vendor figure.
- Recommended pilot spend cap: **$50** (covers 720p plus about 40% retakes).
- Cross-check, same 228 s on Runway gen4.5: 228 × $0.12 = $27.36 + images. On Veo 3.1 Fast with 8 s forced when using refs: 42 × 8 × $0.10 = $33.60.

**Base library v1 (§6.1):** about $56 (480p) to $94 (720p).
**Later waves (StarDock, weapons, planets, death/pod, about 70 clips × 5 s × 2.5 takes = 875 s):** 480p $70.00 / 720p $122.50.
**Live custom (V8):** capped by config at $1/match and $5/day.

## 11. Risks and mitigations

- **Style drift across clips:** lock refs, use first-frame pins, keep one model version (use the dated alias `grok-imagine-video-1.5-2026-05-30`, not the floating name).
- **Moderation charges on combat prompts:** keep the vehicle-only language, and pre-test the prompt templates during lookdev.
- **Temporary output URLs:** download inside the poll loop and keep masters.
- **Price change:** `prices.yaml` has a source URL and date, and `clipgen plan` warns if it's older than 30 days.
- **Vendor outage:** the adapter switch to Runway or Veo.
- **Training/licensing concerns:** prefer xAI (no training, assignment) or Veo paid tier. Note Runway's training grant.

## 12. Unverified items (summary)

- xAI 1.5 per-resolution prices **$0.14/s (720p) and $0.25/s (1080p)**: secondary sources only (fal, ofox, wavespeed, creeta). docs.x.ai shows only "$0.080/sec" and "from $0.08/sec".
- xAI max reference images (1–7 per fal), existence of a seed parameter, whether silent output changes price, real p50/p90 latency, exact output pixel size (1280×704 per fal).
- Runway real latency (the ~15 s is an illustrative example), and gen4.5 quality.
- Veo 3.1 Lite reference-image support, and Veo rate limits.
- Kling latency and rate limits.
- Luma subject-reference support, latency, rate limits, licensing.
- Pika's own models, pricing, and terms (not assessed).
- Relative quality of every tool (no hands-on tests were run; the vendor ranking claim is unverified).
- The takes-per-approved-clip ratios (3 pilot, 2.5 later) are planning assumptions.
