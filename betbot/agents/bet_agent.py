"""BetAgent — places bets across ALL sportsbooks simultaneously for maximum coverage."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard


class BetAgent(BaseAgent):
    name = "🎲 Bet"
    emoji = "🎲"
    description = "Multi-platform executor — places bets across ALL 21 sportsbooks simultaneously"
    role = "executor"
    publishes = ["bets_placed", "bet_log"]
    subscribes = ["bet_sizing", "bankroll_status", "risk_alerts", "arb_alerts", "best_lines"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.bankroll import BankrollManager
        self.manager = BankrollManager()

    def think(self, context: dict) -> dict:
        bankroll_msg = self.bus.latest("bankroll_status")
        sizing_msg = self.bus.latest("bet_sizing")
        risk_msg = self.bus.latest("risk_alerts")
        arb_msg = self.bus.latest("arb_alerts")
        lines_msg = self.bus.latest("best_lines")

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

        # Get best lines per game for multi-platform placement
        best_lines = lines_msg.data if lines_msg else []

        multi_platform = context.get("multi_platform", True)
        return {"can_bet": can_bet, "bets": bets_to_place, "arbs": arbs,
                "best_lines": best_lines, "multi_platform": multi_platform}

    def act(self, plan: dict) -> dict:
        placed = []
        platforms_used = set()

        if not plan["can_bet"]:
            self.log("Skipping — risk limits prevent betting")
            self.send("bets_placed", [], priority=3)
            return {"placed": 0, "total_wagered": 0, "bets": [], "platforms": 0}

        from betbot.bankroll import BankrollManager

        # Place value bets — find best book for each bet
        for bet_info in plan["bets"]:
            game = bet_info.get("game", "Unknown")
            side = bet_info.get("side", "Unknown")
            book = bet_info.get("book", "DraftKings")
            odds = bet_info.get("odds", -110)
            units = bet_info.get("suggested_units", 1)
            confidence = bet_info.get("confidence", 50)

            # If multi-platform, find the best line for this game across all books
            if plan["multi_platform"]:
                best_book, best_odds = self._find_best_line(
                    game, side, plan["best_lines"])
                if best_book:
                    book = best_book
                    odds = best_odds

            self.manager = BankrollManager()
            self.manager.place_bet(f"{game}@{book}", side, odds, units, confidence)
            platforms_used.add(book)
            placed.append({
                "game": game, "side": side, "odds": odds,
                "units": units, "confidence": confidence,
                "type": "value", "edge": bet_info.get("edge", 0),
                "book": book,
            })

        # Place arb bets across multiple platforms
        for arb in plan["arbs"]:
            game = arb.get("game", "Unknown")
            for side_name, side_info in arb.get("bets", {}).items():
                book = side_info.get("book", "Unknown")
                self.manager = BankrollManager()
                self.manager.place_bet(f"{game}@{book}", f"{side_name}",
                                        side_info["odds"], 1, 99.0)
                platforms_used.add(book)
                placed.append({
                    "game": game, "side": side_name, "odds": side_info["odds"],
                    "units": 1, "type": "arbitrage", "book": book,
                })

        self.manager = BankrollManager()
        total_wagered = sum(b.get("units", 1) * self.manager.unit_size for b in placed)
        self.send("bets_placed", placed, priority=5)
        self.send("bet_log", {
            "cycle_bets": len(placed), "wagered": total_wagered,
            "platforms": list(platforms_used), "platform_count": len(platforms_used),
        }, priority=2)

        if placed:
            self.log(f"Placed {len(placed)} bets across {len(platforms_used)} platforms — ${total_wagered:.2f}")
        else:
            self.log("No bets placed this cycle")

        return {"placed": len(placed), "total_wagered": total_wagered,
                "bets": placed, "platforms": len(platforms_used),
                "platform_names": list(platforms_used)}

    def _find_best_line(self, game: str, side: str, best_lines: list) -> tuple:
        """Find the best odds for a game/side across all sportsbooks."""
        side_key = "away" if side != game.split(" vs ")[0].split("@")[0] else "home"
        for bl in best_lines:
            if bl.get("game") == game and side_key in bl:
                info = bl[side_key]
                if isinstance(info, dict):
                    return info.get("book", ""), info.get("odds", 0)
        return "", 0

    def score(self, results: dict) -> float:
        base = results["placed"] * 3.0
        wager_bonus = min(results["total_wagered"] * 0.05, 10)
        arb_count = sum(1 for b in results["bets"] if b.get("type") == "arbitrage")
        arb_bonus = arb_count * 10.0
        platform_bonus = results.get("platforms", 0) * 2.0  # reward multi-platform
        return base + wager_bonus + arb_bonus + platform_bonus
