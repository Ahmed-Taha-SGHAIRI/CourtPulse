"""
ingestion/batch_games.py
────────────────────────────────────────────────────────────────────────────
Batch ingestion of NBA games and per-game player stats from balldontlie API.

Flow:
  1. Paginate /nba/v1/games for the 2024 season (cursor-based pagination).
  2. For every completed game, fetch per-player stats via /nba/v1/stats.
  3. Persist both DataFrames to:
       MinIO  → raw/games/season=2024/games.parquet
                raw/stats/season=2024/stats.parquet
       local  → /data/parquet/games/season=2024/games.parquet
                /data/parquet/stats/season=2024/stats.parquet
       (the local path is the shared Docker volume read by dbt)
────────────────────────────────────────────────────────────────────────────
"""

import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from storage.minio_client import get_client, upload_parquet  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.balldontlie.io"
NBA_SEASON = int(os.environ.get("NBA_SEASON", "2024"))
PER_PAGE = 100


# ── HTTP helper ───────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _get_json(url: str, headers: Dict[str, str], params: Optional[Dict] = None) -> Dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            logger.error(f"API Error {resp.status_code} for {url}: {resp.text}")
        resp.raise_for_status()
        return resp.json()


# ── Games ─────────────────────────────────────────────────────────────────────

def fetch_all_games(headers: Dict[str, str]) -> List[Dict]:
    """Cursor-paginate /nba/v1/games for the 2024 season."""
    games: List[Dict] = []
    cursor: Optional[int] = None

    while True:
        params: Dict[str, Any] = {"seasons[]": NBA_SEASON, "per_page": PER_PAGE}
        if cursor is not None:
            params["cursor"] = cursor

        try:
            data = _get_json(f"{BASE_URL}/v1/games", headers=headers, params=params)
        except Exception as exc:
            logger.error(f"Failed to fetch games page cursor={cursor}: {exc}")
            break

        batch = data.get("data", [])
        games.extend(batch)
        logger.info(f"Fetched {len(batch)} games (cursor={cursor}), total={len(games)}")

        next_cursor = data.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break
        cursor = next_cursor
        time.sleep(0.5)

    logger.info(f"Total games fetched: {len(games)}")
    return games


def build_games_df(raw: List[Dict]) -> pd.DataFrame:
    rows = []
    for g in raw:
        ht = g.get("home_team", {})
        vt = g.get("visitor_team", {})
        rows.append({
            "game_id": g.get("id"),
            "game_date": (g.get("date") or "")[:10],
            "season": g.get("season", NBA_SEASON),
            "status": g.get("status", ""),
            "home_team_id": ht.get("id"),
            "home_team_name": ht.get("full_name", ""),
            "home_team_abbr": ht.get("abbreviation", ""),
            "visitor_team_id": vt.get("id"),
            "visitor_team_name": vt.get("full_name", ""),
            "visitor_team_abbr": vt.get("abbreviation", ""),
            "home_score": g.get("home_team_score", 0) or 0,
            "visitor_score": g.get("visitor_team_score", 0) or 0,
            "postseason": bool(g.get("postseason", False)),
        })
    df = pd.DataFrame(rows)
    for col in ["home_score", "visitor_score"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


# ── Stats ─────────────────────────────────────────────────────────────────────

def fetch_stats_for_game(game_id: int, headers: Dict[str, str]) -> List[Dict]:
    stats: List[Dict] = []
    params: Dict[str, Any] = {
        "seasons[]": NBA_SEASON,
        "game_ids[]": game_id,
        "per_page": PER_PAGE
    }
    try:
        data = _get_json(f"{BASE_URL}/v1/stats", headers=headers, params=params)
        stats.extend(data.get("data", []))
    except Exception as exc:
        logger.warning(f"Could not fetch stats for game_id={game_id}: {exc}")
    return stats


def build_stats_df(raw_stats: List[Dict]) -> pd.DataFrame:
    rows = []
    for s in raw_stats:
        p = s.get("player", {})
        t = s.get("team", {})
        g = s.get("game", {})
        rows.append({
            "stat_id": s.get("id"),
            "game_id": g.get("id"),
            "player_id": p.get("id"),
            "player_name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "team_id": t.get("id"),
            "team_abbr": t.get("abbreviation", ""),
            "min": s.get("min", ""),
            "pts": int(s.get("pts") or 0),
            "reb": int(s.get("reb") or 0),
            "ast": int(s.get("ast") or 0),
            "stl": int(s.get("stl") or 0),
            "blk": int(s.get("blk") or 0),
            "turnover": int(s.get("turnover") or 0),
            "fgm": int(s.get("fgm") or 0),
            "fga": int(s.get("fga") or 0),
            "fg_pct": float(s.get("fg_pct") or 0.0),
            "fg3m": int(s.get("fg3m") or 0),
            "fg3a": int(s.get("fg3a") or 0),
            "fg3_pct": float(s.get("fg3_pct") or 0.0),
            "ftm": int(s.get("ftm") or 0),
            "fta": int(s.get("fta") or 0),
            "ft_pct": float(s.get("ft_pct") or 0.0),
            "oreb": int(s.get("oreb") or 0),
            "dreb": int(s.get("dreb") or 0),
            "pf": int(s.get("pf") or 0),
        })
    return pd.DataFrame(rows)


# ── Local parquet writer ──────────────────────────────────────────────────────

def save_local(df: pd.DataFrame, object_path: str) -> None:
    """Write parquet to /data/parquet/<object_path> for dbt to read."""
    local_path = f"/data/parquet/{object_path}"
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    df.to_parquet(local_path, index=False)
    logger.info(f"Saved local parquet: {local_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    headers = {"Authorization": os.environ["BALLDONTLIE_API_KEY"]}
    minio = get_client()

    # --- Games ---
    raw_games = fetch_all_games(headers)
    if not raw_games:
        logger.warning("No games returned; aborting.")
        return

    games_df = build_games_df(raw_games)
    games_path = "games/season=2024/games.parquet"
    upload_parquet(minio, games_df, "raw", games_path)
    save_local(games_df, games_path)
    logger.info(f"Games saved: {len(games_df)} rows")

    # --- Stats for completed games ---
    completed = [g for g in raw_games if "final" in (g.get("status") or "").lower()]
    logger.info(f"Completed games: {len(completed)}")

    all_stats: List[Dict] = []
    for game in completed:
        gid = game.get("id")
        stats = fetch_stats_for_game(gid, headers)
        all_stats.extend(stats)
        time.sleep(0.5)

    if all_stats:
        stats_df = build_stats_df(all_stats)
        stats_path = "stats/season=2024/stats.parquet"
        upload_parquet(minio, stats_df, "raw", stats_path)
        save_local(stats_df, stats_path)
        logger.info(f"Stats saved: {len(stats_df)} rows")
    else:
        logger.warning("No stats to save.")


if __name__ == "__main__":
    load_dotenv()
    main()
