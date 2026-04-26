"""
ingestion/generate_mock_data.py
──────────────────────────────────────────────────────────────────────────────
Seeds realistic mock NBA data directly into the /data volume so that the
dbt staging models (which read from read_parquet('/data/raw/...')) can
produce populated mart tables without requiring the real API or MinIO.

Writes:
  /data/raw/games/YYYY-MM-DD/games.parquet        — 30-team season schedule
  /data/raw/games/YYYY-MM-DD/game_stats.parquet   — per-game player stats
  /data/raw/players/YYYY-MM-DD/season_averages.parquet
  /data/raw/standings/YYYY-MM-DD/standings.parquet
──────────────────────────────────────────────────────────────────────────────
"""

import os
import random
from datetime import datetime, timedelta

import pandas as pd

random.seed(42)

TODAY = datetime.utcnow().strftime("%Y-%m-%d")
SEASON = 2024

# ── All 30 NBA teams ──────────────────────────────────────────────────────────
TEAMS = [
    "Boston Celtics", "Miami Heat", "Milwaukee Bucks", "Philadelphia 76ers",
    "New York Knicks", "Cleveland Cavaliers", "Orlando Magic", "Indiana Pacers",
    "Chicago Bulls", "Toronto Raptors", "Brooklyn Nets", "Atlanta Hawks",
    "Charlotte Hornets", "Washington Wizards", "Detroit Pistons",
    "Oklahoma City Thunder", "Denver Nuggets", "Minnesota Timberwolves",
    "Los Angeles Clippers", "Los Angeles Lakers", "Golden State Warriors",
    "Phoenix Suns", "Sacramento Kings", "Dallas Mavericks", "Memphis Grizzlies",
    "New Orleans Pelicans", "Utah Jazz", "Portland Trail Blazers",
    "San Antonio Spurs", "Houston Rockets",
]

# ── Generate a realistic 60-game slice of the season ─────────────────────────
def generate_games():
    games = []
    game_id = 1
    start_date = datetime(2024, 10, 22)

    # Round-robin: each adjacent pair plays once, repeat 2 rounds
    pairs = []
    for i in range(0, len(TEAMS) - 1, 2):
        pairs.append((TEAMS[i], TEAMS[i + 1]))
    for i in range(1, len(TEAMS) - 1, 2):
        pairs.append((TEAMS[i], TEAMS[i + 2] if i + 2 < len(TEAMS) else TEAMS[0]))

    day_offset = 0
    for _ in range(15):         # 15 rounds → each player appears ~15 times (> 10 threshold)
        random.shuffle(pairs)
        for home, away in pairs:
            home_score = random.randint(95, 135)
            away_score = random.randint(95, 135)
            # Avoid ties
            while home_score == away_score:
                away_score = random.randint(95, 135)

            games.append({
                "game_id":   game_id,
                "game_date": (start_date + timedelta(days=day_offset)).strftime("%Y-%m-%d"),
                "home_team": home,
                "away_team": away,
                "home_score": home_score,
                "away_score": away_score,
                "status":    "Final",
                "season":    SEASON,
            })
            game_id += 1
            day_offset += 1

    return pd.DataFrame(games)


# ── Generate player stats for each game ──────────────────────────────────────
def generate_game_stats(games_df: pd.DataFrame) -> pd.DataFrame:
    """Create 5 player-stat rows per team per game (10 rows per game)."""
    rows = []
    player_id = 1
    # Fixed player pool per team (5 players each)
    team_players: dict = {}
    for team in TEAMS:
        team_players[team] = list(range(player_id, player_id + 5))
        player_id += 5

    for _, g in games_df.iterrows():
        for team in [g["home_team"], g["away_team"]]:
            for pid in team_players[team]:
                pts   = round(random.uniform(4, 38), 1)
                reb   = round(random.uniform(1, 14), 1)
                ast   = round(random.uniform(0, 12), 1)
                stl   = round(random.uniform(0, 3),  1)
                blk   = round(random.uniform(0, 3),  1)
                to    = round(random.uniform(0, 5),  1)
                fgm   = random.randint(2, 14)
                fga   = fgm + random.randint(1, 8)
                fg3m  = random.randint(0, 6)
                fg3a  = fg3m + random.randint(0, 5)
                ftm   = random.randint(0, 10)
                fta   = ftm + random.randint(0, 4)
                rows.append({
                    "game_id":    int(g["game_id"]),
                    "player_id":  pid,
                    "player_team": team,
                    "season":     SEASON,
                    "pts":  pts, "reb": reb, "ast": ast,
                    "stl":  stl, "blk": blk, "turnover": to,
                    "fgm":  fgm, "fga": fga,
                    "fg_pct": round(fgm / fga, 3) if fga > 0 else 0,
                    "fg3m": fg3m, "fg3a": fg3a,
                    "fg3_pct": round(fg3m / fg3a, 3) if fg3a > 0 else 0,
                    "ftm": ftm, "fta": fta,
                    "ft_pct": round(ftm / fta, 3) if fta > 0 else 0,
                    "oreb": round(random.uniform(0, 4), 1),
                    "dreb": round(random.uniform(0, 8), 1),
                    "min":  round(random.uniform(12, 38), 1),
                    "games_played": 1,
                })
    return pd.DataFrame(rows)


