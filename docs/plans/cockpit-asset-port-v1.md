# cockpit-asset-port-v1

The cockpit page already has the stills, the placeholder clips, and the pilot clips. This slice names each scene the later slices will ask for.

`web/media/manifest.json` key `keys` maps a scene name to a file and a fallback. A missing file uses the next key. The chain ends at `canvas`, which is a drawn scene, so the page never shows a broken image. Port classes `sector_port_0` through `sector_port_9` share the port still. Any other `ship_<class>` name uses the deep-space still until a picture for that ship exists. There is no picture yet for the escape pod, so `in_pod` and `death_pod` draw a scene.

`?visuals=0` on the cockpit page turns the media player off. The spectator page and the play page do not load it. The engine is unchanged.

`scripts/import_cockpit_assets.py` copies files from the Commander's cockpit asset folder into `web/media` when that folder is there. It does nothing when the folder is empty.
