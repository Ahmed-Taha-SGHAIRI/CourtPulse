WITH raw AS (
    SELECT * FROM read_parquet('/data/parquet/games/season=2024/games.parquet')
)
SELECT
    game_id,
    game_date::DATE AS game_date,
    season,
    status,
    home_team_id,
    home_team_name,
    home_team_abbr,
    visitor_team_id,
    visitor_team_name,
    visitor_team_abbr,
    COALESCE(home_score, 0)    AS home_score,
    COALESCE(visitor_score, 0) AS visitor_score,
    postseason,
    CASE
        WHEN home_score > visitor_score THEN home_team_name
        ELSE visitor_team_name
    END AS winner,
    ABS(home_score - visitor_score) AS point_diff
FROM raw
WHERE status ILIKE '%final%'
