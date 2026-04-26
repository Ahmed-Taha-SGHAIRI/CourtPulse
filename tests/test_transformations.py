"""
tests/test_transformations.py
──────────────────────────────────────────────────────────────────────────────
Unit tests for CourtPulse business logic transformations.
Pure Python — no database required.

Tests:
  1. fantasy_score calculation
  2. PER tier classification
  3. winner determination from scores
  4. point_diff calculation
  5. streak_label from rolling_win_rate
──────────────────────────────────────────────────────────────────────────────
"""

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Business logic functions (mirrors what the dbt SQL models compute)
# These are tested independently so changes to SQL are caught early.
# ─────────────────────────────────────────────────────────────────────────────

def fantasy_score(pts: float, reb: float, ast: float,
                  stl: float, blk: float) -> float:
    """
    Compute fantasy score per the mart_player_efficiency formula:
      pts + (reb × 1.2) + (ast × 1.5) + (stl × 3) + (blk × 3)
    """
    return pts + (reb * 1.2) + (ast * 1.5) + (stl * 3.0) + (blk * 3.0)


def per_tier(per: float) -> str:
    """
    Map a simplified PER value to a tier label:
      >= 20  → Star
      15-19  → Starter
      10-14  → Role Player
      < 10   → Bench
    """
    if per >= 20:
        return "Star"
    elif per >= 15:
        return "Starter"
    elif per >= 10:
        return "Role Player"
    else:
        return "Bench"


def determine_winner(home_team: str, away_team: str,
                     home_score: int, away_score: int) -> str:
    """Return the winning team name based on scores."""
    if home_score > away_score:
        return home_team
    elif away_score > home_score:
        return away_team
    return "Tie"


def point_diff(home_score: int, away_score: int) -> int:
    """Absolute point difference between home and away scores."""
    return abs(home_score - away_score)


def streak_label(rolling_win_rate: float) -> str:
    """
    Map 5-game rolling win rate to a streak label:
      >= 0.80 → 'On Fire'
      >= 0.60 → 'Hot'
      >= 0.40 → 'Lukewarm'
      >= 0.20 → 'Cold'
      <  0.20 → 'Freezing'
    """
    if rolling_win_rate >= 0.80:
        return "On Fire"
    elif rolling_win_rate >= 0.60:
        return "Hot"
    elif rolling_win_rate >= 0.40:
        return "Lukewarm"
    elif rolling_win_rate >= 0.20:
        return "Cold"
    else:
        return "Freezing"


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — Fantasy score
# pts=30, reb=10, ast=5, stl=2, blk=1 → 57.5
# 30 + (10*1.2) + (5*1.5) + (2*3) + (1*3) = 30 + 12 + 7.5 + 6 + 3 = 58.5
# ─────────────────────────────────────────────────────────────────────────────
def test_fantasy_score_calculation():
    """Fantasy score formula should produce the correct result."""
    result = fantasy_score(pts=30, reb=10, ast=5, stl=2, blk=1)
    # 30 + 12.0 + 7.5 + 6.0 + 3.0 = 58.5
    assert result == pytest.approx(58.5, abs=1e-6), (
        f"Expected 58.5 but got {result}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — PER tier classification
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("per_value,expected_tier", [
    (22.0, "Star"),
    (17.5, "Starter"),
    (12.0, "Role Player"),
    (8.0,  "Bench"),
    (20.0, "Star"),     # boundary — exactly 20 is Star
    (15.0, "Starter"),  # boundary — exactly 15 is Starter
    (10.0, "Role Player"),  # boundary — exactly 10 is Role Player
    (9.99, "Bench"),
])
def test_per_tier_classification(per_value, expected_tier):
    """PER tiers should map correctly across all ranges and boundaries."""
    result = per_tier(per_value)
    assert result == expected_tier, (
        f"PER={per_value}: expected '{expected_tier}', got '{result}'"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — Winner determination
# home_score=110 > away_score=105 → home team wins
# ─────────────────────────────────────────────────────────────────────────────
def test_winner_home_team():
    """Home team should win when home_score > away_score."""
    result = determine_winner(
        home_team="Los Angeles Lakers",
        away_team="Boston Celtics",
        home_score=110,
        away_score=105,
    )
    assert result == "Los Angeles Lakers"


def test_winner_away_team():
    """Away team should win when away_score > home_score."""
    result = determine_winner(
        home_team="Los Angeles Lakers",
        away_team="Boston Celtics",
        home_score=98,
        away_score=110,
    )
    assert result == "Boston Celtics"


def test_winner_tie():
    """Tie should be returned when scores are equal (OT pending)."""
    result = determine_winner(
        home_team="Team A",
        away_team="Team B",
        home_score=100,
        away_score=100,
    )
    assert result == "Tie"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — Point difference
# ABS(110 - 105) = 5
# ─────────────────────────────────────────────────────────────────────────────
def test_point_diff_home_wins():
    """Point diff should be the absolute score difference."""
    assert point_diff(110, 105) == 5


def test_point_diff_away_wins():
    """Point diff is always positive regardless of which team leads."""
    assert point_diff(95, 118) == 23


def test_point_diff_tie():
    """Point diff of 0 for a tied game."""
    assert point_diff(100, 100) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — Streak labels
# 0.85 → 'On Fire', 0.1 → 'Freezing'
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("rate,expected_label", [
    (0.85,  "On Fire"),
    (0.80,  "On Fire"),   # boundary
    (0.75,  "Hot"),
    (0.60,  "Hot"),       # boundary
    (0.55,  "Lukewarm"),
    (0.40,  "Lukewarm"),  # boundary
    (0.30,  "Cold"),
    (0.20,  "Cold"),      # boundary
    (0.10,  "Freezing"),
    (0.0,   "Freezing"),
])
def test_streak_label(rate, expected_label):
    """Streak labels should map correctly at all boundaries."""
    result = streak_label(rate)
    assert result == expected_label, (
        f"rolling_win_rate={rate}: expected '{expected_label}', got '{result}'"
    )
