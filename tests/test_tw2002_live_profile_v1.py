"""One switch turns every live helper on. Off, each stored flag stays legacy."""
import tw2k.engine.constants as K

HELPERS = (
    "avoid_live",
    "bank_live",
    "alignment_live",
    "alliance_live",
    "api_args_live",
    "assign_pool_fix_live",
    "async_day_live",
    "citadel_days_live",
    "citadel_perk_live",
    "cockpit_parity_live",
    "combat_odds_live",
    "corp_rules_v2_live",
    "death_pod_live",
    "detect_gear_live",
    "discovery_exp_live",
    "exp_score_live",
    "fed_ships_live",
    "fedspace_deploy_live",
    "genesis_start_live",
    "haggle_live",
    "haggle_window_live",
    "hardware_price_live",
    "hold_rules_live",
    "home_planet_live",
    "own_planet_fighter_live",
    "own_planet_turn_live",
    "planet_class_live",
    "planet_nw_live",
    "planet_prod_live",
    "planet_shields_active",
    "port_attack_live",
    "port_class_live",
    "port_price_live",
    "port_regen_live",
    "rank_display_live",
    "rank_titles_live",
    "seat_deadline_live",
    "ship_roster_live",
    "shop_price_live",
    "starting_package_live",
    "terra_colonist_live",
    "trade_in_live",
    "trade_turn_live",
    "turn_regen_live",
    "warp_cost_live",
    "planet_colonist_cap_live",
    "landed_state_live",
    "planet_dividend_off",
    "live_pace",
    "planet_value_scored",
    "planet_realtime_prod",
    "universe_topology_live",
    "planet_scanner_live",
    "scanner_fog_live",
    "citadel_park_live",
    "radio_channel_live",
    "daily_stats_live",
    "fedcomm_live",
    "corp_rank_live",
    "gold_alien_live",
    "class_m_fidelity_live",
    "port_stock_fidelity_live",
    "ship_exit_on",
    "rival_strength_live",
    "kill_cash_held",
    "planet_landing_combat_on",
    "offensive_clash_held",
    "owner_hazard_notice_on",
    "ship_flee_published",
    "planet_shield_l5",
    "ferrengi_engage_on",
    "siege_report_on",
    "planet_growth_tw2002",
    "ai_cockpit_seat_on",
    "cockpit_fields_on",
    "tax_v311",
    "pod_cash_live",
    "yard_stats_on",
    "citadel_table_fix_live",
    "class_m_nw_units",
    "class_m_drop_units",
    "class_m_genesis_units",
    "alien_combat_fix_live",
    "haggle_counter_live",
    "bot_hazard_memory_live",
    "trade_in_parts_live",
    "trader_rank_list_live",
    "nw_estimate_live",
    "seat_idle_start_live",
    "bot_diplomacy_live",
    "port_buy_price_anchor_on",
    "treasury_cap_live",
    "course_max_live",
    "big_bang_density_live",
    "one_way_share_live",
    "atomic_detonator_live",
)


def test_profile_stays_off_and_helpers_stay_false() -> None:
    assert K.TW2002_LIVE_PROFILE == "legacy"
    assert K.tw2002_live_profile() is False
    names = HELPERS
    assert len(names) == 96
    for name in names:
        assert getattr(K, name)() is False, name


def test_profile_on_turns_every_helper_on_without_moving_the_stored_flag(monkeypatch) -> None:
    monkeypatch.setattr(K, "TW2002_LIVE_PROFILE", "live")
    assert K.tw2002_live_profile() is True
    for name in HELPERS:
        assert getattr(K, name)() is True, name
    assert K.TERRA_COLONIST_MODE == "legacy"
    assert K.SHIP_EXIT_MODE == "legacy"
    assert K.RIVAL_STRENGTH_MODE == "legacy"
    assert K.KILL_CASH_MODE == "legacy"
    assert K.PLANET_LANDING_COMBAT_MODE == "legacy"
    assert K.OFFENSIVE_CLASH_MODE == "legacy"
    assert K.OWNER_HAZARD_NOTICE_MODE == "legacy"
    assert K.SHIP_FLEE_MODE == "legacy"
    assert K.PLANET_SHIELD_MODE == "legacy"
    assert K.FERRENGI_ENGAGE_MODE == "legacy"
    assert K.SIEGE_REPORT_MODE == "legacy"
    assert K.PLANET_GROWTH_MODE == "legacy"
    assert K.AI_COCKPIT_SEAT_MODE == "legacy"
    assert K.COCKPIT_FIELDS_MODE == "legacy"
    assert K.TAX_RULE_MODE == "legacy"
    assert K.V311_PROFILE == "legacy"
    assert K.POD_CASH_MODE == "legacy"
    assert K.YARD_STATS_MODE == "legacy"
    assert K.PORT_BUY_PRICE_ANCHOR_MODE == "legacy"
    assert K.EXP_SCORE_MODE == "legacy"
    assert K.CLASS_M_NW_MODE == "legacy"
    assert K.CLASS_M_DROP_MODE == "legacy"
    assert K.CLASS_M_GENESIS_MODE == "legacy"
    assert K.ALIEN_COMBAT_FIX_MODE == "legacy"
    assert K.HAGGLE_COUNTER_MODE == "legacy"
    assert K.BOT_HAZARD_MEMORY_MODE == "legacy"
    assert K.TREASURY_CAP_MODE == "legacy"
    assert K.COURSE_MAX_MODE == "legacy"
    assert K.BIG_BANG_DENSITY_MODE == "legacy"
    assert K.ONE_WAY_SHARE_MODE == "legacy"
    assert K.ATOMIC_DETONATOR_MODE == "legacy"
    assert K.ATOMIC_MINES_PORT_NUKE is True
    assert K.PLANET_TREASURY_CAP == 10_000_000
    assert K.DEFAULT_ONE_WAY_FRACTION == 0.15
    assert K.PORT_SPAWN_PROBABILITY == 0.65
