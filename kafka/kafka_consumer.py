"""
kafka/kafka_consumer.py
────────────────────────────────────────────────────────────────────────────
Consumes nba-live-scores topic and upserts into DuckDB live_scores table.
────────────────────────────────────────────────────────────────────────────
"""

import json
import logging
import os
import time
from dotenv import load_dotenv

import duckdb
from kafka import KafkaConsumer
from kafka.errors import KafkaError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

TOPIC = "nba-live-scores"
GROUP_ID = "courtpulse-consumer"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS live_scores (
    game_key        VARCHAR PRIMARY KEY,
    game_date       VARCHAR,
    status          VARCHAR,
    period          INTEGER,
    clock           VARCHAR,
    home_team       VARCHAR,
    home_team_abbr  VARCHAR,
    visitor_team    VARCHAR,
    visitor_team_abbr VARCHAR,
    home_score      INTEGER,
    visitor_score   INTEGER,
    ingested_at     VARCHAR
);
"""

UPSERT_SQL = """
INSERT OR REPLACE INTO live_scores VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
);
"""


def ensure_table(db_path: str) -> None:
    con = duckdb.connect(db_path)
    con.execute(CREATE_TABLE_SQL)
    con.close()


def upsert_game(db_path: str, msg: dict) -> None:
    game_key = f"{msg['home_team_abbr']}_{msg['visitor_team_abbr']}_{msg['game_date']}"
    values = (
        game_key,
        msg.get("game_date", ""),
        msg.get("status", ""),
        int(msg.get("period", 0)),
        msg.get("clock", ""),
        msg.get("home_team", ""),
        msg.get("home_team_abbr", ""),
        msg.get("visitor_team", ""),
        msg.get("visitor_team_abbr", ""),
        int(msg.get("home_score", 0)),
        int(msg.get("visitor_score", 0)),
        msg.get("ingested_at", ""),
    )
    con = duckdb.connect(db_path)
    con.execute(UPSERT_SQL, values)
    con.close()


def main() -> None:
    db_path = os.environ.get("DUCKDB_PATH", "/data/courtpulse.duckdb")
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

    # Wait for DuckDB path to be writable
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    ensure_table(db_path)

    count = 0
    while True:
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=bootstrap,
                group_id=GROUP_ID,
                auto_offset_reset="latest",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                consumer_timeout_ms=1000,
            )
            for message in consumer:
                try:
                    data = message.value
                    if data.get("status") == "no_games":
                        continue
                    upsert_game(db_path, data)
                    count += 1
                    if count % 10 == 0:
                        logger.info(f"Consumed {count} messages so far.")
                except KafkaError as exc:
                    logger.error(f"Kafka error processing message: {exc}")
                except Exception as exc:
                    logger.error(f"Error processing message: {exc}")
            consumer.close()
        except Exception as exc:
            logger.error(f"Consumer connection error: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    load_dotenv()
    main()
