"""
backend/main.py
────────────────────────────────────────────────────────────────────────────
FastAPI application serving CourtPulse analytics endpoints.

Every endpoint opens a fresh read-only DuckDB connection, queries the mart
tables written by dbt, and returns JSON.  Missing tables (before dbt runs)
are handled gracefully.
────────────────────────────────────────────────────────────────────────────
"""

import logging
import os
import time
from typing import List, Optional

import duckdb
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "/data/courtpulse.duckdb")

app = FastAPI(
    title="CourtPulse API",
    description="Real-time NBA analytics API powered by DuckDB + dbt.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 1)
    logger.info(f"{request.method} {request.url.path} — {duration_ms}ms")
    return response


# ── DB helper ─────────────────────────────────────────────────────────────────

def query_db(sql: str, params=None) -> list:
    """Open a fresh read-only connection, execute SQL, return list of dicts."""
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        if params:
            result = con.execute(sql, params)
        else:
            result = con.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        con.close()


def safe_query(sql: str, params=None, default=None):
    """Wrap query_db and return default on any error."""
    if default is None:
        default = []
    try:
        return query_db(sql, params)
    except Exception as exc:
        logger.warning(f"Query failed: {exc}")
        return default


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/standings")
def get_standings(conference: Optional[str] = Query(default=None)):
    try:
        if conference:
            sql = (
                "SELECT * FROM mart_team_standings "
                "WHERE conference = ? "
                "ORDER BY conference, conference_rank"
            )
            return query_db(sql, [conference])
        else:
            sql = "SELECT * FROM mart_team_standings ORDER BY conference, conference_rank"
            return query_db(sql)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/players")
def get_players(
    team: Optional[str] = Query(default=None),
    tier: Optional[str] = Query(default=None),
    limit: int = Query(default=100),
):
    try:
        conditions = []
        params = []
        if team:
            conditions.append("team_abbreviation = ?")
            params.append(team)
        if tier:
            conditions.append("tier = ?")
            params.append(tier)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        sql = f"SELECT * FROM mart_player_efficiency {where} ORDER BY per DESC LIMIT ?"
        return query_db(sql, params)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/streaks")
def get_streaks():
    try:
        sql = "SELECT * FROM mart_hot_cold_streaks ORDER BY rolling_5game_win_rate DESC"
        return query_db(sql)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/live")
def get_live():
    try:
        # Table may not exist if no games have been ingested yet
        con = duckdb.connect(DUCKDB_PATH, read_only=True)
        try:
            tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        finally:
            con.close()

        if "live_scores" not in tables:
            return []

        sql = "SELECT * FROM live_scores ORDER BY ingested_at DESC"
        return query_db(sql)
    except Exception as exc:
        logger.warning(f"/api/live error: {exc}")
        return []


@app.get("/api/kpis")
def get_kpis():
    best_team_rows = safe_query(
        "SELECT team_name, wins, win_pct FROM mart_team_standings ORDER BY win_pct DESC LIMIT 1"
    )
    top_scorer_rows = safe_query(
        "SELECT player_name, team_abbreviation, pts FROM mart_player_efficiency ORDER BY pts DESC LIMIT 1"
    )
    avg_ppg_rows = safe_query(
        "SELECT ROUND(AVG(avg_pts_scored), 1) AS avg_ppg FROM mart_team_standings"
    )
    total_teams_rows = safe_query(
        "SELECT COUNT(*) AS total FROM mart_team_standings"
    )

    best_team = best_team_rows[0] if best_team_rows else {"team_name": None, "wins": None, "win_pct": None}
    top_scorer = top_scorer_rows[0] if top_scorer_rows else {"player_name": None, "team_abbreviation": None, "pts": None}
    avg_ppg = avg_ppg_rows[0].get("avg_ppg", 0.0) if avg_ppg_rows else 0.0
    total_teams = total_teams_rows[0].get("total", 0) if total_teams_rows else 0

    return {
        "best_team": best_team,
        "top_scorer": top_scorer,
        "avg_ppg": avg_ppg,
        "total_teams": total_teams,
    }