# ── Aggregate to season averages ──────────────────────────────────────────────
def generate_season_averages(stats_df: pd.DataFrame) -> pd.DataFrame:
    agg = stats_df.groupby(["player_id", "player_team", "season"]).agg(
        games_played=("game_id", "count"),
        pts=("pts", "mean"),
        reb=("reb", "mean"),
        ast=("ast", "mean"),
        stl=("stl", "mean"),
        blk=("blk", "mean"),
        turnover=("turnover", "mean"),
        fgm=("fgm", "mean"),
        fga=("fga", "mean"),
        fg_pct=("fg_pct", "mean"),
        fg3m=("fg3m", "mean"),
        fg3a=("fg3a", "mean"),
        fg3_pct=("fg3_pct", "mean"),
        ftm=("ftm", "mean"),
        fta=("fta", "mean"),
        ft_pct=("ft_pct", "mean"),
        oreb=("oreb", "mean"),
        dreb=("dreb", "mean"),
        min=("min", "mean"),
    ).reset_index()
    agg.rename(columns={"player_team": "player_team"}, inplace=True)
    # Round averages
    for col in ["pts", "reb", "ast", "stl", "blk", "turnover", "min"]:
        agg[col] = agg[col].round(1)
    return agg


# ── Main ──────────────────────────────────────────────────────────────────────
def generate_mock_data():
    print("🏀  Generating CourtPulse mock data …")

    # Ensure output directories exist
    for folder in [
        f"/data/raw/games/{TODAY}",
        f"/data/raw/players/{TODAY}",
        f"/data/raw/standings/{TODAY}",
    ]:
        os.makedirs(folder, exist_ok=True)

    # 1. Games
    games_df = generate_games()
    games_df["game_date"] = pd.to_datetime(games_df["game_date"])
    games_df.to_parquet(f"/data/raw/games/{TODAY}/games.parquet", index=False)
    print(f"  ✔ {len(games_df)} games → /data/raw/games/{TODAY}/games.parquet")

    # 2. Per-game player stats
    stats_df = generate_game_stats(games_df)
    stats_df.to_parquet(f"/data/raw/games/{TODAY}/game_stats.parquet", index=False)
    print(f"  ✔ {len(stats_df)} game-stat rows → /data/raw/games/{TODAY}/game_stats.parquet")

    # 3. Season averages (used by stg_player_stats)
    averages_df = generate_season_averages(stats_df)
    # stg_player_stats filters games_played >= 10
    averages_df = averages_df[averages_df["games_played"] >= 10]
    averages_df.to_parquet(f"/data/raw/players/{TODAY}/season_averages.parquet", index=False)
    print(f"  ✔ {len(averages_df)} player-avg rows → /data/raw/players/{TODAY}/season_averages.parquet")

    # 4. Standings snapshot (informational; dbt computes standings from games)
    standings_rows = []
    for team in TEAMS:
        team_games = games_df[(games_df["home_team"] == team) | (games_df["away_team"] == team)]
        wins = sum(
            1 for _, r in team_games.iterrows()
            if (r["home_team"] == team and r["home_score"] > r["away_score"])
            or (r["away_team"] == team and r["away_score"] > r["home_score"])
        )
        losses = len(team_games) - wins
        standings_rows.append({
            "TEAM_NAME": team,
            "WINS": wins,
            "LOSSES": losses,
            "WinPCT": round(wins / max(len(team_games), 1), 3),
            "SEASON": SEASON,
        })
    standings_df = pd.DataFrame(standings_rows)
    standings_df.to_parquet(f"/data/raw/standings/{TODAY}/standings.parquet", index=False)
    print(f"  ✔ {len(standings_df)} standings rows → /data/raw/standings/{TODAY}/standings.parquet")

    print("✅  Mock data generation complete!")


if __name__ == "__main__":
    generate_mock_data()
