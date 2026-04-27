"""
tests/test_data_quality.py
────────────────────────────────────────────────────────────────────────────
Data quality assertions using DuckDB in-memory with mock mart tables.
No network calls, no file I/O — runs entirely in process.
────────────────────────────────────────────────────────────────────────────
"""

import duckdb
import pytest


@pytest.fixture
def con():
    c = duckdb.connect(':memory:')

    c.execute("""
        CREATE TABLE mart_team_standings AS
        SELECT
            1          AS team_id,
            'LAL'      AS team_abbreviation,
            'Los Angeles Lakers' AS team_name,
            'West'     AS conference,
            'Pacific'  AS division,
            35         AS wins,
            15         AS losses,
            0.700      AS win_pct,
            1          AS conference_rank,
            1          AS division_rank,
            '24-11'    AS conference_record,
            '20-5'     AS home_record,
            '15-10'    AS road_record,
            115.3      AS avg_pts_scored,
            110.1      AS avg_pts_allowed,
            5.2        AS point_diff,
            'Playoff'  AS playoff_status
        UNION ALL
        SELECT
            2, 'GSW', 'Golden State Warriors', 'West', 'Pacific',
            20, 30, 0.400, 8, 3,
            '14-21', '12-13', '8-17',
            112.0, 114.5, -2.5, 'Play-In'
    """)

    c.execute("""
        CREATE TABLE mart_player_efficiency AS
        SELECT
            1              AS player_id,
            'LeBron James' AS player_name,
            'LAL'          AS team_abbreviation,
            'F'            AS position,
            25.0           AS pts,
            7.0            AS reb,
            8.0            AS ast,
            1.5            AS stl,
            0.5            AS blk,
            3.2            AS turnover,
            18.5           AS per,
            'Star'         AS tier,
            45             AS games_played,
            55.3           AS fantasy_score,
            1              AS overall_rank,
            1              AS team_rank
        UNION ALL
        SELECT
            2, 'Stephen Curry', 'GSW', 'G',
            29.0, 5.0, 6.0, 1.3, 0.2, 3.0,
            21.2, 'Star', 43, 58.1, 2, 1
        UNION ALL
        SELECT
            3, 'Draymond Green', 'GSW', 'F',
            8.5, 7.0, 6.5, 0.9, 1.1, 2.8,
            12.0, 'Role Player', 40, 29.3, 3, 2
    """)

    yield c
    c.close()


# ── mart_team_standings quality ────────────────────────────────────────────────

def test_no_null_team_names(con):
    result = con.execute(
        "SELECT COUNT(*) FROM mart_team_standings WHERE team_name IS NULL"
    ).fetchone()[0]
    assert result == 0


def test_no_null_team_abbreviations(con):
    result = con.execute(
        "SELECT COUNT(*) FROM mart_team_standings WHERE team_abbreviation IS NULL"
    ).fetchone()[0]
    assert result == 0


def test_win_pct_in_range(con):
    result = con.execute(
        "SELECT COUNT(*) FROM mart_team_standings WHERE win_pct < 0 OR win_pct > 1"
    ).fetchone()[0]
    assert result == 0


def test_wins_non_negative(con):
    result = con.execute(
        "SELECT COUNT(*) FROM mart_team_standings WHERE wins < 0"
    ).fetchone()[0]
    assert result == 0


def test_losses_non_negative(con):
    result = con.execute(
        "SELECT COUNT(*) FROM mart_team_standings WHERE losses < 0"
    ).fetchone()[0]
    assert result == 0


def test_standings_conference_valid(con):
    result = con.execute("""
        SELECT COUNT(*) FROM mart_team_standings
        WHERE conference NOT IN ('East', 'West')
    """).fetchone()[0]
    assert result == 0


def test_playoff_status_valid(con):
    result = con.execute("""
        SELECT COUNT(*) FROM mart_team_standings
        WHERE playoff_status NOT IN ('Playoff', 'Play-In', 'Eliminated')
    """).fetchone()[0]
    assert result == 0


def test_standings_row_count(con):
    result = con.execute("SELECT COUNT(*) FROM mart_team_standings").fetchone()[0]
    assert result == 2


# ── mart_player_efficiency quality ─────────────────────────────────────────────

def test_player_pts_positive(con):
    result = con.execute(
        "SELECT COUNT(*) FROM mart_player_efficiency WHERE pts < 0"
    ).fetchone()[0]
    assert result == 0


def test_player_per_not_null(con):
    result = con.execute(
        "SELECT COUNT(*) FROM mart_player_efficiency WHERE per IS NULL"
    ).fetchone()[0]
    assert result == 0


def test_player_tier_valid(con):
    result = con.execute("""
        SELECT COUNT(*) FROM mart_player_efficiency
        WHERE tier NOT IN ('Star', 'Starter', 'Role Player', 'Bench')
    """).fetchone()[0]
    assert result == 0


def test_player_games_played_positive(con):
    result = con.execute(
        "SELECT COUNT(*) FROM mart_player_efficiency WHERE games_played < 0"
    ).fetchone()[0]
    assert result == 0


def test_player_ids_unique(con):
    total = con.execute("SELECT COUNT(*) FROM mart_player_efficiency").fetchone()[0]
    distinct = con.execute(
        "SELECT COUNT(DISTINCT player_id) FROM mart_player_efficiency"
    ).fetchone()[0]
    assert total == distinct


def test_star_players_have_high_per(con):
    result = con.execute("""
        SELECT COUNT(*) FROM mart_player_efficiency
        WHERE tier = 'Star' AND per < 20
    """).fetchone()[0]
    assert result == 0


def test_fantasy_score_not_null(con):
    result = con.execute(
        "SELECT COUNT(*) FROM mart_player_efficiency WHERE fantasy_score IS NULL"
    ).fetchone()[0]
    assert result == 0
