-- models/marts/mart_hot_cold_streaks.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- Transform 3: 5-game rolling win rate per team using window functions.
--
-- Streak labels (based on rolling_win_rate over the last 5 games):
--   On Fire  : rolling_win_rate >= 0.80
--   Hot      : 0.60 <= rolling_win_rate < 0.80
--   Lukewarm : 0.40 <= rolling_win_rate < 0.60
--   Cold     : 0.20 <= rolling_win_rate < 0.40
--   Freezing : rolling_win_rate < 0.20
-- ─────────────────────────────────────────────────────────────────────────────

WITH games AS (
    SELECT * FROM {{ ref('stg_games') }}
),

-- Expand into team-level game rows
team_games AS (
    SELECT
        game_id,
        game_date,
        home_team  AS team,
        winner,
        CASE WHEN winner = home_team THEN 1 ELSE 0 END AS is_win
    FROM games

    UNION ALL

    SELECT
        game_id,
        game_date,
        away_team  AS team,
        winner,
        CASE WHEN winner = away_team THEN 1 ELSE 0 END AS is_win
    FROM games
),

-- Add row number per team ordered by date (most recent first)
numbered AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY team ORDER BY game_date DESC) AS game_rn
    FROM team_games
),

-- 5-game rolling win rate (last 5 games including current row)
rolling AS (
    SELECT
        team,
        game_date,
        game_id,
        is_win,
        game_rn,

        ROUND(
            AVG(CAST(is_win AS FLOAT)) OVER (
                PARTITION BY team
                ORDER BY game_date
                ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
            ),
        3) AS rolling_win_rate,

        -- How many games contributed to the window (handles early-season)
        COUNT(*) OVER (
            PARTITION BY team
            ORDER BY game_date
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ) AS window_games

    FROM numbered
),

-- Keep only the most recent row per team (latest rolling state)
latest AS (
    SELECT *
    FROM rolling
    QUALIFY ROW_NUMBER() OVER (PARTITION BY team ORDER BY game_date DESC) = 1
),

-- Add streak label
labelled AS (
    SELECT
        team,
        game_date         AS as_of_date,
        rolling_win_rate,
        window_games,

        CASE
            WHEN rolling_win_rate >= 0.80 THEN 'On Fire'
            WHEN rolling_win_rate >= 0.60 THEN 'Hot'
            WHEN rolling_win_rate >= 0.40 THEN 'Lukewarm'
            WHEN rolling_win_rate >= 0.20 THEN 'Cold'
            ELSE 'Freezing'
        END AS streak_label

    FROM latest
)

SELECT *
FROM labelled
ORDER BY rolling_win_rate DESC
