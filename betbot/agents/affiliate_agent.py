"""AffiliateAgent — optimizes affiliate revenue from sportsbook referrals."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard


class AffiliateAgent(BaseAgent):
    name = "📎 Affiliate"
    emoji = "📎"
    description = "Affiliate optimizer — maximizes referral revenue across 8 sportsbooks"
    role = "revenue"
    publishes = ["affiliate_stats", "best_affiliate"]
    subscribes = ["bets_placed", "value_bets", "content_generated"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.affiliate import AffiliateManager
        self.manager = AffiliateManager()

    def think(self, context: dict) -> dict:
        # Determine which books are getting the most action
        bets_msg = self.bus.latest("bets_placed")
        book_mentions = {}
        if bets_msg:
            for bet in bets_msg.data:
                book = bet.get("book", "DraftKings")
                book_mentions[book] = book_mentions.get(book, 0) + 1

        value_msg = self.bus.latest("top_value")
        if value_msg:
            for v in value_msg.data:
                book = v.get("book", "")
                if book:
                    book_mentions[book] = book_mentions.get(book, 0) + 1

        top_books = sorted(book_mentions.items(), key=lambda x: x[1], reverse=True)[:3]
        return {"top_books": [b[0] for b in top_books] if top_books else ["DraftKings", "FanDuel", "BetMGM"]}

    def act(self, plan: dict) -> dict:
        from betbot.affiliate import DEFAULT_BOOKS

        active_links = self.manager.get_links()
        clicks = self.manager.data.get("clicks", {})
        earnings = self.manager.data.get("earnings", {})

        # Simulate affiliate revenue from content/clicks
        total_clicks = sum(clicks.values())
        total_earnings = sum(earnings.values())

        # Track which books to push based on commission rates
        book_rankings = []
        for book, info in DEFAULT_BOOKS.items():
            commission = info["commission"]
            # Parse max commission
            if "-" in commission:
                max_comm = float(commission.split("-")[1].replace("%", ""))
            else:
                max_comm = float(commission.replace("%", ""))
            book_clicks = clicks.get(book, 0)
            book_earnings = earnings.get(book, 0)
            book_rankings.append({
                "book": book, "max_commission": max_comm,
                "clicks": book_clicks, "earnings": book_earnings,
                "priority": max_comm * 0.6 + (1 if book in plan["top_books"] else 0) * 20,
            })
        book_rankings.sort(key=lambda x: x["priority"], reverse=True)

        best = book_rankings[0] if book_rankings else None
        self.send("affiliate_stats", {
            "total_clicks": total_clicks, "total_earnings": total_earnings,
            "rankings": book_rankings[:5],
        }, priority=3)
        if best:
            self.send("best_affiliate", best, priority=4)

        self.log(f"Clicks: {total_clicks} | Earnings: ${total_earnings:.2f} | Push: {best['book'] if best else 'N/A'}")
        return {"total_clicks": total_clicks, "total_earnings": total_earnings,
                "top_book": best["book"] if best else "None", "rankings": book_rankings[:5]}

    def score(self, results: dict) -> float:
        base = 5.0
        click_bonus = results["total_clicks"] * 0.2
        earnings_bonus = results["total_earnings"] * 2.0
        if results["total_earnings"] > 0:
            self.board.record_win(self.name, results["total_earnings"])
        return base + click_bonus + earnings_bonus
