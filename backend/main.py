"""
backend/main.py
──────────────────────────────────────────────────────────────────────────────
CourtPulse FastAPI backend.

Serves transformed NBA analytics data from DuckDB.
All endpoints read from mart tables populated by dbt + Airflow.
CORS is open to the React frontend at http://localhost:3000.

Endpoints:
  GET /health                → liveness probe
  GET /api/standings         → mart_team_standings  (?conference=East|West)
  GET /api/players           → mart_player_efficiency (?team=LAL&tier=Star&limit=50)
  GET /api/streaks           → mart_hot_cold_streaks latest per team
  GET /api/live              → live_scores table (updated by Kafka consumer)
  GET /api/kpis              → aggregated KPI summary object
──────────────────────────────────────────────────────────────────────────────
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd
from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Structured JSON logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

# ── Environment ───────────────────────────────────────────────────────────────
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/data/courtpulse.duckdb")

# ── Global DuckDB connection ──────────────────────────────────────────────────
# We do not use a global connection anymore to prevent read locks from blocking
# writers like Airflow and the Kafka consumer.

def query_to_list(sql: str, params: list = None) -> List[Dict[str, Any]]:
    """Execute SQL and return results as a list of dicts."""
    try:
        # We try up to 5 times in case dbt or kafka-consumer is holding a brief write lock
        for attempt in range(5):
            try:
                with duckdb.connect(DUCKDB_PATH, read_only=True) as db:
                    rel = db.execute(sql, params or [])
                    cols = [desc[0] for desc in rel.description]
                    rows = rel.fetchall()
                    return [dict(zip(cols, row)) for row in rows]
            except duckdb.IOException as e:
                if "lock" in str(e).lower() and attempt < 4:
                    time.sleep(0.5)
                else:
                    raise
    except Exception as exc:
        logger.error(f"Query failed → sql={sql[:120]} error={exc}")
        raise


# ── Pydantic response models ──────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str


class StandingRow(BaseModel):
    team: Optional[str]
    wins: Optional[int]
    losses: Optional[int]
    games_played: Optional[int]
    win_pct: Optional[float]
    avg_pts_scored: Optional[float]
    avg_pts_allowed: Optional[float]
    avg_point_diff: Optional[float]
    home_record: Optional[str]
    away_record: Optional[str]
    overall_seed: Optional[int]
    playoff_position: Optional[str]
    current_streak: Optional[int]

    class Config:
        extra = "allow"


class PlayerRow(BaseModel):
    player_id: Optional[int]
    season: Optional[int]
    team: Optional[str]
    games_played: Optional[int]
    pts: Optional[float]
    reb: Optional[float]
    ast: Optional[float]
    stl: Optional[float]
    blk: Optional[float]
    per: Optional[float]
    fantasy_score: Optional[float]
    tier: Optional[str]
    team_rank: Optional[int]
    overall_rank: Optional[int]

    class Config:
        extra = "allow"


class StreakRow(BaseModel):
    team: Optional[str]
    as_of_date: Optional[str]
    rolling_win_rate: Optional[float]
    window_games: Optional[int]
    streak_label: Optional[str]

    class Config:
        extra = "allow"


class LiveGame(BaseModel):
    game_id: Optional[str]
    home_team: Optional[str]
    away_team: Optional[str]
    quarter: Optional[int]
    time_remaining: Optional[str]
    home_score: Optional[int]
    away_score: Optional[int]
    last_scorer: Optional[str]
    last_play_description: Optional[str]
    updated_at: Optional[str]

    class Config:
        extra = "allow"


class KpiResponse(BaseModel):
    best_team: Optional[str]
    worst_team: Optional[str]
    top_scorer: Optional[str]
    total_games_played: Optional[int]
    avg_points_per_game: Optional[float]
    highest_win_streak_team: Optional[str]


# ── App lifecycle ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise DuckDB on startup; close on shutdown."""
    logger.info("CourtPulse API starting up")
    yield
    logger.info("CourtPulse API shutting down")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="CourtPulse API",
    description="Real-Time NBA Analytics — REST backend serving dbt-transformed DuckDB data.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow React dev server + production frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend:80",
        "http://frontend",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - t0) * 1000, 1)
    logger.info(
        f"method={request.method} path={request.url.path} "
        f"status={response.status_code} duration_ms={duration_ms}"
    )
    return response


# ── Helper: safe table query ──────────────────────────────────────────────────
def _safe_query(sql: str, params: list = None) -> tuple:
    """Returns (data_list, error_string). One will always be None."""
    try:
        return query_to_list(sql, params), None
    except Exception as exc:
        return None, str(exc)


