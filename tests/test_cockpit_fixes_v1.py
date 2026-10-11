"""The bot screen lists every P0 and P1 verb from the cockpit audit."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "web" / "bot.js").read_text(encoding="utf-8")
HTML = (ROOT / "web" / "bot.html").read_text(encoding="utf-8")

P0 = ("terra_colonists",)
P1 = (
    "bank_deposit", "bank_withdraw", "bank_transfer",
    "cloak", "fire_disruptor", "remove_limpet", "launch_beacon",
    "rob", "steal", "port_upgrade", "port_build",
    "corp_set_password", "corp_drop", "corp_transfer",
    "ship_set_corporate", "ship_set_personal", "ship_set_password",
    "apply_commission", "post_reward", "claim_reward",
)


def test_p0_and_p1_verbs_have_a_button_and_a_form() -> None:
    groups = JS.split("const VERB_GROUPS = ", 1)[1].split("const LABEL", 1)[0]
    forms = JS.split("const FORM_SPECS = ", 1)[1].split("function renderGenericForm", 1)[0]
    for kind in P0 + P1:
        assert f'"{kind}"' in groups, kind
        assert f"{kind}:" in forms, kind
    assert 'data-group="port"' in HTML
    join = forms.split("corp_join:", 1)[1].split("corp_leave:", 1)[0]
    assert 'n: "password"' in join
