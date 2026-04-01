"""SettleAgent — tracks results, settles pending bets, feeds accuracy back to other agents."""
from __future__ import annotations
import random
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard


class SettleAgent(BaseAgent):
    name = "✅ Settle"
    emoji = "✅"
    description = "Settlement engine — resolves bets, tracks P&L, feeds results to swarm"
    role = "accountant"
    publishes = ["settle_results", "pnl_update"]
    subscribes = ["bets_placed"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.bankroll import BankrollManager
        self.manager = BankrollManager()

    def think(self, context: dict) -> dict:
        # Reload fresh — BetAgent may have placed bets this cycle
        from betbot.bankroll import BankrollManager
        self.manager = BankrollManager()
        bets = self.manager.data.get("bets", [])
        pending = [i for i, b in enumerate(bets) if b.get("result") == "pending"]
        auto_settle = context.get("auto_settle", True)
        return {"pending_indices": pending, "auto_settle": auto_settle,
                "total_bets": len(bets)}

    def act(self, plan: dict) -> dict:
        settled = []
        total_profit = 0.0

        if plan["auto_settle"] and plan["pending_indices"]:
            from betbot.odds import american_to_decimal

            for idx in plan["pending_indices"]:
                bets = self.manager.data.get("bets", [])
                if idx >= len(bets):
                    continue
                bet = bets[idx]
                conf = bet.get("confidence", 50)

                # Simulate result using confidence as rough win probability
                win_prob = min(conf / 100 * 0.9 + 0.1, 0.85)
                rng = random.Random(hash(f"{bet.get('game', '')}{bet.get('side', '')}{idx}"))
                won = rng.random() < win_prob

                result = "win" if won else "loss"
                self.manager.settle_bet(idx, result)

                profit = 0.0
                if won:
                    payout = bet["amount"] * american_to_decimal(bet["odds"])
                    profit = payout - bet["amount"]

                settled.append({
                    "index": idx, "game": bet.get("game", ""),
                    "side": bet.get("side", ""), "result": result,
                    "won": won, "profit": round(profit, 2),
                    "odds": bet.get("odds", -110),
                })
                total_profit += profit if won else -bet.get("amount", 0)

            # Reload manager after settling
            self.manager = self.manager.__class__()

        self.send("settle_results", settled, priority=6)
        self.send("pnl_update", {
            "settled_count": len(settled),
            "total_profit": round(total_profit, 2),
            "balance": self.manager.balance,
            "roi": self.manager.roi,
        }, priority=5)

        wins = sum(1 for s in settled if s["won"])
        losses = len(settled) - wins
        if settled:
            self.log(f"Settled {len(settled)} bets → {wins}W-{losses}L | P&L: ${total_profit:+.2f}")
        else:
            self.log("No pending bets to settle")

        return {"settled": len(settled), "wins": wins, "losses": losses,
                "profit": round(total_profit, 2), "details": settled}

    def score(self, results: dict) -> float:
        base = results["settled"] * 2.0
        profit_bonus = max(0, results["profit"] * 1.0)
        win_bonus = results["wins"] * 3.0
        # Accurate settling is valuable
        if results["wins"] > 0:
            self.board.record_win(self.name, results["profit"])
        elif results["losses"] > 0:
            self.board.record_loss(self.name)
        return base + profit_bonus + win_bonus
