"""
tests/test_transformations.py
────────────────────────────────────────────────────────────────────────────
Pure Python unit tests for the business logic formulas used in dbt models.
No DB connections, no network calls — all logic defined inline.
────────────────────────────────────────────────────────────────────────────
"""


# ── Test 1: Fantasy score formula ─────────────────────────────────────────────

def calc_fantasy(pts, reb, ast, stl, blk, tov):
    return round(pts + reb * 1.2 + ast * 1.5 + stl * 3.0 + blk * 3.0 - tov * 1.0, 2)


def test_fantasy_score_typical():
    assert calc_fantasy(30, 10, 5, 2, 1, 3) == 57.5


def test_fantasy_score_zeros():
    assert calc_fantasy(0, 0, 0, 0, 0, 0) == 0.0


def test_fantasy_score_high_blocks():
    result = calc_fantasy(10, 5, 2, 1, 5, 1)
    assert result == round(10 + 5 * 1.2 + 2 * 1.5 + 1 * 3.0 + 5 * 3.0 - 1 * 1.0, 2)


def test_fantasy_score_negative_turnovers():
    # High turnovers should lower the score
    low  = calc_fantasy(20, 5, 5, 1, 1, 0)
    high = calc_fantasy(20, 5, 5, 1, 1, 10)
    assert low > high


# ── Test 2: PER tier classification ──────────────────────────────────────────

def get_tier(per):
    if per >= 20:
        return 'Star'
    if per >= 15:
        return 'Starter'
    if per >= 10:
        return 'Role Player'
    return 'Bench'


def test_tier_star():
    assert get_tier(22) == 'Star'


def test_tier_star_boundary():
    assert get_tier(20) == 'Star'


def test_tier_starter():
    assert get_tier(17) == 'Starter'


def test_tier_starter_boundary():
    assert get_tier(15) == 'Starter'


def test_tier_role():
    assert get_tier(12) == 'Role Player'


def test_tier_role_boundary():
    assert get_tier(10) == 'Role Player'


def test_tier_bench():
    assert get_tier(5) == 'Bench'


def test_tier_bench_zero():
    assert get_tier(0) == 'Bench'


# ── Test 3: Winner derivation ─────────────────────────────────────────────────

def get_winner(home_team, home_score, visitor_team, visitor_score):
    return home_team if home_score > visitor_score else visitor_team


def test_home_wins():
    assert get_winner('LAL', 110, 'GSW', 105) == 'LAL'


def test_visitor_wins():
    assert get_winner('LAL', 98, 'GSW', 110) == 'GSW'


def test_tie_goes_to_visitor():
    # In a tie the condition is False so visitor wins (edge case)
    assert get_winner('LAL', 100, 'GSW', 100) == 'GSW'


# ── Test 4: Streak label ──────────────────────────────────────────────────────

def get_streak_label(rate):
    if rate >= 0.8:
        return 'On Fire'
    if rate >= 0.6:
        return 'Hot'
    if rate >= 0.4:
        return 'Lukewarm'
    if rate >= 0.2:
        return 'Cold'
    return 'Freezing'


def test_on_fire():
    assert get_streak_label(0.9) == 'On Fire'


def test_on_fire_boundary():
    assert get_streak_label(0.8) == 'On Fire'


def test_hot():
    assert get_streak_label(0.7) == 'Hot'


def test_lukewarm():
    assert get_streak_label(0.5) == 'Lukewarm'


def test_cold():
    assert get_streak_label(0.3) == 'Cold'


def test_freezing():
    assert get_streak_label(0.1) == 'Freezing'


def test_freezing_zero():
    assert get_streak_label(0.0) == 'Freezing'


# ── Test 5: Point differential ───────────────────────────────────────────────

def test_point_diff_close_game():
    assert abs(110 - 105) == 5


def test_point_diff_blowout():
    assert abs(88 - 110) == 22


def test_point_diff_symmetric():
    assert abs(120 - 90) == abs(90 - 120)
