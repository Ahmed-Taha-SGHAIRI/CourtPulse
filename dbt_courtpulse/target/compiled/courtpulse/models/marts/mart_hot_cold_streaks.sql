WITH games AS (SELECT * FROM "courtpulse"."main"."stg_games"),
team_games AS (
    SELECT home_team_name AS team_name, home_team_abbr AS team_abbr,
           game_date, CASE WHEN winner = home_team_name THEN 1 ELSE 0 END AS won
    FROM games
    UNION ALL
    SELECT visitor_team_name, visitor_team_abbr,
           game_date, CASE WHEN winner = visitor_team_name THEN 1 ELSE 0 END
    FROM games
),
with_rolling AS (
    SELECT *,
        ROUND(AVG(won::FLOAT) OVER (
            PARTITION BY team_name ORDER BY game_date
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ), 3) AS rolling_5game_win_rate,
        ROW_NUMBER() OVER (PARTITION BY team_name ORDER BY game_date DESC) AS rn
    FROM team_games
),
latest AS (SELECT * FROM with_rolling WHERE rn = 1)
SELECT
    team_name, team_abbr,
    rolling_5game_win_rate,
    CASE
        WHEN rolling_5game_win_rate >= 0.8 THEN 'On Fire'
        WHEN rolling_5game_win_rate >= 0.6 THEN 'Hot'
        WHEN rolling_5game_win_rate >= 0.4 THEN 'Lukewarm'
        WHEN rolling_5game_win_rate >= 0.2 THEN 'Cold'
        ELSE 'Freezing'
    END AS streak_label
FROM latest
ORDER BY rolling_5game_win_rate DESC