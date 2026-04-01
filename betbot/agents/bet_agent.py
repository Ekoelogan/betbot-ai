"""BetAgent — places optimal bets based on value, sizing, and risk signals."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard


class BetAgent(BaseAgent):
    name = "🎲 Bet"
    emoji = "🎲"
    description = "Bet executor — places optimally sized bets on the highest-value picks"
    role = "executor"
    publishes = ["bets_placed", "bet_log"]
    subscribes = ["bet_sizing", "bankroll_status", "risk_alerts", "arb_alerts"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.bankroll import BankrollManager
        self.manager = BankrollManager()

    def think(self, context: dict) -> dict:
        bankroll_msg = self.bus.latest("bankroll_status")
        sizing_msg = self.bus.latest("bet_sizing")
        risk_msg = self.bus.latest("risk_alerts")
        arb_msg = self.bus.latest("arb_alerts")

        can_bet = True
        if bankroll_msg and not bankroll_msg.data.get("can_bet", True):
            can_bet = False
        if risk_msg and risk_msg.data.get("type") == "stop_loss":
            can_bet = False

        bets_to_place = []
        if sizing_msg and can_bet:
            bets_to_place = sizing_msg.data[:context.get("max_bets_per_cycle", 3)]

        arbs = []
        if arb_msg and can_bet:
            arbs = arb_msg.data[:2]

        return {"can_bet": can_bet, "bets": bets_to_place, "arbs": arbs}

    def act(self, plan: dict) -> dict:
        placed = []

        if not plan["can_bet"]:
            self.log("Skipping — risk limits prevent betting")
            self.send("bets_placed", [], priority=3)
            return {"placed": 0, "total_wagered": 0, "bets": []}

        # Place value bets
        for bet_info in plan["bets"]:
            game = bet_info.get("game", "Unknown")
            side = bet_info.get("side", "Unknown")
            odds = bet_info.get("odds", -110)
            units = bet_info.get("suggested_units", 1)
            confidence = bet_info.get("confidence", 50)

            self.manager = self.manager.__class__()  # reload fresh
            self.manager.place_bet(game, side, odds, units, confidence)
            placed.append({
                "game": game, "side": side, "odds": odds,
                "units": units, "confidence": confidence,
                "type": "value", "edge": bet_info.get("edge", 0),
            })

        # Place arb bets if any
        for arb in plan["arbs"]:
            game = arb.get("game", "Unknown")
            for side_name, side_info in arb.get("bets", {}).items():
                self.manager = self.manager.__class__()
                self.manager.place_bet(game, f"{side_name}@{side_info['book']}",
                                        side_info["odds"], 1, 99.0)
                placed.append({
                    "game": game, "side": side_name, "odds": side_info["odds"],
                    "units": 1, "type": "arbitrage",
                    "book": side_info["book"],
                })

        total_wagered = sum(b.get("units", 1) * self.manager.unit_size for b in placed)
        self.send("bets_placed", placed, priority=5)
        self.send("bet_log", {"cycle_bets": len(placed), "wagered": total_wagered}, priority=2)

        if placed:
            self.log(f"Placed {len(placed)} bets — ${total_wagered:.2f} wagered")
        else:
            self.log("No bets placed this cycle")

        return {"placed": len(placed), "total_wagered": total_wagered, "bets": placed}

    def score(self, results: dict) -> float:
        base = results["placed"] * 3.0
        wager_bonus = min(results["total_wagered"] * 0.05, 10)
        # Extra for arb bets
        arb_count = sum(1 for b in results["bets"] if b.get("type") == "arbitrage")
        arb_bonus = arb_count * 10.0
        return base + wager_bonus + arb_bonus
