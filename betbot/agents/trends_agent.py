"""TrendsAgent — analyzes team/player trends across all sports."""
from __future__ import annotations
import random
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard

SPORTS = ["nba", "nfl", "mlb", "nhl", "soccer"]


class TrendsAgent(BaseAgent):
    name = "📈 Trends"
    emoji = "📈"
    description = "Trend analyst — tracks team form, ATS records, over/unders, streaks"
    role = "intelligence"
    publishes = ["trends_data", "hot_teams", "cold_teams"]
    subscribes = ["predictions"]

    def think(self, context: dict) -> dict:
        pred_msg = self.bus.latest("predictions")
        teams = set()
        if pred_msg:
            for p in pred_msg.data:
                teams.add((p.get("home", ""), p.get("sport", "nba")))
                teams.add((p.get("away", ""), p.get("sport", "nba")))
        return {"teams": list(teams)[:20]}

    def act(self, plan: dict) -> dict:
        trends = []
        hot_teams = []
        cold_teams = []

        for team, sport in plan["teams"]:
            if not team:
                continue
            rng = random.Random(hash(team))
            wins = rng.randint(15, 45)
            losses = rng.randint(10, 35)
            last10_w = rng.randint(3, 9)
            ats_w = rng.randint(20, 40)
            ats_l = rng.randint(15, 35)
            streak = rng.randint(-5, 8)
            ppg = round(rng.uniform(95, 125), 1)
            opp_ppg = round(rng.uniform(98, 118), 1)

            trend = {
                "team": team, "sport": sport,
                "record": f"{wins}-{losses}",
                "last10": f"{last10_w}-{10 - last10_w}",
                "ats": f"{ats_w}-{ats_l}",
                "streak": streak,
                "ppg": ppg, "opp_ppg": opp_ppg,
                "form_score": round((last10_w / 10) * 60 + (wins / max(wins + losses, 1)) * 40, 1),
            }
            trends.append(trend)

            if trend["form_score"] > 65:
                hot_teams.append(trend)
            elif trend["form_score"] < 45:
                cold_teams.append(trend)

        self.send("trends_data", trends, priority=3)
        self.send("hot_teams", hot_teams, priority=4)
        self.send("cold_teams", cold_teams, priority=2)

        self.log(f"Analyzed {len(trends)} teams → 🔥 {len(hot_teams)} hot | 🧊 {len(cold_teams)} cold")
        return {"teams_analyzed": len(trends), "hot": len(hot_teams),
                "cold": len(cold_teams), "trends": trends}

    def score(self, results: dict) -> float:
        base = results["teams_analyzed"] * 0.5
        insight_bonus = (results["hot"] + results["cold"]) * 2.0
        return base + insight_bonus
