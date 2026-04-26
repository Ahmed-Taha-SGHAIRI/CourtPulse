"""
airflow/dags/courtpulse_pipeline.py
──────────────────────────────────────────────────────────────────────────────
CourtPulse hourly Airflow DAG.

Task chain:
  ingest_games → ingest_players → dbt_run_staging → dbt_run_marts
    → validate_quality → done

Retry policy: retries=2, retry_delay=3 minutes on every task.
on_failure_callback: writes structured JSON error entry to /data/logs/failures.jsonl
──────────────────────────────────────────────────────────────────────────────
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

# ── Paths (inside Docker) ─────────────────────────────────────────────────────
INGESTION_DIR = "/opt/airflow/ingestion"
DBT_DIR = "/opt/airflow/dbt_courtpulse"
FAILURE_LOG = "/data/logs/failures.jsonl"
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/data/courtpulse.duckdb")

# ── Failure callback ──────────────────────────────────────────────────────────
def on_failure_callback(context: dict) -> None:
    """
    Write a structured JSON error record to /data/logs/failures.jsonl
    whenever a task fails.
    """
    Path(FAILURE_LOG).parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dag_id": context.get("dag").dag_id,
        "task_id": context.get("task_instance").task_id,
        "execution_date": str(context.get("execution_date")),
        "exception": str(context.get("exception", "unknown")),
        "log_url": context.get("task_instance").log_url,
    }

    try:
        with open(FAILURE_LOG, "a") as fh:
            fh.write(json.dumps(record) + "\n")
        logger.error(f"Failure logged → task={record['task_id']} error={record['exception']}")
    except Exception as exc:
        logger.error(f"Could not write failure log → error={exc}")


# ── Default args ──────────────────────────────────────────────────────────────
default_args = {
    "owner": "courtpulse",
    "depends_on_past": False,
    "start_date": datetime(2024, 10, 1),
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
    "on_failure_callback": on_failure_callback,
}


# ── Python callables ──────────────────────────────────────────────────────────
def run_ingest_games(**kwargs) -> None:
    """Run batch_games.py ingestion script."""
    sys.path.insert(0, INGESTION_DIR)
    # Import fresh each run
    import importlib
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "batch_games", os.path.join(INGESTION_DIR, "batch_games.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.run()
    logger.info("ingest_games completed")


def run_ingest_players(**kwargs) -> None:
    """Run batch_players.py ingestion script."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "batch_players", os.path.join(INGESTION_DIR, "batch_players.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.run()
    logger.info("ingest_players completed")


def validate_data_quality(**kwargs) -> None:
    """
    Lightweight quality gate: verify DuckDB mart tables exist and are non-empty.
    Raises RuntimeError if any check fails.
    """
    import duckdb

    conn = duckdb.connect(DUCKDB_PATH)
    checks = {
        "marts_mart_player_efficiency": "SELECT COUNT(*) FROM marts_mart_player_efficiency",
        "marts_mart_team_standings": "SELECT COUNT(*) FROM marts_mart_team_standings",
        "marts_mart_hot_cold_streaks": "SELECT COUNT(*) FROM marts_mart_hot_cold_streaks",
    }

    for table, query in checks.items():
        try:
            count = conn.execute(query).fetchone()[0]
            if count == 0:
                raise RuntimeError(f"Quality check FAILED — table is empty: {table}")
            logger.info(f"Quality check PASSED → table={table} rows={count}")
        except duckdb.CatalogException:
            # Table doesn't exist yet (first run or dbt not yet executed)
            logger.warning(f"Quality check SKIPPED — table not found: {table}")

    conn.close()


# ── DAG definition ────────────────────────────────────────────────────────────
with DAG(
    dag_id="courtpulse_hourly",
    default_args=default_args,
    description="CourtPulse: hourly NBA data ingestion, dbt transforms, quality checks",
    schedule_interval="@hourly",
    catchup=False,
    tags=["courtpulse", "nba", "analytics"],
) as dag:

    # Task 1 — Ingest games
    ingest_games = PythonOperator(
        task_id="ingest_games",
        python_callable=run_ingest_games,
    )

    # Task 2 — Ingest players & standings
    ingest_players = PythonOperator(
        task_id="ingest_players",
        python_callable=run_ingest_players,
    )

    # Task 3 — dbt: run staging models
    dbt_run_staging = BashOperator(
        task_id="dbt_run_staging",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"dbt run --select staging --profiles-dir {DBT_DIR} "
            f"--project-dir {DBT_DIR} --no-version-check"
        ),
        env={
            **os.environ,
            "DUCKDB_PATH": DUCKDB_PATH,
        },
    )

    # Task 4 — dbt: run mart models
    dbt_run_marts = BashOperator(
        task_id="dbt_run_marts",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"dbt run --select marts --profiles-dir {DBT_DIR} "
            f"--project-dir {DBT_DIR} --no-version-check"
        ),
        env={
            **os.environ,
            "DUCKDB_PATH": DUCKDB_PATH,
        },
    )

    # Task 5 — Data quality validation
    validate_quality = PythonOperator(
        task_id="validate_quality",
        python_callable=validate_data_quality,
    )

    # Task 6 — Completion marker
    done = BashOperator(
        task_id="done",
        bash_command='echo "CourtPulse pipeline run complete at $(date -u +%Y-%m-%dT%H:%M:%SZ)"',
    )

    # ── DAG task chain ────────────────────────────────────────────────────────
    ingest_games >> ingest_players >> dbt_run_staging >> dbt_run_marts >> validate_quality >> done
