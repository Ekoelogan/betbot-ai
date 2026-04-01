"""PredictorAgent — scans all sports, generates AI predictions, publishes picks."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard

SPORTS = ["nba", "nfl", "mlb", "nhl", "soccer"]


class PredictorAgent(BaseAgent):
    name = "🎯 Predictor"
    emoji = "🎯"
    description = "AI prediction engine — scans all sports for high-confidence picks"
    role = "intelligence"
    publishes = ["predictions", "top_picks"]
    subscribes = ["trends_data", "settle_results"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.predictor import SportPredictor
        self.engine = SportPredictor()
        self.accuracy_log: list[bool] = []

    def think(self, context: dict) -> dict:
        sports = context.get("sports", SPORTS)
        min_confidence = context.get("min_confidence", 10.0)
        return {"sports": sports, "min_confidence": min_confidence}

    def act(self, plan: dict) -> dict:
        all_preds = []
        top_picks = []

        for sport in plan["sports"]:
            preds = self.engine.predict_all(sport)
            for p in preds:
                entry = {
                    "sport": sport, "home": p.home_team, "away": p.away_team,
                    "home_pct": p.home_win_pct, "away_pct": p.away_win_pct,
                    "confidence": p.confidence, "pick": p.recommended_side,
                    "game": f"{p.home_team} vs {p.away_team}",
                }
                all_preds.append(entry)
                if p.confidence >= plan["min_confidence"]:
                    top_picks.append(entry)

        top_picks.sort(key=lambda x: x["confidence"], reverse=True)

        self.send("predictions", all_preds)
        self.send("top_picks", top_picks[:10], priority=5)
        self.log(f"Scanned {len(all_preds)} games → {len(top_picks)} actionable picks")

        return {"total_games": len(all_preds), "top_picks": len(top_picks), "picks": top_picks}

    def score(self, results: dict) -> float:
        # Points for coverage + bonus for high-confidence picks
        base = results["total_games"] * 0.5
        bonus = results["top_picks"] * 2.0

        # Check settled results for accuracy tracking
        settled = self.inbox("settle_results")
        for msg in settled:
            for result in msg.data if isinstance(msg.data, list) else [msg.data]:
                if result.get("source") == self.name:
                    if result.get("won"):
                        self.accuracy_log.append(True)
                        self.board.record_win(self.name, result.get("profit", 0))
                    else:
                        self.accuracy_log.append(False)
                        self.board.record_loss(self.name)

        return base + bonus
