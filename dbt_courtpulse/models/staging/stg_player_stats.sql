-- models/staging/stg_player_stats.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- Staging model for NBA player season averages.
-- Reads all Parquet files from /data/raw/players/, casts stats to FLOAT,
-- computes fantasy_score, and filters to players with ≥ 10 games played.
-- ─────────────────────────────────────────────────────────────────────────────

WITH raw AS (
    SELECT *
    FROM read_parquet('/data/raw/players/**/*.parquet', union_by_name = true)
),

cleaned AS (
    SELECT
        CAST(player_id      AS INTEGER)    AS player_id,
        CAST(season         AS INTEGER)    AS season,
        CAST(games_played   AS INTEGER)    AS games_played,
        CAST(min            AS FLOAT)      AS min,
        CAST(pts            AS FLOAT)      AS pts,
        CAST(reb            AS FLOAT)      AS reb,
        CAST(ast            AS FLOAT)      AS ast,
        CAST(stl            AS FLOAT)      AS stl,
        CAST(blk            AS FLOAT)      AS blk,
        CAST(fgm            AS FLOAT)      AS fgm,
        CAST(fga            AS FLOAT)      AS fga,
        CAST(fg_pct         AS FLOAT)      AS fg_pct,
        CAST(fg3m           AS FLOAT)      AS fg3m,
        CAST(fg3a           AS FLOAT)      AS fg3a,
        CAST(fg3_pct        AS FLOAT)      AS fg3_pct,
        CAST(ftm            AS FLOAT)      AS ftm,
        CAST(fta            AS FLOAT)      AS fta,
        CAST(ft_pct         AS FLOAT)      AS ft_pct,
        CAST(oreb           AS FLOAT)      AS oreb,
        CAST(dreb           AS FLOAT)      AS dreb,
        CAST(turnover       AS FLOAT)      AS turnover,
        COALESCE(CAST(player_team AS VARCHAR), 'Unknown')  AS team,

        -- Fantasy score formula
        -- pts + (reb × 1.2) + (ast × 1.5) + (stl × 3) + (blk × 3)
        (
            CAST(pts  AS FLOAT)
            + (CAST(reb AS FLOAT) * 1.2)
            + (CAST(ast AS FLOAT) * 1.5)
            + (CAST(stl AS FLOAT) * 3.0)
            + (CAST(blk AS FLOAT) * 3.0)
        )                                  AS fantasy_score

    FROM raw
    WHERE CAST(games_played AS INTEGER) >= 10
      AND player_id IS NOT NULL
)

SELECT *
FROM cleaned