def _table_exists(table: str) -> bool:
    """Check whether a table/view exists in DuckDB."""
    for attempt in range(5):
        try:
            with duckdb.connect(DUCKDB_PATH, read_only=True) as db:
                db.execute(f"SELECT 1 FROM {table} LIMIT 1")
                return True
        except duckdb.IOException as e:
            if "lock" in str(e).lower() and attempt < 4:
                time.sleep(0.5)
            else:
                return False
        except Exception:
            return False
    return False


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/api/standings", tags=["Analytics"])
def get_standings(
    conference: Optional[str] = Query(None, description="Filter: East or West"),
):
    """
    Return team standings from mart_team_standings.
    Optional ?conference=East|West filter (requires conference column in mart).
    """
    table = "main_marts.mart_team_standings"

    if not _table_exists(table):
        # Fallback: return empty list so the UI still renders
        return JSONResponse(content=[], status_code=200)

    sql = f"SELECT * FROM {table}"
    filters = []
    params = []

    if conference:
        filters.append("conference = ?")
        params.append(conference)

    if filters:
        sql += " WHERE " + " AND ".join(filters)

    sql += " ORDER BY win_pct DESC"

    data, err = _safe_query(sql, params)
    if err:
        return JSONResponse(content={"error": err}, status_code=500)
    return JSONResponse(content=data)


@app.get("/api/players", tags=["Analytics"])
def get_players(
    team: Optional[str] = Query(None, description="Filter by team abbreviation"),
    tier: Optional[str] = Query(None, description="Filter by tier: Star|Starter|Role Player|Bench"),
    limit: int = Query(50, ge=1, le=500),
):
    """Return player efficiency data from mart_player_efficiency."""
    table = "main_marts.mart_player_efficiency"

    if not _table_exists(table):
        return JSONResponse(content=[], status_code=200)

    sql = f"SELECT * FROM {table}"
    filters = []
    params = []

    if team:
        filters.append("team ILIKE ?")
        params.append(f"%{team}%")
    if tier:
        filters.append("tier = ?")
        params.append(tier)

    if filters:
        sql += " WHERE " + " AND ".join(filters)

    sql += f" ORDER BY per DESC LIMIT {limit}"

    data, err = _safe_query(sql, params)
    if err:
        return JSONResponse(content={"error": err}, status_code=500)
    return JSONResponse(content=data)


@app.get("/api/streaks", tags=["Analytics"])
def get_streaks():
    """Return the latest hot/cold streak label per team, sorted by rolling_win_rate DESC."""
    table = "main_marts.mart_hot_cold_streaks"

    if not _table_exists(table):
        return JSONResponse(content=[], status_code=200)

    sql = f"""
        SELECT *
        FROM {table}
        ORDER BY rolling_win_rate DESC
    """
    data, err = _safe_query(sql)
    if err:
        return JSONResponse(content={"error": err}, status_code=500)
    return JSONResponse(content=data)


@app.get("/api/live", tags=["Live"])
def get_live():
    """Return all active live game states from the live_scores table."""
    sql = "SELECT game_id, home_team, away_team, quarter, time_remaining, home_score, away_score, last_scorer, last_play_description, CAST(updated_at AS VARCHAR) as updated_at FROM live_scores ORDER BY updated_at DESC"
    data, err = _safe_query(sql)
    if err:
        return JSONResponse(content={"error": err}, status_code=500)
    # Serialise timestamps to strings for JSON
    for row in (data or []):
        if "updated_at" in row and row["updated_at"] is not None:
            row["updated_at"] = str(row["updated_at"])
    return JSONResponse(content=data or [])


@app.get("/api/kpis", response_model=KpiResponse, tags=["Analytics"])
def get_kpis():
    """
    Return a single KPI summary object:
      best_team, worst_team, top_scorer, total_games_played,
      avg_points_per_game, highest_win_streak_team
    """
    kpis: Dict[str, Any] = {
        "best_team": None,
        "worst_team": None,
        "top_scorer": None,
        "total_games_played": 0,
        "avg_points_per_game": 0.0,
        "highest_win_streak_team": None,
    }

    standings_table = "main_marts.mart_team_standings"
    players_table = "main_marts.mart_player_efficiency"

    # Best / worst team
    if _table_exists(standings_table):
        best, _ = _safe_query(
            f"SELECT team FROM {standings_table} ORDER BY win_pct DESC LIMIT 1"
        )
        worst, _ = _safe_query(
            f"SELECT team FROM {standings_table} ORDER BY win_pct ASC LIMIT 1"
        )
        streak_team, _ = _safe_query(
            f"SELECT team FROM {standings_table} ORDER BY current_streak DESC LIMIT 1"
        )
        total, _ = _safe_query(
            f"SELECT SUM(games_played)/2 AS total FROM {standings_table}"
        )
        avg_ppg, _ = _safe_query(
            f"SELECT ROUND(AVG(avg_pts_scored),1) AS avg FROM {standings_table}"
        )

        kpis["best_team"] = best[0]["team"] if best else None
        kpis["worst_team"] = worst[0]["team"] if worst else None
        kpis["highest_win_streak_team"] = streak_team[0]["team"] if streak_team else None
        kpis["total_games_played"] = int(total[0]["total"] or 0) if total else 0
        kpis["avg_points_per_game"] = float(avg_ppg[0]["avg"] or 0.0) if avg_ppg else 0.0

    # Top scorer (by pts average)
    if _table_exists(players_table):
        top, _ = _safe_query(
            f"SELECT player_id, pts FROM {players_table} ORDER BY pts DESC LIMIT 1"
        )
        if top:
            kpis["top_scorer"] = f"Player #{top[0]['player_id']} ({top[0]['pts']} PPG)"

    return JSONResponse(content=kpis)
