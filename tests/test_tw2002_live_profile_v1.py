"""One switch turns every live helper on. Off, each stored flag stays legacy."""
import tw2k.engine.constants as K

HELPERS = (
    "alignment_live",
    "assign_pool_fix_live",
    "citadel_days_live",
    "citadel_perk_live",
    "cockpit_parity_live",
    "combat_odds_live",
    "corp_rules_v2_live",
    "death_pod_live",
    "discovery_exp_live",
    "exp_score_live",
    "fed_ships_live",
    "fedspace_deploy_live",
    "genesis_start_live",
    "haggle_live",
    "haggle_window_live",
    "hardware_price_live",
    "hold_rules_live",
    "own_planet_turn_live",
    "planet_nw_live",
    "planet_prod_live",
    "planet_shields_active",
    "port_attack_live",
    "port_class_live",
    "port_price_live",
    "port_regen_live",
    "rank_titles_live",
    "ship_roster_live",
    "shop_price_live",
    "starting_package_live",
    "terra_colonist_live",
    "trade_in_live",
    "trade_turn_live",
    "warp_cost_live",
)


def test_profile_stays_off_and_helpers_stay_false() -> None:
    assert K.TW2002_LIVE_PROFILE == "legacy"
    assert K.tw2002_live_profile() is False
    names = HELPERS
    assert len(names) == 33
    for name in names:
        assert getattr(K, name)() is False, name


def test_profile_on_turns_every_helper_on_without_moving_the_stored_flag(monkeypatch) -> None:
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.tw2002_live_profile() is True
    for name in HELPERS:
        assert getattr(K, name)() is True, name
    assert K.TERRA_COLONIST_MODE == "legacy"
    assert K.EXP_SCORE_MODE == "legacy"
