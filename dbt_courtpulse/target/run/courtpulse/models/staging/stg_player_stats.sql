
  
  create view "courtpulse"."main"."stg_player_stats__dbt_tmp" as (
    WITH players AS (
    SELECT * FROM read_parquet('/data/parquet/players/active_players.parquet')
),
avgs AS (
    SELECT * FROM read_parquet('/data/parquet/players/season_averages_2024.parquet')
)
SELECT
    p.player_id,
    p.full_name AS player_name,
    p.position,
    p.team_name,
    p.team_abbreviation,
    p.team_conference,
    p.team_division,
    a.season,
    COALESCE(a.games_played, 0) AS games_played,
    COALESCE(a.pts, 0.0) AS pts,
    COALESCE(a.reb, 0.0) AS reb,
    COALESCE(a.ast, 0.0) AS ast,
    COALESCE(a.stl, 0.0) AS stl,
    COALESCE(a.blk, 0.0) AS blk,
    COALESCE(a.turnover, 0.0) AS turnover,
    COALESCE(a.fg_pct, 0.0) AS fg_pct,
    COALESCE(a.fg3_pct, 0.0) AS fg3_pct,
    COALESCE(a.ft_pct, 0.0) AS ft_pct,
    COALESCE(a.fga, 0.0) AS fga,
    COALESCE(a.fgm, 0.0) AS fgm,
    COALESCE(a.fta, 0.0) AS fta,
    COALESCE(a.ftm, 0.0) AS ftm,
    ROUND(
        COALESCE(a.pts, 0)
        + (COALESCE(a.reb, 0)      * 1.2)
        + (COALESCE(a.ast, 0)      * 1.5)
        + (COALESCE(a.stl, 0)      * 3.0)
        + (COALESCE(a.blk, 0)      * 3.0)
        - (COALESCE(a.turnover, 0) * 1.0),
    2) AS fantasy_score
FROM players p
LEFT JOIN avgs a USING (player_id)
  );
