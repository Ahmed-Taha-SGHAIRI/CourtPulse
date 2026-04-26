"""
kafka/kafka_consumer_scores.py
──────────────────────────────────────────────────────────────────────────────
Kafka consumer for the  nba-live-scores  topic.

Responsibilities:
  1. Consume JSON events from Kafka.
  2. Append raw events to MinIO JSONL files with hourly rotation:
       streaming/live_scores/YYYY-MM-DD/HH/events.jsonl
  3. Upsert the latest game state into DuckDB table  live_scores  so the
     FastAPI backend can serve live data with minimal latency.
  4. Log a summary every 50 events.
──────────────────────────────────────────────────────────────────────────────
"""

import io
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Dict

import duckdb
from kafka import KafkaConsumer

# ── Path resolution (so storage module is importable) ────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from storage.minio_client import ensure_buckets, init_client  # noqa: E402

# ── Structured JSON logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

# ── Environment ───────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = "nba-live-scores"
KAFKA_GROUP = "courtpulse-consumer-group"
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "/data/courtpulse.duckdb")
MINIO_BUCKET = "streaming"
LOG_EVERY = 50  # log a summary every N events


# ── DuckDB initialisation ─────────────────────────────────────────────────────
def init_duckdb_table(path: str) -> None:
    """
    Ensure the live_scores table exists.
    """
    for attempt in range(10):
        try:
            with duckdb.connect(path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS live_scores (
                        game_id               VARCHAR PRIMARY KEY,
                        home_team             VARCHAR,
                        away_team             VARCHAR,
                        quarter               INTEGER,
                        time_remaining        VARCHAR,
                        home_score            INTEGER,
                        away_score            INTEGER,
                        last_scorer           VARCHAR,
                        last_play_description VARCHAR,
                        updated_at            TIMESTAMPTZ
                    )
                    """
                )
            logger.info(f"DuckDB table live_scores ensured → path={path}")
            return
        except Exception as e:
            if "lock" in str(e).lower() and attempt < 9:
                time.sleep(2.0)
            else:
                raise


def upsert_live_score(path: str, event: Dict) -> None:
    """
    Upsert the latest game state into the live_scores table.
    DuckDB does not support INSERT OR REPLACE with ON CONFLICT natively in all
    versions, so we DELETE then INSERT.
    """
    for attempt in range(10):
        try:
            with duckdb.connect(path) as conn:
                conn.execute(
                    "DELETE FROM live_scores WHERE game_id = ?",
                    [event["game_id"]],
                )
                conn.execute(
                    """
                    INSERT INTO live_scores VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        event["game_id"],
                        event["home_team"],
                        event["away_team"],
                        event["quarter"],
                        event["time_remaining"],
                        event["home_score"],
                        event["away_score"],
                        event.get("last_scorer", ""),
                        event.get("last_play_description", ""),
                        datetime.now(timezone.utc).isoformat(),
                    ],
                )
            return
        except Exception as e:
            if "lock" in str(e).lower() and attempt < 9:
                time.sleep(1.0)
            else:
                raise


# ── MinIO JSONL writer ────────────────────────────────────────────────────────
class JsonlWriter:
    """
    Buffers JSONL lines and flushes them to MinIO with hourly rotation.
    """

    def __init__(self):
        self.s3 = init_client()
        self._reset()

    def _reset(self):
        self._buffer: list = []
        self._current_hour: str = self._hour_key()

    @staticmethod
    def _hour_key() -> str:
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d/%H")

    def write(self, event: Dict) -> None:
        hour = self._hour_key()
        if hour != self._current_hour:
            self.flush()
            self._reset()
        self._buffer.append(json.dumps(event))

    def flush(self) -> None:
        if not self._buffer:
            return
        key = f"live_scores/{self._current_hour}/events.jsonl"
        body = "\n".join(self._buffer) + "\n"
        try:
            self.s3.put_object(
                Bucket=MINIO_BUCKET,
                Key=key,
                Body=body.encode("utf-8"),
                ContentType="application/x-ndjson",
            )
            logger.info(
                f"Flushed JSONL to MinIO → key={key} events={len(self._buffer)}"
            )
        except Exception as exc:
            logger.error(f"MinIO flush failed → key={key} error={exc}")
        self._buffer.clear()


# ── Graceful shutdown ─────────────────────────────────────────────────────────
_running = True


def _shutdown(signum, frame):
    global _running
    logger.info("Shutdown signal received — stopping consumer")
    _running = False


signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)


# ── Main consume loop ─────────────────────────────────────────────────────────
def run() -> None:
    """Consume nba-live-scores, write to MinIO JSONL, upsert DuckDB."""
    # Give Kafka time to start
    time.sleep(20)

    ensure_buckets(["raw", "streaming", "processed"])

    init_duckdb_table(DUCKDB_PATH)
    writer = JsonlWriter()

    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=KAFKA_GROUP,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        enable_auto_commit=True,
        consumer_timeout_ms=5000,  # poll every 5 s so we can check _running
    )
    logger.info(f"Kafka consumer started → topic={KAFKA_TOPIC} group={KAFKA_GROUP}")

    event_count = 0

    while _running:
        try:
            for message in consumer:
                if not _running:
                    break

                event: Dict = message.value
                game_id = event.get("game_id", "unknown")

                # 1. Write to MinIO JSONL
                writer.write(event)

                # 2. Upsert DuckDB
                try:
                    upsert_live_score(DUCKDB_PATH, event)
                except Exception as exc:
                    logger.error(
                        f"DuckDB upsert failed → game_id={game_id} error={exc}"
                    )

                event_count += 1
                if event_count % LOG_EVERY == 0:
                    logger.info(
                        f"Consumer progress → events_processed={event_count} "
                        f"last_game={game_id}"
                    )

        except Exception as exc:
            logger.warning(f"Consumer poll error → error={exc}")

    # Cleanup
    writer.flush()
    consumer.close()
    logger.info(f"Consumer stopped cleanly → total_events={event_count}")


if __name__ == "__main__":
    run()
