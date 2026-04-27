"""
ingestion/kafka_producer.py
────────────────────────────────────────────────────────────────────────────
Polls /nba/v1/box_scores/live every 30 s and publishes to Kafka topic
nba-live-scores.
────────────────────────────────────────────────────────────────────────────
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from kafka import KafkaProducer
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.balldontlie.io"
TOPIC = "nba-live-scores"
POLL_INTERVAL = 30


# ── HTTP helper ───────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _fetch_live(headers: Dict[str, str]) -> List[Dict[str, Any]]:
    from datetime import timedelta
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    
    with httpx.Client(timeout=30.0) as client:
        # Fetch both yesterday and today to catch late-night live games across time zones
        resp = client.get(
            f"{BASE_URL}/v1/games", 
            headers=headers, 
            params={"dates[]": [yesterday, today]}
        )
        resp.raise_for_status()
        return resp.json().get("data", [])


# ── Message builders ──────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_game_message(box: Dict[str, Any]) -> Dict[str, Any]:
    home = box.get("home_team", {})
    vis = box.get("visitor_team", {})
    return {
        "game_date": (box.get("date") or "")[:10],
        "status": box.get("status", ""),
        "period": box.get("period", 0),
        "clock": box.get("time", ""),
        "home_team": home.get("full_name", ""),
        "home_team_abbr": home.get("abbreviation", ""),
        "visitor_team": vis.get("full_name", ""),
        "visitor_team_abbr": vis.get("abbreviation", ""),
        "home_score": int(box.get("home_team_score", 0) or 0),
        "visitor_score": int(box.get("visitor_team_score", 0) or 0),
        "ingested_at": _now_iso(),
    }


# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    headers = {"Authorization": os.environ["BALLDONTLIE_API_KEY"]}
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

    producer = KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    logger.info(f"Kafka producer started, topic={TOPIC}")

    while True:
        try:
            games = _fetch_live(headers)
            if not games:
                msg = {"status": "no_games", "ingested_at": _now_iso()}
                producer.send(TOPIC, msg)
                logger.info("Produced heartbeat: no_games")
            else:
                for box in games:
                    msg = build_game_message(box)
                    producer.send(TOPIC, msg)
                    logger.info(
                        f"Produced: {msg['home_team_abbr']} vs {msg['visitor_team_abbr']} "
                        f"period={msg['period']} clock={msg['clock']}"
                    )
            producer.flush()
        except Exception as exc:
            logger.error(f"Producer loop error: {exc}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    load_dotenv()
    main()
