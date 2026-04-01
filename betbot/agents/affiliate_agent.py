"""AffiliateAgent — optimizes revenue across ALL affiliate networks."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard


class AffiliateAgent(BaseAgent):
    name = "📎 Affiliate"
    emoji = "📎"
    description = "Affiliate empire — maximizes revenue across 46+ programs: sportsbooks, CJ, ClickBank, Amazon, Temu & more"
    role = "revenue"
    publishes = ["affiliate_stats", "best_affiliate", "network_rankings"]
    subscribes = ["bets_placed", "value_bets", "content_generated"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.affiliate import AffiliateManager
        self.manager = AffiliateManager()

    def think(self, context: dict) -> dict:
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

        top_books = sorted(book_mentions.items(), key=lambda x: x[1], reverse=True)[:5]
        return {
            "top_books": [b[0] for b in top_books] if top_books else ["DraftKings", "FanDuel", "BetMGM"],
            "optimize_all": context.get("optimize_all_networks", True),
        }

    def act(self, plan: dict) -> dict:
        from betbot.affiliate import (
            SPORTSBOOK_AFFILIATES, GAMBLING_AFFILIATES,
            NETWORK_AFFILIATES, ALL_AFFILIATES,
        )

        clicks = self.manager.data.get("clicks", {})
        earnings = self.manager.data.get("earnings", {})
        total_clicks = sum(clicks.values())
        total_earnings = sum(earnings.values())

        # Rank ALL programs by revenue potential
        all_rankings = []

        # Score sportsbooks
        for name, info in SPORTSBOOK_AFFILIATES.items():
            comm = info["commission"]
            max_comm = float(comm.split("-")[1].replace("%", "")) if "-" in comm else float(comm.replace("%", ""))
            cpa_str = info.get("cpa", "$50")
            max_cpa = float(cpa_str.split("-")[1].replace("$", "").replace(",", "")) if "-" in cpa_str else float(cpa_str.replace("$", "").replace(",", ""))
            priority = max_comm * 0.4 + max_cpa * 0.1 + (20 if name in plan["top_books"] else 0)
            all_rankings.append({
                "name": name, "category": "sportsbook", "max_commission": max_comm,
                "max_cpa": max_cpa, "clicks": clicks.get(name, 0),
                "earnings": earnings.get(name, 0), "priority": round(priority, 1),
            })

        # Score gambling affiliates
        for name, info in GAMBLING_AFFILIATES.items():
            comm = info["commission"]
            max_comm = float(comm.split("-")[1].replace("%", "")) if "-" in comm else float(comm.replace("%", ""))
            cpa_str = info.get("cpa", "$50")
            max_cpa = float(cpa_str.split("-")[1].replace("$", "").replace(",", "")) if "-" in cpa_str else float(cpa_str.replace("$", "").replace(",", ""))
            priority = max_comm * 0.5 + max_cpa * 0.08
            all_rankings.append({
                "name": name, "category": info["category"], "max_commission": max_comm,
                "max_cpa": max_cpa, "clicks": clicks.get(name, 0),
                "earnings": earnings.get(name, 0), "priority": round(priority, 1),
            })

        # Score network affiliates (CJ, ClickBank, Amazon, Temu, etc.)
        for name, info in NETWORK_AFFILIATES.items():
            comm = info["commission"]
            if "CPA" in str(comm):
                max_comm = 50.0
            elif "-" in str(comm):
                max_comm = float(str(comm).split("-")[1].replace("%", ""))
            else:
                max_comm = float(str(comm).replace("%", ""))
            epc_str = info.get("avg_epc", "$0.10")
            max_epc = float(epc_str.split("-")[1].replace("$", "")) if "-" in epc_str else float(epc_str.replace("$", ""))
            priority = max_comm * 0.3 + max_epc * 15
            if info.get("recurring"):
                priority *= 1.5  # recurring commissions are gold
            all_rankings.append({
                "name": name, "category": info.get("network", info["category"]),
                "max_commission": max_comm, "max_epc": max_epc,
                "clicks": clicks.get(name, 0), "earnings": earnings.get(name, 0),
                "priority": round(priority, 1),
                "brands": info.get("brands", [])[:3],
            })

        all_rankings.sort(key=lambda x: x["priority"], reverse=True)

        # Top picks per category
        top_sportsbook = [r for r in all_rankings if r["category"] == "sportsbook"][:5]
        top_gambling = [r for r in all_rankings if r["category"] in ("crypto_casino", "dfs", "social_casino", "lottery")][:5]
        top_network = [r for r in all_rankings if r["category"] not in ("sportsbook", "crypto_casino", "dfs", "social_casino", "lottery")][:5]

        best = all_rankings[0] if all_rankings else None
        self.send("affiliate_stats", {
            "total_programs": len(ALL_AFFILIATES),
            "total_clicks": total_clicks, "total_earnings": total_earnings,
            "top_overall": all_rankings[:10],
            "top_sportsbook": top_sportsbook[:3],
            "top_gambling": top_gambling[:3],
            "top_network": top_network[:3],
        }, priority=3)
        self.send("network_rankings", all_rankings, priority=2)
        if best:
            self.send("best_affiliate", best, priority=4)

        self.log(f"Optimized {len(ALL_AFFILIATES)} programs | Clicks: {total_clicks} | "
                 f"Earnings: ${total_earnings:.2f} | Top: {best['name'] if best else 'N/A'}")

        return {
            "total_programs": len(ALL_AFFILIATES),
            "total_clicks": total_clicks, "total_earnings": total_earnings,
            "top_book": best["name"] if best else "None",
            "rankings_count": len(all_rankings),
            "top_5": [r["name"] for r in all_rankings[:5]],
        }

    def score(self, results: dict) -> float:
        base = 5.0
        program_bonus = results["total_programs"] * 0.1
        click_bonus = results["total_clicks"] * 0.2
        earnings_bonus = results["total_earnings"] * 2.0
        if results["total_earnings"] > 0:
            self.board.record_win(self.name, results["total_earnings"])
        return base + program_bonus + click_bonus + earnings_bonus
