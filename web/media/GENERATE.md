# Generate media stills (Commander runbook)

1. Read prompt in `web/media/prompts/<name>.txt`.
2. Generate image (16:9) via Grok Bot GenerateImage (or artist).
3. Save/copy to `web/media/stills/<name>.png` matching `manifest.json`.
4. `python scripts/media_validate_manifest.py` until missing = 0.
5. Refresh `/bot` — `media-player.js` picks up the file.

Video: drop `.webm` into `web/media/clips/` and add `"clip": "clips/....webm"` on the kind/group entry. No native Grok-video tool in Commander yet; Enterprise clip recorder or external API can fill clips later.

## Status
- **ML1 stills:** 16/16 present under `stills/` (2026-09-25 PT). Re-run `python scripts/media_validate_manifest.py` after edits.
- **ML3 clips:** empty; drop WebM/MP4 into `clips/` and set `clip` on manifest entries.
