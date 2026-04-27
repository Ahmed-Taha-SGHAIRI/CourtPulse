WITH base AS (SELECT * FROM "courtpulse"."main"."stg_player_stats"),
per_calc AS (
    SELECT *,
        CASE
            WHEN games_played = 0 THEN 0
            ELSE ROUND(
                (pts + (reb * 1.2) + (ast * 1.5) + stl + blk - (fga - fgm) - turnover),
            2)
        END AS per
    FROM base
),
ranked AS (
    SELECT *,
        RANK() OVER (PARTITION BY team_abbreviation ORDER BY per DESC) AS team_rank,
        RANK() OVER (ORDER BY per DESC)                                AS overall_rank
    FROM per_calc
)
SELECT *,
    CASE
        WHEN per >= 40 THEN 'Star'
        WHEN per >= 30 THEN 'Starter'
        WHEN per >= 20 THEN 'Role Player'
        ELSE 'Bench'
    END AS tier
FROM ranked
ORDER BY per DESC