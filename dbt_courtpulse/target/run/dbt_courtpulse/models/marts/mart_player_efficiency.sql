
  
    
    

    create  table
      "courtpulse"."main_marts"."mart_player_efficiency__dbt_tmp"
  
    as (
      -- models/marts/mart_player_efficiency.sql
-- ─────────────────────────────────────────────────────────────────────────────
-- Transform 1: Player Efficiency Rating (simplified PER), team rank, tier.
--
-- Simplified PER formula (scaled to approximate NBA PER range):
--   PER = (pts + reb*1.2 + ast*1.5 + stl*3 + blk*3 - turnover*1.5) / games_played * (82/games_played)^0.1
-- We use a practical approximation that is deterministic and interpretable.
-- ─────────────────────────────────────────────────────────────────────────────

WITH base AS (
    SELECT *
    FROM "courtpulse"."main_staging"."stg_player_stats"
    WHERE games_played > 0
),

per_calc AS (
    SELECT
        player_id,
        season,
        team,
        games_played,
        min,
        pts,
        reb,
        ast,
        stl,
        blk,
        turnover,
        fg_pct,
        fg3_pct,
        ft_pct,
        fantasy_score,

        -- Simplified PER calculation
        ROUND(
            (
                pts
                + (reb  * 1.2)
                + (ast  * 1.5)
                + (stl  * 3.0)
                + (blk  * 3.0)
                - (turnover * 1.5)
            ) / NULLIF(games_played, 0),
        2) AS per

    FROM base
),

ranked AS (
    SELECT
        *,
        -- Rank within team by PER (1 = best)
        ROW_NUMBER() OVER (
            PARTITION BY team
            ORDER BY per DESC NULLS LAST
        ) AS team_rank,

        -- Overall rank across all players
        ROW_NUMBER() OVER (
            ORDER BY per DESC NULLS LAST
        ) AS overall_rank,

        -- Tier classification based on PER
        CASE
            WHEN per >= 20 THEN 'Star'
            WHEN per >= 15 THEN 'Starter'
            WHEN per >= 10 THEN 'Role Player'
            ELSE 'Bench'
        END AS tier

    FROM per_calc
)

SELECT *
FROM ranked
ORDER BY per DESC NULLS LAST
    );
  
  