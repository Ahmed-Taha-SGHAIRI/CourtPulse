-- models/marts/mart_team_standings.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- Transform 2: Team standings derived from completed game records.
-- ─────────────────────────────────────────────────────────────────────────────

WITH games AS (
    SELECT * FROM "courtpulse"."main_staging"."stg_games"
),

-- Expand each game into two rows: one per team perspective
team_games AS (
    SELECT
        game_id,
        game_date,
        home_team  AS team,
        away_team  AS opponent,
        home_score AS pts_scored,
        away_score AS pts_allowed,
        winner,
        'home'     AS venue
    FROM games

    UNION ALL

    SELECT
        game_id,
        game_date,
        away_team  AS team,
        home_team  AS opponent,
        away_score AS pts_scored,
        home_score AS pts_allowed,
        winner,
        'away'     AS venue
    FROM games
),

-- Annotate win/loss
team_results AS (
    SELECT
        *,
        CASE WHEN winner = team THEN 1 ELSE 0 END AS is_win,
        CASE WHEN winner = team THEN 0 ELSE 1 END AS is_loss
    FROM team_games
),

-- Aggregate standing stats
aggregated AS (
    SELECT
        team,
        SUM(is_win)                                        AS wins,
        SUM(is_loss)                                       AS losses,
        COUNT(*)                                           AS games_played,
        ROUND(SUM(is_win) * 1.0 / NULLIF(COUNT(*), 0), 3) AS win_pct,
        ROUND(AVG(pts_scored),  1)                         AS avg_pts_scored,
        ROUND(AVG(pts_allowed), 1)                         AS avg_pts_allowed,
        SUM(CASE WHEN venue = 'home' AND is_win  = 1 THEN 1 ELSE 0 END) AS home_wins,
        SUM(CASE WHEN venue = 'home' AND is_loss = 1 THEN 1 ELSE 0 END) AS home_losses,
        SUM(CASE WHEN venue = 'away' AND is_win  = 1 THEN 1 ELSE 0 END) AS away_wins,
        SUM(CASE WHEN venue = 'away' AND is_loss = 1 THEN 1 ELSE 0 END) AS away_losses
    FROM team_results
    GROUP BY team
),

-- ── Streak calculation ────────────────────────────────────────────────────────
-- Step 1: For each game per team (newest first), get the previous game's is_win
--         using a plain LAG window (no nesting).
streak_with_lag AS (
    SELECT
        team,
        game_date,
        is_win,
        LAG(is_win, 1, is_win) OVER (
            PARTITION BY team ORDER BY game_date DESC
        ) AS prev_is_win
    FROM team_results
),

-- Step 2: Mark where a flip occurs (current != previous)
streak_with_flip AS (
    SELECT
        team,
        game_date,
        is_win,
        CASE WHEN is_win != prev_is_win THEN 1 ELSE 0 END AS flipped
    FROM streak_with_lag
),

-- Step 3: Running sum of flips gives a group ID per streak run (newest first)
streak_grouped AS (
    SELECT
        team,
        game_date,
        is_win,
        SUM(flipped) OVER (
            PARTITION BY team ORDER BY game_date DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS grp
    FROM streak_with_flip
),

-- Step 4: Count games in group 0 = the current active streak
streak_summary AS (
    SELECT
        team,
        MAX(is_win) AS streak_win,
        COUNT(*)    AS streak_length
    FROM streak_grouped
    WHERE grp = 0
    GROUP BY team
),

-- Final: join aggregated stats with streak
final AS (
    SELECT
        a.team,
        a.wins,
        a.losses,
        a.games_played,
        a.win_pct,
        a.avg_pts_scored,
        a.avg_pts_allowed,
        ROUND(a.avg_pts_scored - a.avg_pts_allowed, 1) AS avg_point_diff,
        CONCAT(CAST(a.home_wins   AS VARCHAR), '-', CAST(a.home_losses AS VARCHAR)) AS home_record,
        CONCAT(CAST(a.away_wins   AS VARCHAR), '-', CAST(a.away_losses AS VARCHAR)) AS away_record,
        ROW_NUMBER() OVER (ORDER BY a.win_pct DESC, a.wins DESC) AS overall_seed,
        CASE
            WHEN ROW_NUMBER() OVER (ORDER BY a.win_pct DESC, a.wins DESC) <= 6  THEN 'Playoff'
            WHEN ROW_NUMBER() OVER (ORDER BY a.win_pct DESC, a.wins DESC) <= 10 THEN 'Play-In'
            ELSE 'Eliminated'
        END AS playoff_position,
        COALESCE(
            CASE WHEN s.streak_win = 1 THEN s.streak_length
                 ELSE -s.streak_length
            END, 0
        ) AS current_streak
    FROM aggregated a
    LEFT JOIN streak_summary s ON s.team = a.team
)

SELECT *
FROM final
ORDER BY win_pct DESC, wins DESC