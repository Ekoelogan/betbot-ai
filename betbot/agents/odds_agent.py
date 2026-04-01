"""OddsAgent — monitors odds across all sportsbooks, finds best lines."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard

SPORTS = ["nba", "nfl", "mlb", "nhl", "soccer"]


class OddsAgent(BaseAgent):
    name = "📊 Odds"
    emoji = "📊"
    description = "Odds monitor — finds best lines and line movements across 8 books"
    role = "intelligence"
    publishes = ["odds_data", "best_lines", "line_moves"]
    subscribes = ["predictions"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.odds import OddsEngine
        self.engine = OddsEngine()

    def think(self, context: dict) -> dict:
        sports = context.get("sports", SPORTS)
        return {"sports": sports}

    def act(self, plan: dict) -> dict:
        all_odds = {}
        best_lines = []
        total_games = 0

        for sport in plan["sports"]:
            odds = self.engine.get_odds(sport)
            all_odds[sport] = odds
            total_games += len(odds)

            best = self.engine.best_odds(sport)
            for b in best:
                b["sport"] = sport
            best_lines.extend(best)

        self.send("odds_data", all_odds, priority=3)
        self.send("best_lines", best_lines, priority=4)
        self.log(f"Monitored {total_games} games across {len(plan['sports'])} sports → {len(best_lines)} best lines")

        savings = self._calc_savings(best_lines)
        return {"total_games": total_games, "best_lines": len(best_lines),
                "savings_pct": savings, "odds": all_odds}

    def _calc_savings(self, best_lines: list) -> float:
        """Estimate savings from finding best lines vs average."""
        if not best_lines:
            return 0.0
        total_improvement = 0
        count = 0
        for bl in best_lines:
            for side in ["home", "away"]:
                if side in bl and isinstance(bl[side], dict):
                    from betbot.odds import american_to_implied
                    best_implied = american_to_implied(bl[side]["odds"])
                    # Average book might be 2-3% worse
                    improvement = max(0, (1 - best_implied) * 0.02)
                    total_improvement += improvement
                    count += 1
        return round(total_improvement / max(count, 1) * 100, 2)

    def score(self, results: dict) -> float:
        base = results["total_games"] * 0.3
        line_bonus = results["best_lines"] * 1.5
        savings_bonus = results["savings_pct"] * 10
        return base + line_bonus + savings_bonus
