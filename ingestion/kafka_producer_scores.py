"""
ingestion/kafka_producer_scores.py
──────────────────────────────────────────────────────────────────────────────
Simulates 3 concurrent live NBA games and produces JSON score-update events
to the Kafka topic  nba-live-scores  every 30 seconds.

Event schema:
  {
    "game_id"            : str,
    "home_team"          : str,
    "away_team"          : str,
    "quarter"            : int,   # 1-4
    "time_remaining"     : str,   # "MM:SS"
    "home_score"         : int,
    "away_score"         : int,
    "last_scorer"        : str,
    "last_play_description": str,
    "timestamp"          : str    # ISO-8601 UTC
  }

Behaviour:
  - Each game progresses through quarters 1→4.
  - Every tick the score increments 0-4 points randomly.
  - After Q4 ends the game is marked complete and a new game starts.
  - Runs as an infinite loop until interrupted (Ctrl-C / SIGTERM).
──────────────────────────────────────────────────────────────────────────────
"""

import json
import logging
import os
import random
import signal
import time
from datetime import datetime, timezone
from typing import Dict, List

from kafka import KafkaProducer  # kafka-python

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
TICK_INTERVAL = 30  # seconds between score updates

# ── NBA team / player pools ───────────────────────────────────────────────────
TEAMS = [
    "Los Angeles Lakers", "Boston Celtics", "Golden State Warriors",
    "Miami Heat", "Milwaukee Bucks", "Phoenix Suns", "Dallas Mavericks",
    "Denver Nuggets", "Philadelphia 76ers", "Brooklyn Nets",
    "Memphis Grizzlies", "New Orleans Pelicans", "Sacramento Kings",
    "Cleveland Cavaliers", "Toronto Raptors",
]

PLAYERS = [
    "LeBron James", "Stephen Curry", "Jayson Tatum", "Giannis Antetokounmpo",
    "Nikola Jokic", "Luka Doncic", "Kevin Durant", "Joel Embiid",
    "Damian Lillard", "Anthony Davis", "Ja Morant", "Zion Williamson",
    "De'Aaron Fox", "Donovan Mitchell", "Pascal Siakam",
]

PLAY_TEMPLATES = [
    "{player} drills a mid-range jumper.",
    "{player} explodes to the rim for the layup.",
    "{player} nails the three-pointer!",
    "{player} draws the foul and sinks both free throws.",
    "{player} with the and-one!",
    "{player} throws it down with authority!",
    "{player} hits the pull-up jumper.",
    "{player} finds the open look and connects.",
]


# ── Game state factory ────────────────────────────────────────────────────────
def new_game(game_id: str) -> Dict:
    """Create a fresh game state dict."""
    teams = random.sample(TEAMS, 2)
    return {
        "game_id": game_id,
        "home_team": teams[0],
        "away_team": teams[1],
        "quarter": 1,
        "seconds_remaining": 12 * 60,  # 12-minute quarters
        "home_score": 0,
        "away_score": 0,
        "status": "active",
    }


def format_time(seconds: int) -> str:
    """Convert seconds → 'MM:SS' string."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def tick_game(state: Dict) -> Dict:
    """
    Advance one game tick:
      - Decrement clock by TICK_INTERVAL seconds (capped at quarter boundary)
      - Possibly score 0-4 points for home or away team
      - Advance quarter if clock hits 0
    """
    seconds_remaining = state["seconds_remaining"]
    elapsed = min(TICK_INTERVAL, seconds_remaining)
    seconds_remaining -= elapsed
    state["seconds_remaining"] = seconds_remaining

    # Random scoring event (70 % chance)
    if random.random() < 0.7:
        points = random.choices([2, 2, 2, 3, 1, 4], weights=[40, 40, 40, 20, 15, 5])[0]
        scorer = random.choice(PLAYERS)
        play = random.choice(PLAY_TEMPLATES).format(player=scorer)
        if random.random() < 0.5:
            state["home_score"] += points
        else:
            state["away_score"] += points
        state["last_scorer"] = scorer
        state["last_play"] = play
    else:
        state["last_scorer"] = "—"
        state["last_play"] = "Defensive stop. Ball returned to centre."

    # Quarter transition
    if seconds_remaining <= 0:
        if state["quarter"] < 4:
            state["quarter"] += 1
            state["seconds_remaining"] = 12 * 60
            logger.info(
                f"Quarter change → game_id={state['game_id']} quarter={state['quarter']}"
            )
        else:
            state["status"] = "final"

    return state


def build_event(state: Dict) -> Dict:
    """Serialise game state into the Kafka event schema."""
    return {
        "game_id": state["game_id"],
        "home_team": state["home_team"],
        "away_team": state["away_team"],
        "quarter": state["quarter"],
        "time_remaining": format_time(state["seconds_remaining"]),
        "home_score": state["home_score"],
        "away_score": state["away_score"],
        "last_scorer": state.get("last_scorer", "—"),
        "last_play_description": state.get("last_play", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Kafka producer ────────────────────────────────────────────────────────────
def create_producer() -> KafkaProducer:
    """Create a Kafka producer with JSON value serialisation."""
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
        retries=5,
    )
    logger.info(f"Kafka producer connected → brokers={KAFKA_BOOTSTRAP}")
    return producer


# ── Graceful shutdown ─────────────────────────────────────────────────────────
_running = True


def _shutdown(signum, frame):
    global _running
    logger.info("Shutdown signal received — stopping producer")
    _running = False


signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)


# ── Main loop ─────────────────────────────────────────────────────────────────
def run() -> None:
    """Infinite produce loop — simulates 3 concurrent NBA games."""
    # Wait for Kafka to be ready
    time.sleep(15)

    producer = create_producer()
    game_counter = 0

    # Initialise 3 games
    games: List[Dict] = []
    for i in range(3):
        game_counter += 1
        games.append(new_game(f"GAME-{game_counter:04d}"))

    tick = 0
    while _running:
        tick += 1
        for idx, state in enumerate(games):
            if state["status"] == "final":
                logger.info(
                    f"Game ended → game_id={state['game_id']} "
                    f"score={state['home_score']}-{state['away_score']}"
                )
                # Start a new game to replace the finished one
                game_counter += 1
                games[idx] = new_game(f"GAME-{game_counter:04d}")
                state = games[idx]

            state = tick_game(state)
            games[idx] = state

            event = build_event(state)
            producer.send(KAFKA_TOPIC, value=event)

        producer.flush()
        logger.info(
            f"Tick {tick} sent → active_games={len(games)} topic={KAFKA_TOPIC}"
        )
        time.sleep(TICK_INTERVAL)

    producer.close()
    logger.info("Kafka producer stopped cleanly")


if __name__ == "__main__":
    run()
