"""Odds engine — fetch, convert, compare odds across sportsbooks."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()
PRIMARY = "#ff2d78"

SPORTS_MAP = {
    "nfl": "americanfootball_nfl",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "soccer": "soccer_epl",
    "ncaaf": "americanfootball_ncaaf",
    "ncaab": "basketball_ncaab",
    "mma": "mma_mixed_martial_arts",
}

DEMO_ODDS: list[dict] = [
    {"game": "Lakers vs Celtics", "sport": "nba",
     "books": {"DraftKings": {"home": -150, "away": +130}, "FanDuel": {"home": -145, "away": +125},
               "BetMGM": {"home": -155, "away": +135}, "Caesars": {"home": -148, "away": +128}}},
    {"game": "Chiefs vs Eagles", "sport": "nfl",
     "books": {"DraftKings": {"home": -110, "away": -110}, "FanDuel": {"home": -108, "away": -112},
               "BetMGM": {"home": -115, "away": +105}, "Caesars": {"home": -110, "away": -110}}},
    {"game": "Yankees vs Dodgers", "sport": "mlb",
     "books": {"DraftKings": {"home": +120, "away": -140}, "FanDuel": {"home": +125, "away": -145},
               "BetMGM": {"home": +115, "away": -135}, "Caesars": {"home": +122, "away": -142}}},
    {"game": "Man City vs Arsenal", "sport": "soccer",
     "books": {"DraftKings": {"home": -120, "away": +280, "draw": +240},
               "FanDuel": {"home": -115, "away": +290, "draw": +235},
               "BetMGM": {"home": -125, "away": +275, "draw": +245}}},
    {"game": "Oilers vs Panthers", "sport": "nhl",
     "books": {"DraftKings": {"home": +140, "away": -160}, "FanDuel": {"home": +145, "away": -165},
               "BetMGM": {"home": +135, "away": -155}}},
]


def american_to_decimal(american: int) -> float:
    if american > 0:
        return 1 + american / 100
    return 1 + 100 / abs(american)


def american_to_implied(american: int) -> float:
    if american > 0:
        return 100 / (american + 100)
    return abs(american) / (abs(american) + 100)


def decimal_to_american(decimal_odds: float) -> int:
    if decimal_odds >= 2.0:
        return int(round((decimal_odds - 1) * 100))
    return int(round(-100 / (decimal_odds - 1)))


class OddsEngine:
    """Fetch, convert, and compare odds across sportsbooks."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("ODDS_API_KEY", "")

    def get_odds(self, sport: str = "nba") -> list[dict]:
        """Get odds for a sport. Uses demo data if no API key."""
        if self.api_key:
            return self._fetch_live(sport)
        return [g for g in DEMO_ODDS if g["sport"] == sport.lower()]

    def _fetch_live(self, sport: str) -> list[dict]:
        try:
            import requests
            sport_key = SPORTS_MAP.get(sport.lower(), sport)
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            r = requests.get(url, params={"apiKey": self.api_key, "regions": "us",
                                          "markets": "h2h", "oddsFormat": "american"}, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return [g for g in DEMO_ODDS if g["sport"] == sport.lower()]

    def best_odds(self, sport: str) -> list[dict]:
        """Find best available odds per game across books."""
        games = self.get_odds(sport)
        results = []
        for g in games:
            best = {"game": g["game"]}
            for side in ["home", "away", "draw"]:
                best_book, best_val = "", -9999
                for book, odds in g.get("books", {}).items():
                    if side in odds and odds[side] > best_val:
                        best_val = odds[side]
                        best_book = book
                if best_book:
                    best[side] = {"odds": best_val, "book": best_book,
                                  "implied": round(american_to_implied(best_val) * 100, 1)}
            results.append(best)
        return results

    def find_arbitrage(self, sport: str) -> list[dict]:
        """Find arbitrage opportunities where inverse implied probs < 1."""
        games = self.get_odds(sport)
        arbs = []
        for g in games:
            books = g.get("books", {})
            sides = set()
            for b in books.values():
                sides.update(b.keys())
            # Find best odds per side
            best = {}
            for side in sides:
                for book, odds in books.items():
                    if side in odds:
                        if side not in best or odds[side] > best[side]["odds"]:
                            best[side] = {"odds": odds[side], "book": book}
            if len(best) >= 2:
                total_implied = sum(american_to_implied(v["odds"]) for v in best.values())
                if total_implied < 1.0:
                    profit_pct = round((1 / total_implied - 1) * 100, 2)
                    arbs.append({"game": g["game"], "profit_pct": profit_pct,
                                 "bets": best, "total_implied": round(total_implied, 4)})
        return arbs

    def display_odds(self, sport: str):
        """Pretty-print odds table."""
        games = self.get_odds(sport)
        if not games:
            console.print(f"[dim]No odds found for {sport}[/dim]")
            return
        for g in games:
            tbl = Table(title=f"[bold {PRIMARY}]{g['game']}[/bold {PRIMARY}]", border_style=PRIMARY)
            tbl.add_column("Sportsbook", style="bold")
            tbl.add_column("Home", justify="center")
            tbl.add_column("Away", justify="center")
            if any("draw" in v for v in g.get("books", {}).values()):
                tbl.add_column("Draw", justify="center")
            for book, odds in g.get("books", {}).items():
                row = [book]
                for side in ["home", "away", "draw"]:
                    if side in odds:
                        v = odds[side]
                        color = "green" if v > 0 else "red"
                        row.append(f"[{color}]{'+' if v > 0 else ''}{v}[/{color}]")
                tbl.add_row(*row)
            console.print(tbl)
            console.print()
