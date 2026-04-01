"""Predictor — ML-based sports prediction engine."""
from __future__ import annotations

import hashlib
import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
PRIMARY = "#ff2d78"
DATA_DIR = Path.home() / ".betbot"


@dataclass
class Prediction:
    sport: str
    home_team: str
    away_team: str
    home_win_pct: float
    away_win_pct: float
    confidence: float
    recommended_side: str
    kelly_fraction: float = 0.0
    edge: float = 0.0


def _seed_from_teams(home: str, away: str) -> int:
    """Deterministic seed from team names so predictions are consistent."""
    h = hashlib.md5(f"{home}{away}".encode()).hexdigest()
    return int(h[:8], 16)


# ── Demo game schedules ────────────────────────────────────────────────────

DEMO_GAMES: dict[str, list[dict]] = {
    "nba": [
        {"home": "Lakers", "away": "Celtics"},
        {"home": "Warriors", "away": "Bucks"},
        {"home": "Nuggets", "away": "76ers"},
        {"home": "Mavericks", "away": "Knicks"},
        {"home": "Heat", "away": "Suns"},
    ],
    "nfl": [
        {"home": "Chiefs", "away": "Eagles"},
        {"home": "49ers", "away": "Cowboys"},
        {"home": "Ravens", "away": "Bills"},
        {"home": "Lions", "away": "Packers"},
    ],
    "mlb": [
        {"home": "Yankees", "away": "Dodgers"},
        {"home": "Braves", "away": "Astros"},
        {"home": "Rangers", "away": "Phillies"},
    ],
    "nhl": [
        {"home": "Oilers", "away": "Panthers"},
        {"home": "Stars", "away": "Avalanche"},
        {"home": "Rangers", "away": "Hurricanes"},
    ],
    "soccer": [
        {"home": "Man City", "away": "Arsenal"},
        {"home": "Liverpool", "away": "Chelsea"},
        {"home": "Real Madrid", "away": "Barcelona"},
    ],
}


class SportPredictor:
    """ML-inspired sports prediction engine.

    Uses a deterministic simulation that models key features:
    home advantage, team strength, recent form, rest days.
    For production, swap in a real scikit-learn pipeline.
    """

    def __init__(self):
        self.model_version = "1.0.0"
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def predict(self, sport: str, home: str, away: str) -> Prediction:
        """Predict outcome for a single game."""
        seed = _seed_from_teams(home, away)
        rng = random.Random(seed)

        # Simulated feature weights
        home_advantage = rng.uniform(0.52, 0.58)
        home_form = rng.uniform(0.4, 0.7)
        away_form = rng.uniform(0.4, 0.7)
        h2h_factor = rng.uniform(0.45, 0.55)

        raw_home = (home_advantage * 0.3 + home_form * 0.35 +
                    h2h_factor * 0.2 + rng.uniform(0, 0.15) * 0.15)
        raw_away = 1 - raw_home

        # Normalise
        total = raw_home + raw_away
        home_pct = round(raw_home / total, 3)
        away_pct = round(raw_away / total, 3)

        confidence = round(abs(home_pct - 0.5) * 2 * 100, 1)
        confidence = min(confidence, 92.0)

        recommended = home if home_pct > away_pct else away

        return Prediction(
            sport=sport, home_team=home, away_team=away,
            home_win_pct=home_pct, away_win_pct=away_pct,
            confidence=confidence, recommended_side=recommended,
        )

    def predict_all(self, sport: str) -> list[Prediction]:
        """Predict all upcoming games for a sport."""
        games = DEMO_GAMES.get(sport.lower(), [])
        return [self.predict(sport, g["home"], g["away"]) for g in games]

    def find_value_bets(self, sport: str, odds_data: list[dict]) -> list[dict]:
        """Compare model predictions against market odds to find value."""
        from betbot.odds import american_to_implied
        values = []
        for game in odds_data:
            name = game.get("game", "")
            parts = name.split(" vs ")
            if len(parts) != 2:
                continue
            home, away = parts[0].strip(), parts[1].strip()
            pred = self.predict(sport, home, away)

            for book, odds in game.get("books", {}).items():
                home_implied = american_to_implied(odds.get("home", -110))
                away_implied = american_to_implied(odds.get("away", +100))

                home_edge = pred.home_win_pct - home_implied
                away_edge = pred.away_win_pct - away_implied

                if home_edge > 0.03:
                    kelly = round(home_edge / (1 / home_implied - 1), 3) if home_implied < 1 else 0
                    values.append({
                        "game": name, "side": home, "book": book,
                        "model_pct": round(pred.home_win_pct * 100, 1),
                        "market_pct": round(home_implied * 100, 1),
                        "edge": round(home_edge * 100, 1),
                        "odds": odds["home"], "kelly": kelly,
                        "confidence": pred.confidence,
                    })
                if away_edge > 0.03:
                    kelly = round(away_edge / (1 / away_implied - 1), 3) if away_implied < 1 else 0
                    values.append({
                        "game": name, "side": away, "book": book,
                        "model_pct": round(pred.away_win_pct * 100, 1),
                        "market_pct": round(away_implied * 100, 1),
                        "edge": round(away_edge * 100, 1),
                        "odds": odds["away"], "kelly": kelly,
                        "confidence": pred.confidence,
                    })
        return sorted(values, key=lambda x: x["edge"], reverse=True)

    def display_predictions(self, sport: str):
        """Pretty-print predictions for a sport."""
        preds = self.predict_all(sport)
        if not preds:
            console.print(f"[dim]No games found for {sport}[/dim]")
            return
        tbl = Table(title=f"[bold {PRIMARY}]🏈 {sport.upper()} Predictions[/bold {PRIMARY}]",
                    border_style=PRIMARY)
        tbl.add_column("Game", style="bold")
        tbl.add_column("Home %", justify="center")
        tbl.add_column("Away %", justify="center")
        tbl.add_column("Pick", style="bold cyan")
        tbl.add_column("Confidence", justify="center")
        for p in preds:
            conf_color = "green" if p.confidence > 60 else "yellow" if p.confidence > 40 else "red"
            tbl.add_row(
                f"{p.home_team} vs {p.away_team}",
                f"{p.home_win_pct * 100:.1f}%",
                f"{p.away_win_pct * 100:.1f}%",
                p.recommended_side,
                f"[{conf_color}]{p.confidence}%[/{conf_color}]",
            )
        console.print(tbl)
