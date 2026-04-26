"""
tests/test_data_quality.py
──────────────────────────────────────────────────────────────────────────────
Data quality tests using in-memory DuckDB mock data.

Tests:
  1. No null team names in standings
  2. win_pct is between 0.0 and 1.0 for all teams
  3. All players with games_played > 10 have fantasy_score > 0
──────────────────────────────────────────────────────────────────────────────
"""

import pytest
import duckdb


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — shared in-memory DuckDB with mock data
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db():
    """
    Create an in-memory DuckDB instance with mock standings and player tables.
    Scoped to the module so tables are shared across all tests in this file.
    """
    conn = duckdb.connect(":memory:")

    # ── Mock standings table ──────────────────────────────────────────────────
    conn.execute(
        """
        CREATE TABLE mock_standings (
            team            VARCHAR,
            wins            INTEGER,
            losses          INTEGER,
            games_played    INTEGER,
            win_pct         DOUBLE,
            avg_pts_scored  DOUBLE,
            avg_pts_allowed DOUBLE,
            playoff_position VARCHAR
        )
        """
    )
    conn.executemany(
        "INSERT INTO mock_standings VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("Los Angeles Lakers",       42, 30, 72, 0.583, 115.2, 112.4, "Playoff"),
            ("Boston Celtics",           56, 16, 72, 0.778, 120.1, 108.9, "Playoff"),
            ("Golden State Warriors",    34, 38, 72, 0.472, 113.5, 116.2, "Eliminated"),
            ("Miami Heat",               38, 34, 72, 0.528, 111.0, 110.5, "Play-In"),
            ("Milwaukee Bucks",          45, 27, 72, 0.625, 118.3, 114.1, "Playoff"),
            ("Phoenix Suns",             22, 50, 72, 0.306, 109.8, 117.9, "Eliminated"),
            ("Denver Nuggets",           52, 20, 72, 0.722, 119.0, 111.2, "Playoff"),
            ("Dallas Mavericks",         50, 22, 72, 0.694, 117.5, 109.8, "Playoff"),
        ],
    )

    # ── Mock player stats table ───────────────────────────────────────────────
    conn.execute(
        """
        CREATE TABLE mock_player_stats (
            player_id    INTEGER,
            team         VARCHAR,
            games_played INTEGER,
            pts          DOUBLE,
            reb          DOUBLE,
            ast          DOUBLE,
            stl          DOUBLE,
            blk          DOUBLE,
            fantasy_score DOUBLE
        )
        """
    )
    conn.executemany(
        "INSERT INTO mock_player_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            # games_played > 10, should all have fantasy_score > 0
            (1,  "Los Angeles Lakers",    65, 27.5, 8.2, 4.5, 1.1, 0.8, 54.5),
            (2,  "Boston Celtics",        70, 30.1, 5.6, 4.1, 1.3, 0.4, 52.0),
            (3,  "Denver Nuggets",        68, 24.5, 12.4, 9.8, 1.5, 0.7, 70.3),
            (4,  "Dallas Mavericks",      72, 33.9, 4.2, 9.3, 1.2, 0.5, 60.0),
            (5,  "Milwaukee Bucks",       60, 29.8, 11.3, 5.7, 0.9, 1.1, 61.2),
            # games_played <= 10 — excluded from quality check on fantasy_score
            (99, "Phoenix Suns",           8, 12.0, 4.0, 2.0, 0.5, 0.5, 25.0),
        ],
    )

    yield conn
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — No null team names in standings
# ─────────────────────────────────────────────────────────────────────────────
def test_no_null_team_names(db):
    """
    Every row in the standings table must have a non-null team name.
    A null team name would indicate a broken join or bad ingestion.
    """
    result = db.execute(
        "SELECT COUNT(*) AS null_count FROM mock_standings WHERE team IS NULL"
    ).fetchone()

    null_count = result[0]
    assert null_count == 0, (
        f"Found {null_count} rows with NULL team name in standings. "
        "Check ingestion and staging transformations."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — win_pct between 0.0 and 1.0 for all teams
# ─────────────────────────────────────────────────────────────────────────────
def test_win_pct_valid_range(db):
    """
    win_pct must be in [0.0, 1.0] for every team.
    Values outside this range indicate a calculation error.
    """
    invalid = db.execute(
        """
        SELECT team, win_pct
        FROM mock_standings
        WHERE win_pct < 0.0 OR win_pct > 1.0
        """
    ).fetchall()

    assert len(invalid) == 0, (
        f"Found {len(invalid)} teams with invalid win_pct: {invalid}"
    )


def test_win_pct_not_null(db):
    """win_pct must not be NULL for any team in standings."""
    null_rows = db.execute(
        "SELECT team FROM mock_standings WHERE win_pct IS NULL"
    ).fetchall()

    assert len(null_rows) == 0, (
        f"Teams with NULL win_pct: {[r[0] for r in null_rows]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — All players with games_played > 10 have fantasy_score > 0
# ─────────────────────────────────────────────────────────────────────────────
def test_active_players_have_positive_fantasy_score(db):
    """
    Any player who has played more than 10 games must have a positive
    fantasy score. A zero or negative value would indicate a data issue.
    """
    violations = db.execute(
        """
        SELECT player_id, team, games_played, fantasy_score
        FROM mock_player_stats
        WHERE games_played > 10
          AND (fantasy_score IS NULL OR fantasy_score <= 0)
        """
    ).fetchall()

    assert len(violations) == 0, (
        f"Found {len(violations)} active players with invalid fantasy_score: "
        f"{violations}"
    )


def test_qualified_players_count(db):
    """
    Sanity check: there should be at least 1 qualified player
    (games_played > 10) in the mock dataset.
    """
    count = db.execute(
        "SELECT COUNT(*) FROM mock_player_stats WHERE games_played > 10"
    ).fetchone()[0]

    assert count >= 1, "No qualified players found — check mock data setup."


def test_win_pct_consistency(db):
    """
    win_pct should equal wins / games_played (within floating-point tolerance).
    """
    inconsistent = db.execute(
        """
        SELECT team, wins, games_played, win_pct,
               ROUND(CAST(wins AS DOUBLE) / games_played, 3) AS expected
        FROM mock_standings
        WHERE ABS(win_pct - ROUND(CAST(wins AS DOUBLE) / games_played, 3)) > 0.01
        """
    ).fetchall()

    assert len(inconsistent) == 0, (
        f"win_pct is inconsistent with wins/games_played for: "
        f"{[(r[0], r[2], r[3]) for r in inconsistent]}"
    )
