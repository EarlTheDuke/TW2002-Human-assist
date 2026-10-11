"""Every engine verb has a button on the bot screen. The parity switch stays off."""
import re
from pathlib import Path

from tw2k.engine.actions import ActionKind
from tw2k.engine import constants as K

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
HTML = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")


def _quoted(block: str) -> set[str]:
    return set(re.findall(r'"([a-z0-9_]+)"', block))


def test_every_verb_has_a_button() -> None:
    s3 = JS.split("const S3_VERBS = ", 1)[1].split(";", 1)[0]
    groups = JS.split("const VERB_GROUPS = ", 1)[1].split("const LABEL", 1)[0]
    forms = JS.split("const FORM_SPECS = ", 1)[1].split("function renderGenericForm", 1)[0]
    covered = _quoted(s3) | _quoted(groups)
    missing = [k.value for k in ActionKind if k.value not in covered]
    assert missing == []
    for kind in covered - _quoted(s3):
        assert f"{kind}:" in forms, kind
    assert 'data-group="tavern"' in HTML
    assert 'id="holdBtn"' in HTML and 'data-verb="wait"' in HTML
    assert "FAILED" in JS


def test_parity_switch_stays_off() -> None:
    assert K.COCKPIT_PARITY_MODE == "legacy"
    assert K.cockpit_parity_live() is False
