"""ValueAgent — combines predictions + odds to find exploitable edges."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard

SPORTS = ["nba", "nfl", "mlb", "nhl", "soccer"]


class ValueAgent(BaseAgent):
    name = "💎 Value"
    emoji = "💎"
    description = "Value hunter — finds edges where model disagrees with the market"
    role = "analyst"
    publishes = ["value_bets", "top_value"]
    subscribes = ["predictions", "odds_data", "best_lines"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.predictor import SportPredictor
        from betbot.odds import OddsEngine
        self.predictor = SportPredictor()
        self.odds_engine = OddsEngine()

    def think(self, context: dict) -> dict:
        sports = context.get("sports", SPORTS)
        min_edge = context.get("min_edge", 3.0)
        # Pull predictions from bus if available
        pred_msg = self.bus.latest("predictions")
        odds_msg = self.bus.latest("odds_data")
        return {
            "sports": sports, "min_edge": min_edge,
            "has_preds": pred_msg is not None,
            "has_odds": odds_msg is not None,
        }

    def act(self, plan: dict) -> dict:
        all_value = []

        # Use bus data if available, else generate fresh
        odds_msg = self.bus.latest("odds_data")

        for sport in plan["sports"]:
            if odds_msg and sport in odds_msg.data:
                odds_data = odds_msg.data[sport]
            else:
                odds_data = self.odds_engine.get_odds(sport)

            values = self.predictor.find_value_bets(sport, odds_data)
            for v in values:
                v["sport"] = sport
            all_value.extend(values)

        all_value.sort(key=lambda x: x["edge"], reverse=True)
        top = all_value[:10]

        self.send("value_bets", all_value, priority=5)
        self.send("top_value", top, priority=8)
        self.log(f"Found {len(all_value)} value bets → top edge: {top[0]['edge']}%" if top else "No value bets found")

        total_edge = sum(v["edge"] for v in all_value)
        return {"total_value_bets": len(all_value), "top_value": top,
                "total_edge": round(total_edge, 1), "avg_edge": round(total_edge / max(len(all_value), 1), 1)}

    def score(self, results: dict) -> float:
        base = results["total_value_bets"] * 1.0
        edge_bonus = results["total_edge"] * 0.5
        quality = results["avg_edge"] * 3.0
        return base + edge_bonus + quality
