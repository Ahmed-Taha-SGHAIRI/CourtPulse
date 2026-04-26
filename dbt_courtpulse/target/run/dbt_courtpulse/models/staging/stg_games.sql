
  
  create view "courtpulse"."main_staging"."stg_games__dbt_tmp" as (
    -- models/staging/stg_games.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- Staging model for NBA games.
-- Reads all Parquet files from the MinIO-mounted /data/raw/games/ path,
-- casts types, derives winner & point_diff, and filters to completed games.
-- ─────────────────────────────────────────────────────────────────────────────

WITH raw AS (
    SELECT *
    FROM read_parquet('/data/raw/games/**/*.parquet', union_by_name = true)
),

cleaned AS (
    SELECT
        CAST(game_id     AS INTEGER)       AS game_id,
        CAST(game_date   AS DATE)          AS game_date,
        CAST(home_team   AS VARCHAR)       AS home_team,
        CAST(away_team   AS VARCHAR)       AS away_team,
        CAST(home_score  AS INTEGER)       AS home_score,
        CAST(away_score  AS INTEGER)       AS away_score,
        CAST(status      AS VARCHAR)       AS status,
        CAST(season      AS INTEGER)       AS season,

        -- Derived columns
        CASE
            WHEN CAST(home_score AS INTEGER) > CAST(away_score AS INTEGER) THEN home_team
            WHEN CAST(away_score AS INTEGER) > CAST(home_score AS INTEGER) THEN away_team
            ELSE 'Tie'
        END                                AS winner,

        ABS(
            CAST(home_score AS INTEGER) - CAST(away_score AS INTEGER)
        )                                  AS point_diff

    FROM raw
    WHERE status = 'Final'
      AND game_id IS NOT NULL
)

SELECT *
FROM cleaned
  );
