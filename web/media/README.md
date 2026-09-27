# `/bot` media library

Short stills (and later clips) keyed to **fogged event kinds**. Served at `/static/media/...`.

See plan: `docs/plans/2026-09-26-clip-library.md`.

## Layout

- `manifest.json` — kind/group → asset
- `stills/` — png/webp
- `clips/` — webm/mp4 (optional)
- `prompts/` — generation prompts for Commander / artists

## Add an asset

1. Drop file in `stills/` or `clips/`.
2. Point `manifest.json` `kinds` or `groups` at it (paths relative to this folder).
3. Run `python scripts/media_validate_manifest.py`.
4. Refresh `/bot`.

## Generate stills (Commander)

Use the prompt files in `prompts/`. Save outputs into `stills/` with the filenames listed in the manifest. Do not invent event kinds that seats never see.
