"""ArbitrageAgent — scans for risk-free arbitrage opportunities across books."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard

SPORTS = ["nba", "nfl", "mlb", "nhl", "soccer"]


class ArbitrageAgent(BaseAgent):
    name = "⚡ Arbitrage"
    emoji = "⚡"
    description = "Arbitrage scanner — finds risk-free profit across sportsbooks"
    role = "analyst"
    publishes = ["arb_opportunities", "arb_alerts"]
    subscribes = ["odds_data", "bankroll_status"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.odds import OddsEngine
        self.engine = OddsEngine()

    def think(self, context: dict) -> dict:
        sports = context.get("sports", SPORTS)
        min_profit = context.get("min_arb_profit", 0.5)
        return {"sports": sports, "min_profit": min_profit}

    def act(self, plan: dict) -> dict:
        all_arbs = []

        for sport in plan["sports"]:
            arbs = self.engine.find_arbitrage(sport)
            for a in arbs:
                a["sport"] = sport
                if a["profit_pct"] >= plan["min_profit"]:
                    all_arbs.append(a)

        all_arbs.sort(key=lambda x: x["profit_pct"], reverse=True)

        if all_arbs:
            self.send("arb_opportunities", all_arbs, priority=10)  # highest priority
            self.send("arb_alerts", all_arbs[:3], priority=10)
            self.log(f"🚨 {len(all_arbs)} ARB FOUND — best: +{all_arbs[0]['profit_pct']}%")
        else:
            self.send("arb_opportunities", [], priority=1)
            self.log("No arbitrage opportunities this cycle")

        total_profit = sum(a["profit_pct"] for a in all_arbs)
        return {"arb_count": len(all_arbs), "arbs": all_arbs,
                "total_profit_pct": round(total_profit, 2)}

    def score(self, results: dict) -> float:
        # Arbs are extremely valuable — heavy scoring
        arb_bonus = results["arb_count"] * 15.0
        profit_bonus = results["total_profit_pct"] * 20.0
        if results["arb_count"] > 0:
            self.board.record_win(self.name, results["total_profit_pct"])
        return arb_bonus + profit_bonus
