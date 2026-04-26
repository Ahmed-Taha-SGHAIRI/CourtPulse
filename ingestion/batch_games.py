"""
ingestion/batch_games.py
──────────────────────────────────────────────────────────────────────────────
Batch ingestion of NBA game data from balldontlie.io API.

Flow:
  1. Paginate through all 2024-25 games via the balldontlie API
  2. For each completed game, also fetch per-game player stats
  3. Build a normalised DataFrame
  4. Save as Parquet to MinIO → raw/games/YYYY-MM-DD/games.parquet

Rate-limit: 1 second sleep between paginated requests.
Retries:    tenacity — 3 attempts, exponential back-off.
──────────────────────────────────────────────────────────────────────────────
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

# ── Ensure the storage module is importable regardless of CWD ─────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from storage.minio_client import ensure_buckets, upload_parquet  # noqa: E402

# ── Structured JSON logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_URL = "https://www.balldontlie.io/api/v1"
NBA_SEASON = int(os.getenv("NBA_SEASON", "2024"))
PER_PAGE = 100
REQUEST_SLEEP = 1.0  # seconds between paginated requests


# ── HTTP helpers with retry ───────────────────────────────────────────────────
@retry(
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _get_json(url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Perform an HTTP GET and return parsed JSON.  Retried up to 3× with
    exponential back-off on network / HTTP errors.
    """
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


# ── Game fetching ─────────────────────────────────────────────────────────────
def fetch_all_games(season: int = NBA_SEASON) -> List[Dict]:
    """
    Paginate through balldontlie /games endpoint and return all game dicts
    for the requested season.

    Parameters
    ----------
    season : int  NBA season year (e.g. 2024 for the 2024-25 season).

    Returns
    -------
    list[dict]  All raw game records.
    """
    games: List[Dict] = []
    page = 1

    logger.info(f"Fetching games → season={season}")

    while True:
        params = {
            "seasons[]": season,
            "per_page": PER_PAGE,
            "page": page,
        }

        try:
            data = _get_json(f"{BASE_URL}/games", params=params)
        except Exception as exc:
            logger.error(f"Failed to fetch games page {page} → error={exc}")
            break

        batch = data.get("data", [])
        games.extend(batch)
        logger.info(f"Fetched games page {page} → count={len(batch)} total={len(games)}")

        # Pagination cursor
        meta = data.get("meta", {})
        next_page = meta.get("next_page")
        if not next_page:
            break

        page = next_page
        time.sleep(REQUEST_SLEEP)  # respect rate limit

    logger.info(f"Total games fetched → count={len(games)}")
    return games


# ── Stats fetching ────────────────────────────────────────────────────────────
def fetch_stats_for_game(game_id: int) -> List[Dict]:
    """
    Fetch per-player stats for a single completed game.

    Parameters
    ----------
    game_id : int  balldontlie game identifier.

    Returns
    -------
    list[dict]  Player stat records for the game.
    """
    stats: List[Dict] = []
    page = 1

    while True:
        params = {
            "game_ids[]": game_id,
            "per_page": PER_PAGE,
            "page": page,
        }
        try:
            data = _get_json(f"{BASE_URL}/stats", params=params)
        except Exception as exc:
            logger.warning(f"Could not fetch stats → game_id={game_id} error={exc}")
            break

        batch = data.get("data", [])
        stats.extend(batch)

        meta = data.get("meta", {})
        next_page = meta.get("next_page")
        if not next_page:
            break
        page = next_page
        time.sleep(REQUEST_SLEEP)

    return stats


# ── DataFrame builders ────────────────────────────────────────────────────────
def build_games_dataframe(raw_games: List[Dict]) -> pd.DataFrame:
    """
    Normalise raw game dicts into a clean DataFrame.

    Columns: game_id, game_date, home_team, away_team,
             home_score, away_score, status, season.
    """
    rows = []
    for g in raw_games:
        rows.append(
            {
                "game_id": g.get("id"),
                "game_date": g.get("date", "")[:10],  # ISO date only
                "home_team": g.get("home_team", {}).get("full_name", "Unknown"),
                "away_team": g.get("visitor_team", {}).get("full_name", "Unknown"),
                "home_score": g.get("home_team_score", 0),
                "away_score": g.get("visitor_team_score", 0),
                "status": g.get("status", ""),
                "season": g.get("season", NBA_SEASON),
            }
        )
    df = pd.DataFrame(rows)
    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce")
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce").fillna(0).astype(int)
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce").fillna(0).astype(int)
    logger.info(f"Games DataFrame built → rows={len(df)}")
    return df


# ── Main pipeline ─────────────────────────────────────────────────────────────
def run() -> None:
    """
    Full batch ingestion pipeline for NBA games.
    """
    logger.info("Starting batch_games ingestion pipeline")
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # 1. Ensure MinIO buckets exist
    try:
        ensure_buckets(["raw", "streaming", "processed"])
    except Exception as exc:
        logger.error(f"MinIO bucket init failed → error={exc}")

    # 2. Fetch all games
    raw_games = fetch_all_games(season=NBA_SEASON)
    if not raw_games:
        logger.warning("No games returned from API — aborting")
        return

    # 3. Build and upload games DataFrame
    games_df = build_games_dataframe(raw_games)
    try:
        upload_parquet(games_df, "raw", f"games/{today}/games.parquet")
    except Exception as exc:
        logger.error(f"Failed to upload games Parquet → error={exc}")

    # 4. Fetch stats for completed games (limited to first 20 to respect rate limits)
    completed_games = [g for g in raw_games if g.get("status") == "Final"]
    logger.info(f"Completed games found → count={len(completed_games)}")

    all_stats: List[Dict] = []
    for game in completed_games[:20]:  # cap for demo; remove cap for full run
        game_id = game.get("id")
        logger.info(f"Fetching stats → game_id={game_id}")
        stats = fetch_stats_for_game(game_id)
        all_stats.extend(stats)
        time.sleep(REQUEST_SLEEP)

    if all_stats:
        stats_df = pd.json_normalize(all_stats)
        # Rename nested keys produced by json_normalize
        stats_df.columns = [c.replace(".", "_") for c in stats_df.columns]
        try:
            upload_parquet(stats_df, "raw", f"games/{today}/game_stats.parquet")
            logger.info(f"Game stats uploaded → rows={len(stats_df)}")
        except Exception as exc:
            logger.error(f"Failed to upload game stats Parquet → error={exc}")

    logger.info("batch_games ingestion pipeline complete")


if __name__ == "__main__":
    run()
