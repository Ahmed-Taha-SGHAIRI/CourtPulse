# 🏀 CourtPulse — Real-Time NBA Analytics Pipeline

CourtPulse is a production-ready, end-to-end data engineering pipeline for NBA analytics. It ingests live and historical data from the [balldontlie API](https://www.balldontlie.io), stores raw data in MinIO (S3-compatible), transforms it with dbt + DuckDB, orchestrates pipeline runs with Airflow, and serves results through a FastAPI backend and a React 18 frontend — all wired together with Docker Compose.

---

## Architecture Diagram

```mermaid
flowchart TD
    A[balldontlie API] -->|batch hourly| B[Python Ingestion]
    A -->|every 30s| C[Kafka Producer]
    B -->|upload| D[MinIO Raw Parquet]
    B -->|write| E[/data/parquet]
    C -->|produce| F[Kafka Topic: nba-live-scores]
    F -->|consume| G[Kafka Consumer]
    G -->|upsert| H[DuckDB live_scores table]
    E -->|read_parquet| I[dbt + DuckDB]
    I -->|materialize| J[Mart Tables]
    J -->|query| K[FastAPI :8000]
    H -->|query| K
    K -->|JSON| L[React Frontend :3000]
    M[Airflow :8080] -->|orchestrates| B
    M -->|orchestrates| I
```

---

## Data Sources

| Source | Endpoints Used | Auth |
|---|---|---|
| balldontlie API | `/nba/v1/games`, `/nba/v1/stats`, `/nba/v1/players/active`, `/nba/v1/season_averages`, `/nba/v1/standings`, `/nba/v1/box_scores/live` | Raw API key in `Authorization` header |

---

## Tech Stack

| Layer | Tool | Version | Why |
|---|---|---|---|
| Ingestion (batch) | Python + httpx | 3.11 / 0.27.0 | Async-ready HTTP client with retry via tenacity |
| Ingestion (streaming) | Apache Kafka | confluentinc 7.5.0 | Industry-standard event streaming |
| Storage (lake) | MinIO | latest | S3-compatible, runs locally in Docker |
| Storage (warehouse) | DuckDB | 0.10.2 | Embedded OLAP — no separate server needed |
| Transformation | dbt-duckdb | 1.8.1 | SQL-based transforms with lineage + testing |
| Orchestration | Apache Airflow | 2.9.1 | DAG-based scheduling with UI |
| Backend | FastAPI + Uvicorn | 0.111.0 / 0.29.0 | High-performance async REST API |
| Frontend | React 18 + Vite + TailwindCSS + Recharts | latest | Fast SPA with rich data visualisation |
| Retry logic | tenacity | 8.2.3 | Declarative retry with exponential back-off |
| Testing | pytest | 8.2.2 | Industry-standard Python test runner |

---

## Quick Start

```bash
git clone <repo>
cd courtpulse
cp .env.example .env
docker-compose up -d

# Wait ~60 seconds for all services to initialise
# Then trigger the first pipeline run:
docker-compose exec airflow-webserver airflow dags trigger courtpulse_hourly
```

> **Note:** The pipeline will call the balldontlie API, write Parquet files to `/data/parquet/`, and run dbt transformations. The frontend will show data once the first DAG run completes (typically 3–10 minutes depending on season size).

---

## Service URLs

| Service | URL | Credentials |
|---|---|---|
| Frontend | http://localhost:3000 | — |
| API | http://localhost:8000 | — |
| API Docs (Swagger) | http://localhost:8000/docs | — |
| Airflow | http://localhost:8080 | admin / admin |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |

---

## Environment Variables

Copy `.env.example` to `.env`. No changes are required for local development:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `BALLDONTLIE_API_KEY` | provided | balldontlie API key |
| `MINIO_ROOT_USER` | `minioadmin` | MinIO access key |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO secret key |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO internal hostname |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker address |
| `DUCKDB_PATH` | `/data/courtpulse.duckdb` | Shared DuckDB file path |
| `NBA_SEASON` | `2024` | Season year to ingest |

---

## Running Tests

```bash
cd tests
pip install -r requirements.txt
pytest -v
```

Expected output: all tests pass with no network or file I/O required.

---

## Project Structure

```
courtpulse/
├── docker-compose.yml          # Full stack orchestration
├── .env.example                # Environment variables template
├── ingestion/                  # Batch + streaming ingestion
│   ├── batch_games.py          # Fetches games & stats from API
│   ├── batch_players.py        # Fetches players, averages & standings
│   └── kafka_producer.py       # Polls live box scores → Kafka
├── kafka/
│   └── kafka_consumer.py       # Consumes Kafka → DuckDB live_scores
├── storage/
│   └── minio_client.py         # MinIO helper functions
├── dbt_courtpulse/             # dbt project
│   └── models/
│       ├── staging/            # Views over raw Parquet files
│       └── marts/              # Materialised analytics tables
├── airflow/
│   └── dags/courtpulse_pipeline.py  # Hourly orchestration DAG
├── backend/
│   └── main.py                 # FastAPI app with 6 endpoints
├── frontend/                   # React 18 + Vite SPA
│   └── src/
│       ├── pages/              # Overview, Players, Streaks, LiveScores
│       └── components/         # KpiCard, StandingsTable, PlayerTable…
└── tests/
    ├── test_transformations.py # Business logic unit tests
    └── test_data_quality.py    # DuckDB in-memory data quality tests
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/api/standings?conference=West` | Team standings (filterable) |
| `GET` | `/api/players?tier=Star&limit=50` | Player efficiency (filterable) |
| `GET` | `/api/streaks` | Rolling 5-game win rates |
| `GET` | `/api/live` | Live game scores (Kafka-fed) |
| `GET` | `/api/kpis` | Dashboard KPI summary |

---

## dbt Models

| Model | Type | Description |
|---|---|---|
| `stg_games` | View | Cleaned completed games with winner derivation |
| `stg_player_stats` | View | Active players joined with season averages + fantasy score |
| `mart_player_efficiency` | Table | PER calculation, tier labels, team/overall rank |
| `mart_team_standings` | Table | Standings enriched with home/away splits and playoff status |
| `mart_hot_cold_streaks` | Table | Rolling 5-game win rate per team with streak label |
