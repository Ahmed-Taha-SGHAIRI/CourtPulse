WITH games AS (SELECT * FROM "courtpulse"."main"."stg_games"),
teams AS (
    SELECT * FROM read_parquet('/data/parquet/teams/teams.parquet')
),
home_stats AS (
    SELECT 
        home_team_id AS team_id,
        COUNT(*) AS gp,
        SUM(CASE WHEN home_score > visitor_score THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN home_score < visitor_score THEN 1 ELSE 0 END) AS losses,
        AVG(home_score) AS pts_scored,
        AVG(visitor_score) AS pts_allowed
    FROM games
    GROUP BY 1
),
visitor_stats AS (
    SELECT 
        visitor_team_id AS team_id,
        COUNT(*) AS gp,
        SUM(CASE WHEN visitor_score > home_score THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN visitor_score < home_score THEN 1 ELSE 0 END) AS losses,
        AVG(visitor_score) AS pts_scored,
        AVG(home_score) AS pts_allowed
    FROM games
    GROUP BY 1
),
combined AS (
    SELECT team_id, gp, wins, losses, pts_scored, pts_allowed FROM home_stats
    UNION ALL
    SELECT team_id, gp, wins, losses, pts_scored, pts_allowed FROM visitor_stats
),
final_agg AS (
    SELECT 
        team_id,
        SUM(gp) AS gp,
        SUM(wins) AS wins,
        SUM(losses) AS losses,
        AVG(pts_scored) AS avg_pts_scored,
        AVG(pts_allowed) AS avg_pts_allowed
    FROM combined
    GROUP BY 1
)
SELECT 
    t.team_id,
    t.team_name,
    t.team_abbreviation,
    t.conference,
    t.division,
    f.wins,
    f.losses,
    ROUND(f.wins::FLOAT / NULLIF(f.wins + f.losses, 0), 3) AS win_pct,
    DENSE_RANK() OVER (PARTITION BY t.conference ORDER BY f.wins DESC, f.losses ASC) AS conference_rank,
    DENSE_RANK() OVER (PARTITION BY t.division ORDER BY f.wins DESC, f.losses ASC) AS division_rank,
    '0-0' AS conference_record,
    '0-0' AS home_record,
    '0-0' AS road_record,
    ROUND(f.avg_pts_scored, 1) AS avg_pts_scored,
    ROUND(f.avg_pts_allowed, 1) AS avg_pts_allowed,
    ROUND(f.avg_pts_scored - f.avg_pts_allowed, 1) AS point_diff,
    CASE 
        WHEN DENSE_RANK() OVER (PARTITION BY t.conference ORDER BY f.wins DESC, f.losses ASC) <= 6 THEN 'Playoff'
        WHEN DENSE_RANK() OVER (PARTITION BY t.conference ORDER BY f.wins DESC, f.losses ASC) <= 10 THEN 'Play-In'
        ELSE 'Eliminated'
    END AS playoff_status
FROM final_agg f
JOIN teams t USING (team_id)
ORDER BY t.conference, conference_rank