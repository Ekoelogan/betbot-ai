"""BankrollAgent — manages risk, sizing, stop-loss, Kelly optimization."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard


class BankrollAgent(BaseAgent):
    name = "💰 Bankroll"
    emoji = "💰"
    description = "Risk manager — Kelly sizing, stop-loss enforcement, bankroll optimization"
    role = "risk_manager"
    publishes = ["bankroll_status", "bet_sizing", "risk_alerts"]
    subscribes = ["value_bets", "arb_opportunities", "settle_results"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.bankroll import BankrollManager
        self.manager = BankrollManager()

    def think(self, context: dict) -> dict:
        # Reload fresh — bets may have been settled
        from betbot.bankroll import BankrollManager
        self.manager = BankrollManager()
        balance = self.manager.balance
        can_bet = self.manager.can_bet()
        roi = self.manager.roi
        win_rate = self.manager.win_rate
        pending = sum(1 for b in self.manager.data.get("bets", []) if b.get("result") == "pending")

        risk_level = "green"
        if not can_bet:
            risk_level = "red"
        elif roi < -10:
            risk_level = "orange"
        elif pending > 5:
            risk_level = "yellow"

        return {
            "balance": balance, "can_bet": can_bet, "roi": roi,
            "win_rate": win_rate, "risk_level": risk_level,
            "pending_bets": pending, "unit_size": self.manager.unit_size,
        }

    def act(self, plan: dict) -> dict:
        status = {
            "balance": plan["balance"],
            "unit_size": plan["unit_size"],
            "can_bet": plan["can_bet"],
            "risk_level": plan["risk_level"],
            "roi": plan["roi"],
            "win_rate": plan["win_rate"],
            "max_bet_units": self._calc_max_units(plan),
        }
        self.send("bankroll_status", status, priority=7)

        # Generate sizing recommendations for pending value bets
        value_msg = self.bus.latest("top_value")
        sizing = []
        if value_msg and plan["can_bet"]:
            from betbot.bankroll import kelly_criterion, units_from_confidence
            from betbot.odds import american_to_decimal
            for v in value_msg.data[:5]:
                decimal_odds = american_to_decimal(v["odds"])
                model_prob = v["model_pct"] / 100
                kelly = kelly_criterion(model_prob, decimal_odds)
                units = units_from_confidence(v.get("confidence", 50))
                # Half-Kelly for safety
                safe_kelly = kelly * 0.5
                suggested_amount = min(safe_kelly * plan["balance"], plan["unit_size"] * units)
                sizing.append({
                    **v, "kelly": kelly, "half_kelly": safe_kelly,
                    "suggested_units": units, "suggested_amount": round(suggested_amount, 2),
                })

        self.send("bet_sizing", sizing, priority=6)

        if not plan["can_bet"]:
            self.send("risk_alerts", {"type": "stop_loss", "message": "Daily stop-loss hit"}, priority=10)
            self.log("⛔ STOP-LOSS ACTIVE — no new bets allowed")
        elif plan["risk_level"] == "orange":
            self.send("risk_alerts", {"type": "caution", "message": "ROI declining — reduce exposure"}, priority=5)
            self.log("⚠️ Risk level ORANGE — recommending reduced exposure")
        else:
            self.log(f"Balance: ${plan['balance']:.2f} | ROI: {plan['roi']:+.1f}% | Risk: {plan['risk_level']}")

        return {**status, "sizing_count": len(sizing), "sizing": sizing}

    def _calc_max_units(self, plan: dict) -> int:
        if not plan["can_bet"]:
            return 0
        if plan["risk_level"] == "red":
            return 0
        if plan["risk_level"] == "orange":
            return 2
        if plan["risk_level"] == "yellow":
            return 3
        return 5

    def score(self, results: dict) -> float:
        base = 5.0  # Always earns for risk management
        if results["risk_level"] == "green":
            base += 3.0
        sizing_bonus = results["sizing_count"] * 1.5
        roi_bonus = max(0, results["roi"] * 0.5)
        return base + sizing_bonus + roi_bonus
