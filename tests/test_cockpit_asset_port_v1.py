"""cockpit-asset-port-v1. Scene keys, a missing-file fallback, and the asset import."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "web" / "media"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate_mod = _load("media_validate_manifest", ROOT / "scripts" / "media_validate_manifest.py")
import_mod = _load("import_cockpit_assets", ROOT / "scripts" / "import_cockpit_assets.py")


def _manifest() -> dict:
    return json.loads((MEDIA / "manifest.json").read_text(encoding="utf-8"))


def test_validator_accepts_the_scene_keys() -> None:
    data = _manifest()
    errors, _report = validate_mod.validate(data, MEDIA)
    assert errors == []
    for key in validate_mod.SCENE_KEYS:
        assert key in data["keys"]
    assert validate_mod.resolve_scene(data, "sector_deep", MEDIA) == "stills/sector_deep.webp"
    assert validate_mod.resolve_scene(data, "death_pod", MEDIA) == "stills/death_pod.webp"
    assert validate_mod.resolve_scene(data, "sector_port_4", MEDIA) == "stills/sector_port_4.webp"
    assert validate_mod.resolve_scene(data, "ship_unknown_hull", MEDIA) == "stills/sector_deep.webp"


def test_a_missing_file_falls_through_to_a_drawn_scene() -> None:
    data = _manifest()
    data["keys"]["sector_deep"] = {"file": "stills/does_not_exist.png", "fallback": "canvas"}
    data["keys"]["warp"] = {"file": "stills/also_missing.png", "fallback": "sector_deep"}
    assert validate_mod.resolve_scene(data, "warp", MEDIA) == "canvas"


def test_the_validator_script_exits_clean() -> None:
    run = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "media_validate_manifest.py")],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "OK" in run.stdout


def test_import_copies_a_dropped_still(tmp_path: Path) -> None:
    stills = tmp_path / "stills"
    stills.mkdir()
    (stills / "extra.png").write_bytes(b"png")
    media = tmp_path / "media"
    media.mkdir()
    manifest = media / "manifest.json"
    manifest.write_text(json.dumps({"keys": {}}), encoding="utf-8")
    (tmp_path / "manifest_additions.json").write_text(
        json.dumps({"keys": {"sector_deep": {"file": "stills/extra.png", "fallback": "canvas"}}}),
        encoding="utf-8",
    )
    copied = import_mod.import_assets(tmp_path, media, manifest)
    assert copied == ["stills/extra.png"]
    assert (media / "stills" / "extra.png").is_file()
    saved = json.loads(manifest.read_text(encoding="utf-8"))
    assert saved["keys"]["sector_deep"]["file"] == "stills/extra.png"


def test_import_turns_a_dropped_scene_into_webp(tmp_path: Path) -> None:
    from PIL import Image

    stills = tmp_path / "stills"
    stills.mkdir()
    Image.new("RGB", (32, 18), (10, 20, 30)).save(stills / "sector_deep.jpg", "JPEG")
    media = tmp_path / "media"
    media.mkdir()
    manifest = media / "manifest.json"
    manifest.write_text(json.dumps({"keys": {"sector_deep": {"fallback": "canvas"}}}), encoding="utf-8")
    (tmp_path / "manifest_additions.json").write_text(
        json.dumps({"contexts": {"sector_deep": {"still": "stills/sector_deep.jpg"}}}),
        encoding="utf-8",
    )
    copied = import_mod.import_assets(tmp_path, media, manifest)
    assert copied == ["stills/sector_deep.webp"]
    assert (media / "stills" / "sector_deep.webp").stat().st_size <= 300_000
    saved = json.loads(manifest.read_text(encoding="utf-8"))
    assert saved["keys"]["sector_deep"]["file"] == "stills/sector_deep.webp"
    assert saved["keys"]["sector_deep"]["fallback"] == "canvas"


def test_import_ignores_a_missing_folder() -> None:
    assert import_mod.import_assets(ROOT / "does-not-exist") == []
