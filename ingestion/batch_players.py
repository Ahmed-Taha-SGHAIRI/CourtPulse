"""
ingestion/batch_players.py
──────────────────────────────────────────────────────────────────────────────
Batch ingestion of NBA player season averages and team standings.

Sources:
  1. balldontlie.io  /season_averages  — player stats (PPG, RPG, APG, …)
  2. stats.nba.com   leaguestandingsv3 — official league standings

Output:
  - MinIO raw/players/YYYY-MM-DD/season_averages.parquet
  - MinIO raw/standings/YYYY-MM-DD/standings.parquet

Retries: tenacity — 3× with exponential back-off.
Logging: structured JSON.
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

# ── Path fix so storage module resolves from Docker / CLI ────────────────────
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
BDL_BASE = "https://www.balldontlie.io/api/v1"
NBA_STATS_BASE = "https://stats.nba.com/stats"
NBA_SEASON = int(os.getenv("NBA_SEASON", "2024"))
NBA_SEASON_STR = f"{NBA_SEASON}-{str(NBA_SEASON + 1)[-2:]}"  # e.g. "2024-25"
PER_PAGE = 100
REQUEST_SLEEP = 1.0

# Headers required by stats.nba.com to avoid 403
NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.nba.com",
    "Accept": "application/json",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}


# ── HTTP helper with retry ────────────────────────────────────────────────────
@retry(
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _get_json(
    url: str,
    params: Optional[Dict] = None,
    headers: Optional[Dict] = None,
) -> Dict[str, Any]:
    """HTTP GET with retry, returns parsed JSON."""
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url, params=params, headers=headers or {})
        response.raise_for_status()
        return response.json()


# ── Player ID fetching ────────────────────────────────────────────────────────
def fetch_all_player_ids() -> List[int]:
    """
    Fetch all active player IDs from balldontlie /players.

    Returns
    -------
    list[int]  Player IDs.
    """
    ids: List[int] = []
    page = 1

    logger.info("Fetching player IDs from balldontlie")
    while True:
        params = {"per_page": PER_PAGE, "page": page}
        try:
            data = _get_json(f"{BDL_BASE}/players", params=params)
        except Exception as exc:
            logger.error(f"Failed to fetch players page {page} → error={exc}")
            break

        batch = data.get("data", [])
        ids.extend([p["id"] for p in batch if p.get("id")])
        logger.info(f"Player IDs page {page} → fetched={len(batch)} total={len(ids)}")

        meta = data.get("meta", {})
        next_page = meta.get("next_page")
        if not next_page:
            break
        page = next_page
        time.sleep(REQUEST_SLEEP)

    logger.info(f"Total player IDs → count={len(ids)}")
    return ids


# ── Season averages ───────────────────────────────────────────────────────────
def fetch_season_averages(player_ids: List[int], season: int = NBA_SEASON) -> List[Dict]:
    """
    Fetch season averages for up to 100 player IDs per request.

    Parameters
    ----------
    player_ids : list[int]
    season     : int  NBA season year.

    Returns
    -------
    list[dict]
    """
    averages: List[Dict] = []
    chunk_size = 100

    for i in range(0, len(player_ids), chunk_size):
        chunk = player_ids[i : i + chunk_size]
        params: Dict[str, Any] = {"season": season}
        # balldontlie expects repeated query params: player_ids[]=1&player_ids[]=2
        # httpx handles lists correctly when passed as list values
        params["player_ids[]"] = chunk

        try:
            data = _get_json(f"{BDL_BASE}/season_averages", params=params)
            batch = data.get("data", [])
            averages.extend(batch)
            logger.info(
                f"Season averages chunk {i // chunk_size + 1} → fetched={len(batch)}"
            )
        except Exception as exc:
            logger.error(
                f"Season averages fetch failed → chunk_start={i} error={exc}"
            )

        time.sleep(REQUEST_SLEEP)

    logger.info(f"Total season averages → count={len(averages)}")
    return averages


# ── League standings ──────────────────────────────────────────────────────────
def fetch_nba_standings(season: str = NBA_SEASON_STR) -> List[Dict]:
    """
    Fetch league standings from stats.nba.com leaguestandingsv3.

    Parameters
    ----------
    season : str  Season string, e.g. '2024-25'.

    Returns
    -------
    list[dict]  One dict per team row.
    """
    url = f"{NBA_STATS_BASE}/leaguestandingsv3"
    params = {
        "LeagueID": "00",
        "Season": season,
        "SeasonType": "Regular Season",
    }

    logger.info(f"Fetching standings from stats.nba.com → season={season}")
    try:
        data = _get_json(url, params=params, headers=NBA_HEADERS)
    except Exception as exc:
        logger.error(f"Standings fetch failed → error={exc}")
        return []

    # Parse resultSets[0]: map headers → rowSet rows
    result_sets = data.get("resultSets", [])
    if not result_sets:
        logger.warning("No resultSets in standings response")
        return []

    first_set = result_sets[0]
    headers_list: List[str] = first_set.get("headers", [])
    row_set: List[List] = first_set.get("rowSet", [])

    rows = [dict(zip(headers_list, row)) for row in row_set]
    logger.info(f"Standings rows parsed → count={len(rows)}")
    return rows


# ── DataFrame builders ────────────────────────────────────────────────────────
def build_averages_df(raw: List[Dict]) -> pd.DataFrame:
    """Normalise season averages to a clean DataFrame."""
    df = pd.DataFrame(raw)
    numeric_cols = ["pts", "ast", "reb", "stl", "blk", "fgm", "fga", "fg_pct",
                    "fg3m", "fg3a", "fg3_pct", "ftm", "fta", "ft_pct", "oreb",
                    "dreb", "turnover", "pf", "min", "games_played"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    logger.info(f"Season averages DataFrame built → rows={len(df)}")
    return df


def build_standings_df(raw: List[Dict]) -> pd.DataFrame:
    """Normalise standings rows to a clean DataFrame."""
    df = pd.DataFrame(raw)
    numeric_cols = ["WINS", "LOSSES", "WinPCT", "HOME", "ROAD", "L10", "STREAK",
                    "PTS", "OPP_PTS", "PTS_DIFF"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    logger.info(f"Standings DataFrame built → rows={len(df)}")
    return df


# ── Main pipeline ─────────────────────────────────────────────────────────────
def run() -> None:
    """Full batch ingestion pipeline for player stats and standings."""
    logger.info("Starting batch_players ingestion pipeline")
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # 1. Ensure buckets
    try:
        ensure_buckets(["raw", "streaming", "processed"])
    except Exception as exc:
        logger.error(f"MinIO bucket init failed → error={exc}")

    # 2. Player season averages
    player_ids = fetch_all_player_ids()
    if player_ids:
        raw_averages = fetch_season_averages(player_ids, season=NBA_SEASON)
        if raw_averages:
            avg_df = build_averages_df(raw_averages)
            try:
                upload_parquet(
                    avg_df, "raw", f"players/{today}/season_averages.parquet"
                )
            except Exception as exc:
                logger.error(f"Failed to upload player averages → error={exc}")
        else:
            logger.warning("No season averages returned — skipping upload")
    else:
        logger.warning("No player IDs fetched — skipping season averages")

    # 3. League standings from stats.nba.com
    raw_standings = fetch_nba_standings(season=NBA_SEASON_STR)
    if raw_standings:
        standings_df = build_standings_df(raw_standings)
        try:
            upload_parquet(
                standings_df, "raw", f"standings/{today}/standings.parquet"
            )
        except Exception as exc:
            logger.error(f"Failed to upload standings → error={exc}")
    else:
        logger.warning("No standings data returned — skipping upload")

    logger.info("batch_players ingestion pipeline complete")


if __name__ == "__main__":
    run()
