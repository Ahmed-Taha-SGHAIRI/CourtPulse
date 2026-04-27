"""
ingestion/batch_players.py
────────────────────────────────────────────────────────────────────────────
Batch ingestion of active players, season averages, and standings.

Saves to:
  MinIO  → raw/players/active_players.parquet
           raw/players/season_averages_2024.parquet
           raw/standings/standings_2024.parquet
  Local  → /data/parquet/players/active_players.parquet
           /data/parquet/players/season_averages_2024.parquet
           /data/parquet/standings/standings_2024.parquet
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


# ── Local writer ──────────────────────────────────────────────────────────────

def save_local(df: pd.DataFrame, object_path: str) -> None:
    local_path = f"/data/parquet/{object_path}"
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    df.to_parquet(local_path, index=False)
    logger.info(f"Saved local parquet: {local_path}")


# ── Active Players ────────────────────────────────────────────────────────────

def fetch_active_players(headers: Dict[str, str]) -> List[Dict]:
    players: List[Dict] = []
    cursor: Optional[int] = None

    while True:
        params: Dict[str, Any] = {"per_page": PER_PAGE}
        if cursor is not None:
            params["cursor"] = cursor

        try:
            data = _get_json(f"{BASE_URL}/v1/players/active", headers=headers, params=params)
        except Exception as exc:
            logger.error(f"Failed to fetch players cursor={cursor}: {exc}")
            break

        batch = data.get("data", [])
        players.extend(batch)
        logger.info(f"Fetched {len(batch)} players (cursor={cursor}), total={len(players)}")

        next_cursor = data.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break
        cursor = next_cursor
        time.sleep(0.5)

    return players


def build_players_df(raw: List[Dict]) -> pd.DataFrame:
    rows = []
    for p in raw:
        t = p.get("team", {}) or {}
        rows.append({
            "player_id": p.get("id"),
            "first_name": p.get("first_name", ""),
            "last_name": p.get("last_name", ""),
            "full_name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "position": p.get("position", ""),
            "height": p.get("height", ""),
            "weight": p.get("weight", ""),
            "jersey_number": p.get("jersey_number", ""),
            "college": p.get("college", ""),
            "country": p.get("country", ""),
            "draft_year": p.get("draft_year"),
            "draft_round": p.get("draft_round"),
            "draft_number": p.get("draft_number"),
            "team_id": t.get("id"),
            "team_name": t.get("full_name", ""),
            "team_abbreviation": t.get("abbreviation", ""),
            "team_conference": t.get("conference", ""),
            "team_division": t.get("division", ""),
        })
    return pd.DataFrame(rows)


# ── Players (Free Tier Alternative) ───────────────────────────────────────────

def fetch_players_free(headers: Dict[str, str], limit: int = 500) -> List[Dict]:
    """Fetch players from the free /v1/players endpoint with a limit."""
    players: List[Dict] = []
    cursor: Optional[int] = None
    
    while len(players) < limit:
        params = {"per_page": 100}
        if cursor:
            params["cursor"] = cursor
        
        try:
            data = _get_json(f"{BASE_URL}/v1/players", headers=headers, params=params)
            batch = data.get("data", [])
            if not batch:
                break
            players.extend(batch)
            cursor = data.get("meta", {}).get("next_cursor")
            if not cursor:
                break
        except Exception as exc:
            logger.error(f"Error fetching players at cursor {cursor}: {exc}")
            break
            
    return players[:limit]


# ── Season Averages ───────────────────────────────────────────────────────────

def fetch_season_averages(player_ids: List[int], headers: Dict[str, str]) -> List[Dict]:
    averages: List[Dict] = []
    for pid in player_ids:
        try:
            data = _get_json(
                f"{BASE_URL}/v1/season_averages/general",
                headers=headers,
                params={
                    "season": NBA_SEASON,
                    "season_type": "regular",
                    "type": "base",
                    "player_ids[]": pid
                },
            )
            records = data.get("data", [])
            averages.extend(records)
        except Exception as exc:
            logger.warning(f"Could not fetch averages for player_id={pid}: {exc}")
        time.sleep(0.3)
    return averages


def build_averages_df(raw: List[Dict]) -> pd.DataFrame:
    rows = []
    for a in raw:
        # BallDontLie v1 wraps statistics in a "stats" object
        s = a.get("stats", {})
        p = a.get("player", {})
        rows.append({
            "player_id": p.get("id"),
            "season": a.get("season", NBA_SEASON),
            "games_played": int(s.get("gp") or 0),
            "pts": float(s.get("pts") or 0.0),
            "ast": float(s.get("ast") or 0.0),
            "reb": float(s.get("reb") or 0.0),
            "stl": float(s.get("stl") or 0.0),
            "blk": float(s.get("blk") or 0.0),
            "turnover": float(s.get("tov") or 0.0),
            "min": s.get("min", ""),
            "fgm": float(s.get("fgm") or 0.0),
            "fga": float(s.get("fga") or 0.0),
            "fg_pct": float(s.get("fg_pct") or 0.0),
            "fg3m": float(s.get("fg3m") or 0.0),
            "fg3a": float(s.get("fg3a") or 0.0),
            "fg3_pct": float(s.get("fg3_pct") or 0.0),
            "ftm": float(s.get("ftm") or 0.0),
            "fta": float(s.get("fta") or 0.0),
            "ft_pct": float(s.get("ft_pct") or 0.0),
            "oreb": float(s.get("oreb") or 0.0),
            "dreb": float(s.get("dreb") or 0.0),
        })
    return pd.DataFrame(rows)


# ── Standings ─────────────────────────────────────────────────────────────────

def fetch_standings(headers: Dict[str, str]) -> List[Dict]:
    try:
        data = _get_json(
            f"{BASE_URL}/v1/standings",
            headers=headers,
            params={"season": NBA_SEASON},
        )
        return data.get("data", [])
    except Exception as exc:
        logger.error(f"Failed to fetch standings: {exc}")
        return []


def build_standings_df(raw: List[Dict]) -> pd.DataFrame:
    if not raw:
        return pd.DataFrame()
    rows = []
    for s in raw:
        t = s.get("team", {}) or {}
        rows.append({
            "team_id": t.get("id"),
            "team_name": t.get("full_name", ""),
            "team_abbreviation": t.get("abbreviation", ""),
            "conference": t.get("conference", ""),
            "division": t.get("division", ""),
            "conference_record": s.get("conference_record", ""),
            "conference_rank": int(s.get("conference_rank") or 0),
            "division_record": s.get("division_record", ""),
            "division_rank": int(s.get("division_rank") or 0),
            "wins": int(s.get("wins") or 0),
            "losses": int(s.get("losses") or 0),
            "home_record": s.get("home_record", ""),
            "road_record": s.get("road_record", ""),
            "season": int(s.get("season") or NBA_SEASON),
        })
    return pd.DataFrame(rows)


# ── Teams ─────────────────────────────────────────────────────────────────────

def fetch_teams(headers: Dict[str, str]) -> List[Dict]:
    try:
        data = _get_json(f"{BASE_URL}/v1/teams", headers=headers)
        return data.get("data", [])
    except Exception as exc:
        logger.error(f"Failed to fetch teams: {exc}")
        return []


def build_teams_df(raw: List[Dict]) -> pd.DataFrame:
    rows = []
    conf_map = {"East": "Eastern", "West": "Western"}
    for t in raw:
        conf = t.get("conference", "").strip()
        if not conf or conf not in conf_map:
            continue
            
        rows.append({
            "team_id": t.get("id"),
            "team_name": t.get("full_name", ""),
            "team_abbreviation": t.get("abbreviation", ""),
            "conference": conf_map.get(conf, conf),
            "division": t.get("division", ""),
            "city": t.get("city", ""),
            "name": t.get("name", ""),
        })
    return pd.DataFrame(rows)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    headers = {"Authorization": os.environ["BALLDONTLIE_API_KEY"]}
    minio = get_client()

    # --- Teams (Free Tier) ---
    raw_teams = fetch_teams(headers)
    if raw_teams:
        teams_df = build_teams_df(raw_teams)
        upload_parquet(minio, teams_df, "raw", "teams/teams.parquet")
        save_local(teams_df, "teams/teams.parquet")
        logger.info(f"Teams saved: {len(teams_df)} rows")

    # --- Active players (All-Star Tier) / Players (Free Tier Fallback) ---
    raw_players = fetch_active_players(headers)
    if not raw_players:
        logger.info("Accessing free /v1/players fallback...")
        raw_players = fetch_players_free(headers, limit=500)

    if raw_players:
        players_df = build_players_df(raw_players)
        upload_parquet(minio, players_df, "raw", "players/active_players.parquet")
        save_local(players_df, "players/active_players.parquet")
        logger.info(f"Players saved: {len(players_df)} rows")

    # --- Season averages (GOAT Tier) ---
    try:
        if 'players_df' in locals() and not players_df.empty:
            player_ids = players_df["player_id"].dropna().astype(int).tolist()
            raw_avgs = fetch_season_averages(player_ids, headers)
            if raw_avgs:
                avgs_df = build_averages_df(raw_avgs)
                upload_parquet(minio, avgs_df, "raw", "players/season_averages_2024.parquet")
                save_local(avgs_df, "players/season_averages_2024.parquet")
                logger.info(f"Season averages saved: {len(avgs_df)} rows")
    except Exception as exc:
        logger.warning(f"Skipping season averages (likely tier restriction): {exc}")

    # --- Standings (GOAT Tier) ---
    try:
        raw_standings = fetch_standings(headers)
        if raw_standings:
            standings_df = build_standings_df(raw_standings)
            upload_parquet(minio, standings_df, "raw", "standings/standings_2024.parquet")
            save_local(standings_df, "standings/standings_2024.parquet")
            logger.info(f"Standings saved: {len(standings_df)} rows")
    except Exception as exc:
        logger.warning(f"Skipping standings (likely tier restriction): {exc}")


if __name__ == "__main__":
    load_dotenv()
    main()
