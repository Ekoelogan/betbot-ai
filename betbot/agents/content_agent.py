"""ContentAgent — generates monetized content across 4 platforms."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard

PLATFORMS = ["twitter", "instagram", "blog", "email"]


class ContentAgent(BaseAgent):
    name = "📝 Content"
    emoji = "📝"
    description = "Content factory — generates affiliate-linked content across all platforms"
    role = "revenue"
    publishes = ["content_generated", "content_queue"]
    subscribes = ["top_picks", "top_value", "best_affiliate"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        from betbot.affiliate import AffiliateManager
        self.manager = AffiliateManager()

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
            target_book = aff_msg.data.get("book", "DraftKings")

        platforms = context.get("platforms", PLATFORMS)
        return {"best_pick": best_pick, "book": target_book, "platforms": platforms}

    def act(self, plan: dict) -> dict:
        if not plan["best_pick"]:
            self.log("No picks available for content generation")
            self.send("content_generated", [], priority=1)
            return {"pieces": 0, "content": []}

        pick = plan["best_pick"]
        sport = pick.get("sport", "nba")
        game = pick.get("game", "Unknown")
        side = pick.get("pick", pick.get("side", "Unknown"))
        conf = pick.get("confidence", 50)
        edge = f"{conf:.1f}%"

        content_pieces = []
        for platform in plan["platforms"]:
            text = self.manager.generate_content(
                platform=platform, sport=sport,
                pick=f"{side} ({game})", confidence=conf,
                edge=edge, book=plan["book"],
            )
            content_pieces.append({
                "platform": platform, "text": text,
                "sport": sport, "book": plan["book"],
                "pick": side, "game": game,
            })

        self.send("content_generated", content_pieces, priority=4)
        self.send("content_queue", {
            "count": len(content_pieces),
            "platforms": plan["platforms"],
            "book": plan["book"],
        }, priority=2)

        self.log(f"Generated {len(content_pieces)} pieces → {', '.join(plan['platforms'])} | Book: {plan['book']}")
        return {"pieces": len(content_pieces), "content": content_pieces,
                "book": plan["book"], "sport": sport}

    def score(self, results: dict) -> float:
        base = results["pieces"] * 3.0
        # Each piece = potential affiliate click → revenue
        revenue_potential = results["pieces"] * 1.5
        if results["pieces"] > 0:
            self.board.record_win(self.name, results["pieces"] * 0.5)
        return base + revenue_potential
