"""ContentAgent — generates monetized content across 7 platforms + retail affiliate content."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard

PLATFORMS = ["twitter", "instagram", "blog", "email", "tiktok", "youtube", "threads"]

# Sample retail products to promote via affiliate networks
RETAIL_PROMOS = [
    {"product_name": "Wireless Earbuds Pro", "discount": "60% OFF", "rating": "4.8/5", "network": "Amazon Associates", "category": "Electronics"},
    {"product_name": "Sports Betting Strategy Guide", "discount": "75% OFF", "rating": "4.9/5", "network": "ClickBank", "category": "Digital"},
    {"product_name": "Smart Fitness Watch", "discount": "50% OFF", "rating": "4.7/5", "network": "Temu Affiliate", "category": "Wearables"},
    {"product_name": "VPN Premium (3yr)", "discount": "82% OFF", "rating": "4.8/5", "network": "CJ Affiliate", "category": "Software"},
    {"product_name": "AI Trading Course", "discount": "70% OFF", "rating": "4.6/5", "network": "ClickBank", "category": "Education"},
    {"product_name": "Betting Analytics Dashboard", "discount": "$49/mo", "rating": "4.9/5", "network": "ShareASale", "category": "SaaS"},
    {"product_name": "Portable Projector", "discount": "45% OFF", "rating": "4.5/5", "network": "Temu Affiliate", "category": "Electronics"},
    {"product_name": "Premium Sports Apparel Bundle", "discount": "40% OFF", "rating": "4.7/5", "network": "Impact", "category": "Fashion"},
]


class ContentAgent(BaseAgent):
    name = "📝 Content"
    emoji = "📝"
    description = "Content factory — generates affiliate content across 7 platforms for sports + retail"
    role = "revenue"
    publishes = ["content_generated", "content_queue"]
    subscribes = ["top_picks", "top_value", "best_affiliate", "network_rankings"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.affiliate import AffiliateManager
        self.manager = AffiliateManager()
        self._promo_idx = 0

    def think(self, context: dict) -> dict:
        picks_msg = self.bus.latest("top_picks")
        value_msg = self.bus.latest("top_value")
        aff_msg = self.bus.latest("best_affiliate")

        best_pick = None
        if picks_msg and picks_msg.data:
            best_pick = picks_msg.data[0]
        elif value_msg and value_msg.data:
            v = value_msg.data[0]
            best_pick = {"sport": v.get("sport", "nba"), "game": v["game"],
                         "pick": v["side"], "confidence": v.get("confidence", 50)}

        target_book = "DraftKings"
        if aff_msg and aff_msg.data:
            target_book = aff_msg.data.get("name", aff_msg.data.get("book", "DraftKings"))

        platforms = context.get("platforms", PLATFORMS)
        generate_retail = context.get("generate_retail_content", True)
        return {"best_pick": best_pick, "book": target_book,
                "platforms": platforms, "generate_retail": generate_retail}

    def act(self, plan: dict) -> dict:
        content_pieces = []

        # ── Sports betting content ───────────────────────────────────────
        if plan["best_pick"]:
            pick = plan["best_pick"]
            sport = pick.get("sport", "nba")
            game = pick.get("game", "Unknown")
            side = pick.get("pick", pick.get("side", "Unknown"))
            conf = pick.get("confidence", 50)
            edge = f"{conf:.1f}%"

            for platform in plan["platforms"]:
                text = self.manager.generate_content(
                    platform=platform, sport=sport,
                    pick=f"{side} ({game})", confidence=conf,
                    edge=edge, book=plan["book"],
                )
                content_pieces.append({
                    "platform": platform, "text": text, "type": "sports",
                    "sport": sport, "book": plan["book"],
                    "pick": side, "game": game,
                })

        # ── Retail / network affiliate content ───────────────────────────
        if plan["generate_retail"]:
            promo = RETAIL_PROMOS[self._promo_idx % len(RETAIL_PROMOS)]
            self._promo_idx += 1

            for platform in ["twitter", "instagram", "blog", "email", "tiktok"]:
                text = self.manager.generate_retail_content(
                    platform=platform,
                    product_name=promo["product_name"],
                    discount=promo["discount"],
                    rating=promo["rating"],
                    network=promo["network"],
                    category=promo["category"],
                )
                content_pieces.append({
                    "platform": platform, "text": text, "type": "retail",
                    "network": promo["network"], "product": promo["product_name"],
                })

        self.send("content_generated", content_pieces, priority=4)
        self.send("content_queue", {
            "count": len(content_pieces),
            "sports_pieces": sum(1 for c in content_pieces if c["type"] == "sports"),
            "retail_pieces": sum(1 for c in content_pieces if c["type"] == "retail"),
            "platforms": list(set(c["platform"] for c in content_pieces)),
        }, priority=2)

        sports_n = sum(1 for c in content_pieces if c["type"] == "sports")
        retail_n = sum(1 for c in content_pieces if c["type"] == "retail")
        self.log(f"Generated {len(content_pieces)} pieces — {sports_n} sports + {retail_n} retail "
                 f"across {len(set(c['platform'] for c in content_pieces))} platforms")

        return {"pieces": len(content_pieces), "sports_pieces": sports_n,
                "retail_pieces": retail_n, "content": content_pieces}

    def score(self, results: dict) -> float:
        base = results["pieces"] * 3.0
        revenue_potential = results["pieces"] * 1.5
        retail_bonus = results.get("retail_pieces", 0) * 2.0  # retail = extra revenue streams
        if results["pieces"] > 0:
            self.board.record_win(self.name, results["pieces"] * 0.5)
        return base + revenue_potential + retail_bonus
