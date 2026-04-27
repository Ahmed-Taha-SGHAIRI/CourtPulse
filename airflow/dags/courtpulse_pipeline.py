"""
airflow/dags/courtpulse_pipeline.py
────────────────────────────────────────────────────────────────────────────
Hourly Airflow DAG that orchestrates the CourtPulse batch pipeline:
  1. Ingest games from balldontlie API → MinIO + /data/parquet
  2. Ingest players, season averages, and standings → MinIO + /data/parquet
  3. Run dbt staging models (views over raw parquet)
  4. Run dbt mart models (materialised tables in DuckDB)
────────────────────────────────────────────────────────────────────────────
"""

import logging
import sys
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# ── Path setup so ingestion modules are importable from the DAG ──────────────
sys.path.insert(0, "/opt/airflow/dbt_courtpulse")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Airflow mounts the dags dir at /opt/airflow/dags; ingestion scripts will be mounted at /opt/airflow/ingestion.
_INGESTION_PATH = "/opt/airflow/ingestion"
if _INGESTION_PATH not in sys.path:
    sys.path.insert(0, _INGESTION_PATH)

# Also add the storage module
_STORAGE_PATH = "/opt/airflow/storage"
if _STORAGE_PATH not in sys.path:
    sys.path.insert(0, _STORAGE_PATH)

default_args = {
    "owner": "courtpulse",
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
}

DBT_DIR = "/opt/airflow/dbt_courtpulse"

with DAG(
    dag_id="courtpulse_hourly",
    schedule_interval="@hourly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    description="CourtPulse: ingest NBA data, transform with dbt, load mart tables.",
    tags=["courtpulse", "nba", "dbt"],
) as dag:

    def run_ingest_games():
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "batch_games", "/opt/airflow/ingestion/batch_games.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.main()

    def run_ingest_players():
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "batch_players", "/opt/airflow/ingestion/batch_players.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.main()

    def pipeline_done():
        logging.info("CourtPulse pipeline complete.")

    ingest_games = PythonOperator(
        task_id="ingest_games",
        python_callable=run_ingest_games,
    )

    ingest_players = PythonOperator(
        task_id="ingest_players",
        python_callable=run_ingest_players,
    )

    dbt_staging = BashOperator(
        task_id="dbt_staging",
        bash_command=(
            f"cd {DBT_DIR} && "
            "dbt run --select staging --profiles-dir . --project-dir ."
        ),
    )

    dbt_marts = BashOperator(
        task_id="dbt_marts",
        bash_command=(
            f"cd {DBT_DIR} && "
            "dbt run --select marts --profiles-dir . --project-dir ."
        ),
    )

    done = PythonOperator(
        task_id="done",
        python_callable=pipeline_done,
    )

    ingest_games >> ingest_players >> dbt_staging >> dbt_marts >> done
