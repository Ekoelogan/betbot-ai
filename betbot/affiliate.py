"""Affiliate marketing engine — sportsbooks + CJ, ClickBank, Amazon, Temu & more."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
PRIMARY = "#ff2d78"
DATA_DIR = Path.home() / ".betbot"
AFFILIATE_FILE = DATA_DIR / "affiliates.json"

# ── Sportsbook Affiliates ────────────────────────────────────────────────────

SPORTSBOOK_AFFILIATES = {
    "DraftKings": {"base_url": "https://www.draftkings.com", "commission": "25-40%", "cookie_days": 30, "category": "sportsbook", "cpa": "$50-$200"},
    "FanDuel": {"base_url": "https://www.fanduel.com", "commission": "25-35%", "cookie_days": 30, "category": "sportsbook", "cpa": "$50-$150"},
    "BetMGM": {"base_url": "https://www.betmgm.com", "commission": "20-30%", "cookie_days": 30, "category": "sportsbook", "cpa": "$75-$200"},
    "Caesars": {"base_url": "https://www.caesars.com/sportsbook", "commission": "25%", "cookie_days": 14, "category": "sportsbook", "cpa": "$100-$250"},
    "Bet365": {"base_url": "https://www.bet365.com", "commission": "20-30%", "cookie_days": 30, "category": "sportsbook", "cpa": "$50-$100"},
    "Bovada": {"base_url": "https://www.bovada.lv", "commission": "25-45%", "cookie_days": 60, "category": "sportsbook", "cpa": "$75-$150"},
    "PointsBet": {"base_url": "https://www.pointsbet.com", "commission": "30%", "cookie_days": 30, "category": "sportsbook", "cpa": "$50-$100"},
    "BetRivers": {"base_url": "https://www.betrivers.com", "commission": "25-30%", "cookie_days": 30, "category": "sportsbook", "cpa": "$50-$125"},
    "ESPN BET": {"base_url": "https://www.espnbet.com", "commission": "25-35%", "cookie_days": 30, "category": "sportsbook", "cpa": "$75-$175"},
    "Hard Rock Bet": {"base_url": "https://www.hardrock.bet", "commission": "25-30%", "cookie_days": 30, "category": "sportsbook", "cpa": "$50-$125"},
    "Fanatics": {"base_url": "https://sportsbook.fanatics.com", "commission": "20-30%", "cookie_days": 30, "category": "sportsbook", "cpa": "$75-$150"},
    "WynnBET": {"base_url": "https://www.wynnbet.com", "commission": "25-35%", "cookie_days": 30, "category": "sportsbook", "cpa": "$75-$150"},
    "BetParx": {"base_url": "https://www.betparx.com", "commission": "25%", "cookie_days": 30, "category": "sportsbook", "cpa": "$50-$100"},
    "Betfred": {"base_url": "https://www.betfred.com", "commission": "25-30%", "cookie_days": 30, "category": "sportsbook", "cpa": "$50-$100"},
    "SuperBook": {"base_url": "https://www.superbook.com", "commission": "25%", "cookie_days": 30, "category": "sportsbook", "cpa": "$50-$100"},
    "BetUS": {"base_url": "https://www.betus.com", "commission": "30-50%", "cookie_days": 90, "category": "sportsbook", "cpa": "$100-$300"},
    "MyBookie": {"base_url": "https://www.mybookie.ag", "commission": "25-45%", "cookie_days": 60, "category": "sportsbook", "cpa": "$75-$200"},
    "Betway": {"base_url": "https://www.betway.com", "commission": "25-35%", "cookie_days": 30, "category": "sportsbook", "cpa": "$50-$125"},
    "888sport": {"base_url": "https://www.888sport.com", "commission": "25-40%", "cookie_days": 45, "category": "sportsbook", "cpa": "$50-$150"},
    "Unibet": {"base_url": "https://www.unibet.com", "commission": "20-35%", "cookie_days": 30, "category": "sportsbook", "cpa": "$50-$100"},
    "BetOnline": {"base_url": "https://www.betonline.ag", "commission": "25-50%", "cookie_days": 60, "category": "sportsbook", "cpa": "$100-$250"},
}

# ── Gambling-Specific Affiliates ─────────────────────────────────────────────

GAMBLING_AFFILIATES = {
    "Stake.com": {"base_url": "https://stake.com", "commission": "25-40%", "cookie_days": 30, "category": "crypto_casino", "cpa": "$100-$400"},
    "Roobet": {"base_url": "https://roobet.com", "commission": "20-30%", "cookie_days": 30, "category": "crypto_casino", "cpa": "$50-$200"},
    "BC.Game": {"base_url": "https://bc.game", "commission": "25-35%", "cookie_days": 30, "category": "crypto_casino", "cpa": "$75-$300"},
    "Rollbit": {"base_url": "https://rollbit.com", "commission": "20-30%", "cookie_days": 30, "category": "crypto_casino", "cpa": "$50-$150"},
    "Duelbits": {"base_url": "https://duelbits.com", "commission": "25-40%", "cookie_days": 30, "category": "crypto_casino", "cpa": "$75-$200"},
    "PrizePicks": {"base_url": "https://www.prizepicks.com", "commission": "30-40%", "cookie_days": 30, "category": "dfs", "cpa": "$25-$75"},
    "Underdog Fantasy": {"base_url": "https://underdogfantasy.com", "commission": "30-40%", "cookie_days": 30, "category": "dfs", "cpa": "$25-$75"},
    "Sleeper": {"base_url": "https://sleeper.com", "commission": "25-35%", "cookie_days": 30, "category": "dfs", "cpa": "$20-$50"},
    "Fliff": {"base_url": "https://www.getfliff.com", "commission": "30%", "cookie_days": 30, "category": "social_casino", "cpa": "$15-$50"},
    "Jackpocket": {"base_url": "https://www.jackpocket.com", "commission": "25%", "cookie_days": 30, "category": "lottery", "cpa": "$15-$40"},
}

# ── Retail / E-Commerce Affiliate Networks ───────────────────────────────────

NETWORK_AFFILIATES = {
    # CJ (Commission Junction)
    "CJ Affiliate": {"base_url": "https://www.cj.com", "commission": "3-50%", "cookie_days": 45, "category": "network",
                      "brands": ["GoDaddy", "Priceline", "Overstock", "J.Crew", "Grammarly", "IHG Hotels", "Office Depot"],
                      "avg_epc": "$0.04-$2.50", "network": "cj"},
    # ClickBank
    "ClickBank": {"base_url": "https://www.clickbank.com", "commission": "50-75%", "cookie_days": 60, "category": "digital",
                   "brands": ["Digital products", "E-books", "Courses", "Software", "Health supplements"],
                   "avg_epc": "$0.50-$5.00", "gravity_range": "10-500", "network": "clickbank"},
    # Amazon Associates
    "Amazon Associates": {"base_url": "https://affiliate-program.amazon.com", "commission": "1-10%", "cookie_days": 1, "category": "ecommerce",
                          "brands": ["All Amazon products", "Prime Video", "Audible", "Kindle"],
                          "avg_epc": "$0.02-$0.50", "network": "amazon"},
    # Temu
    "Temu Affiliate": {"base_url": "https://www.temu.com/affiliate", "commission": "5-20%", "cookie_days": 30, "category": "ecommerce",
                        "brands": ["Electronics", "Fashion", "Home & Garden", "Sports", "Toys"],
                        "avg_epc": "$0.10-$1.00", "network": "temu"},
    # ShareASale
    "ShareASale": {"base_url": "https://www.shareasale.com", "commission": "5-50%", "cookie_days": 30, "category": "network",
                    "brands": ["Reebok", "Wayfair", "WP Engine", "Grammarly", "Namecheap"],
                    "avg_epc": "$0.05-$3.00", "network": "shareasale"},
    # Impact
    "Impact": {"base_url": "https://impact.com", "commission": "5-30%", "cookie_days": 30, "category": "network",
                "brands": ["Uber", "Airbnb", "Shopify", "Levi's", "Adidas", "Canva"],
                "avg_epc": "$0.10-$5.00", "network": "impact"},
    # Awin
    "Awin": {"base_url": "https://www.awin.com", "commission": "5-30%", "cookie_days": 30, "category": "network",
              "brands": ["Etsy", "AliExpress", "HP", "Under Armour", "Samsung"],
              "avg_epc": "$0.05-$2.00", "network": "awin"},
    # Rakuten
    "Rakuten Advertising": {"base_url": "https://rakutenadvertising.com", "commission": "5-25%", "cookie_days": 30, "category": "network",
                             "brands": ["Walmart", "Macy's", "New Balance", "Sephora", "Dyson"],
                             "avg_epc": "$0.05-$2.50", "network": "rakuten"},
    # FlexOffers
    "FlexOffers": {"base_url": "https://www.flexoffers.com", "commission": "5-50%", "cookie_days": 30, "category": "network",
                    "brands": ["NordVPN", "Samsung", "Target", "Nike", "Hulu"],
                    "avg_epc": "$0.05-$3.00", "network": "flexoffers"},
    # PartnerStack
    "PartnerStack": {"base_url": "https://partnerstack.com", "commission": "15-30%", "cookie_days": 90, "category": "saas",
                      "brands": ["Monday.com", "Notion", "Webflow", "Gorgias", "Leadpages"],
                      "avg_epc": "$0.50-$10.00", "recurring": True, "network": "partnerstack"},
    # MaxBounty
    "MaxBounty": {"base_url": "https://www.maxbounty.com", "commission": "CPA", "cookie_days": 30, "category": "cpa_network",
                   "brands": ["Finance", "Insurance", "Gaming", "Diet", "Crypto"],
                   "avg_epc": "$1.00-$20.00", "network": "maxbounty"},
    # AvantLink
    "AvantLink": {"base_url": "https://www.avantlink.com", "commission": "5-15%", "cookie_days": 30, "category": "outdoor",
                   "brands": ["REI", "Backcountry", "Moosejaw", "TripAdvisor"],
                   "avg_epc": "$0.10-$2.00", "network": "avantlink"},
    # Refersion
    "Refersion": {"base_url": "https://www.refersion.com", "commission": "10-30%", "cookie_days": 30, "category": "dtc",
                   "brands": ["DTC brands", "Shopify stores", "E-commerce"],
                   "avg_epc": "$0.20-$3.00", "network": "refersion"},
    # SHEIN
    "SHEIN Affiliate": {"base_url": "https://www.shein.com/affiliate", "commission": "10-20%", "cookie_days": 30, "category": "ecommerce",
                         "brands": ["Fashion", "Accessories", "Beauty"],
                         "avg_epc": "$0.05-$0.50", "network": "shein"},
    # AliExpress
    "AliExpress Affiliate": {"base_url": "https://portals.aliexpress.com", "commission": "3-9%", "cookie_days": 3, "category": "ecommerce",
                              "brands": ["Electronics", "Fashion", "Home", "Toys"],
                              "avg_epc": "$0.02-$0.30", "network": "aliexpress"},
}

# Unified view of ALL affiliates
ALL_AFFILIATES = {**SPORTSBOOK_AFFILIATES, **GAMBLING_AFFILIATES, **NETWORK_AFFILIATES}
DEFAULT_BOOKS = SPORTSBOOK_AFFILIATES  # backward compat

# ── Content Templates ────────────────────────────────────────────────────────

CONTENT_TEMPLATES = {
    "twitter": "🔥 {sport} PICK: {pick} ({confidence}% confidence)\n\n{edge} edge vs the market\n\n🎯 Best odds at {book}\n👉 Sign up: {link}\n\n#SportsBetting #{sport} #GamblingTwitter",
    "instagram": "🏆 TODAY'S {sport} PICK 🏆\n\n✅ {pick}\n📊 Model confidence: {confidence}%\n💰 Value edge: {edge}\n🎰 Best odds: {book}\n\n🔗 Link in bio for {book} signup bonus!\n\n#SportsBetting #{sport} #BettingPicks #FreePicks #GamblingPicks",
    "blog": "## {sport} Pick of the Day\n\n**{pick}** — {confidence}% model confidence\n\nOur AI model has identified a **{edge} edge** against the market on this pick. Best available odds are at **{book}**.\n\n[Sign up at {book} and get your welcome bonus →]({link})\n\n*Disclaimer: Betting involves risk. Please gamble responsibly.*",
    "email": "Subject: 🔥 {sport} Value Pick — {confidence}% Confidence\n\nHey,\n\nOur AI model just flagged a high-value {sport} pick:\n\n→ {pick} ({confidence}% confidence, {edge} edge)\n→ Best odds at {book}\n\nSign up here to claim your bonus: {link}\n\nGood luck!\n— BetBot AI",
    "tiktok": "🎬 {sport} LOCK OF THE DAY 🔒\n\n{pick} — {confidence}% AI confidence\n{edge} value edge 💰\n\nBest odds → {book}\n🔗 Link in bio!\n\n#SportsBetting #{sport} #BettingTikTok #FreePicks #Locks",
    "youtube": "📹 {sport} AI PICK — {confidence}% Confidence\n\n✅ {pick}\n📊 {edge} edge vs market\n🎰 Best odds: {book}\n\n👇 Sign up link in description:\n{link}\n\n🔔 Subscribe for daily AI picks!",
    "threads": "🏀 {sport} pick:\n\n{pick} ({confidence}% AI conf)\n{edge} edge → {book}\n\nSign up: {link}\n\n#SportsBetting",
}

RETAIL_CONTENT_TEMPLATES = {
    "twitter": "🔥 DEAL ALERT: {product_name}\n\n💰 {discount}\n⭐ {rating}\n🛒 {network}\n\n👉 {link}\n\n#Deals #{category} #Savings",
    "instagram": "💎 MUST-HAVE DEAL 💎\n\n🛍️ {product_name}\n💰 {discount}\n⭐ Rating: {rating}\n🏪 Via {network}\n\n🔗 Link in bio!\n\n#Deals #{category} #OnlineShopping #SaveMoney",
    "blog": "## Deal of the Day: {product_name}\n\n**{discount}** — ⭐ {rating}\n\nGrab this deal through **{network}** before it expires.\n\n[Shop Now →]({link})\n\n*As an affiliate, we may earn a commission on qualifying purchases.*",
    "email": "Subject: 💰 Deal Alert — {product_name} ({discount})\n\nHey,\n\nJust found this amazing deal:\n\n→ {product_name}\n→ {discount}\n→ Available through {network}\n\nShop here: {link}\n\nHappy shopping!\n— BetBot AI",
    "tiktok": "🛍️ DEAL YOU NEED 🔥\n\n{product_name}\n💰 {discount}\n⭐ {rating}\n🏪 {network}\n\n🔗 Link in bio!\n\n#Deals #{category} #Shopping #TikTokMadeMeBuyIt",
    "youtube": "📹 DEAL REVIEW: {product_name}\n\n💰 {discount}\n⭐ {rating}\n🏪 Via {network}\n\n👇 Affiliate link in description:\n{link}\n\n🔔 Subscribe for daily deals!",
}


class AffiliateManager:
    """Manage ALL affiliate links — sportsbooks, networks, retail, crypto."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if AFFILIATE_FILE.exists():
            return json.loads(AFFILIATE_FILE.read_text())
        return {"links": {}, "clicks": {}, "earnings": {}, "network_stats": {}}

    def _save(self):
        AFFILIATE_FILE.write_text(json.dumps(self.data, indent=2))

    def add_link(self, name: str, url: str, code: str = ""):
        self.data["links"][name] = {"url": url, "code": code, "added": time.time()}
        self._save()
        console.print(f"[bold {PRIMARY}]✓[/] Added affiliate link for [cyan]{name}[/cyan]")

    def get_links(self) -> dict:
        return self.data["links"]

    def get_link_url(self, name: str) -> str:
        link = self.data["links"].get(name, {})
        url = link.get("url", ALL_AFFILIATES.get(name, {}).get("base_url", ""))
        code = link.get("code", "")
        if code and "?" in url:
            return f"{url}&ref={code}"
        elif code:
            return f"{url}?ref={code}"
        return url

    def track_click(self, name: str):
        clicks = self.data.setdefault("clicks", {})
        clicks[name] = clicks.get(name, 0) + 1
        self._save()

    def log_earning(self, name: str, amount: float):
        earnings = self.data.setdefault("earnings", {})
        earnings[name] = earnings.get(name, 0) + amount
        self._save()

    def generate_content(self, platform: str, sport: str, pick: str,
                         confidence: float, edge: str, book: str) -> str:
        template = CONTENT_TEMPLATES.get(platform, CONTENT_TEMPLATES["twitter"])
        link = self.get_link_url(book)
        self.track_click(book)
        return template.format(
            sport=sport.upper(), pick=pick, confidence=confidence,
            edge=edge, book=book, link=link,
        )

    def generate_retail_content(self, platform: str, product_name: str,
                                 discount: str, rating: str, network: str,
                                 category: str = "deals") -> str:
        template = RETAIL_CONTENT_TEMPLATES.get(platform, RETAIL_CONTENT_TEMPLATES["twitter"])
        link = self.get_link_url(network)
        self.track_click(network)
        return template.format(
            product_name=product_name, discount=discount, rating=rating,
            network=network, link=link, category=category,
        )

    def display_links(self):
        """Show all affiliate links grouped by category."""
        # Sportsbooks
        tbl = Table(title=f"[bold {PRIMARY}]🎰 Sportsbook Affiliates ({len(SPORTSBOOK_AFFILIATES)})[/bold {PRIMARY}]",
                    border_style=PRIMARY)
        tbl.add_column("Sportsbook", style="bold")
        tbl.add_column("Commission")
        tbl.add_column("CPA")
        tbl.add_column("Clicks", justify="center")
        tbl.add_column("Earnings", justify="right", style="green")
        tbl.add_column("Status")

        for book, info in SPORTSBOOK_AFFILIATES.items():
            clicks = self.data.get("clicks", {}).get(book, 0)
            earnings = self.data.get("earnings", {}).get(book, 0)
            has_link = book in self.data.get("links", {})
            status = "[green]● Active[/green]" if has_link else "[dim]○ Available[/dim]"
            tbl.add_row(book, info["commission"], info.get("cpa", "—"),
                        str(clicks), f"${earnings:.2f}", status)
        console.print(tbl)
        console.print()

        # Gambling
        tbl2 = Table(title=f"[bold {PRIMARY}]🎲 Gambling Affiliates ({len(GAMBLING_AFFILIATES)})[/bold {PRIMARY}]",
                     border_style=PRIMARY)
        tbl2.add_column("Platform", style="bold")
        tbl2.add_column("Type", style="dim")
        tbl2.add_column("Commission")
        tbl2.add_column("CPA")
        tbl2.add_column("Clicks", justify="center")
        tbl2.add_column("Earnings", justify="right", style="green")
        for name, info in GAMBLING_AFFILIATES.items():
            clicks = self.data.get("clicks", {}).get(name, 0)
            earnings = self.data.get("earnings", {}).get(name, 0)
            tbl2.add_row(name, info["category"], info["commission"],
                         info.get("cpa", "—"), str(clicks), f"${earnings:.2f}")
        console.print(tbl2)
        console.print()

        # Networks
        tbl3 = Table(title=f"[bold {PRIMARY}]🌐 Affiliate Networks ({len(NETWORK_AFFILIATES)})[/bold {PRIMARY}]",
                     border_style=PRIMARY)
        tbl3.add_column("Network", style="bold")
        tbl3.add_column("Category", style="dim")
        tbl3.add_column("Commission")
        tbl3.add_column("Avg EPC")
        tbl3.add_column("Clicks", justify="center")
        tbl3.add_column("Earnings", justify="right", style="green")
        tbl3.add_column("Top Brands")
        for name, info in NETWORK_AFFILIATES.items():
            clicks = self.data.get("clicks", {}).get(name, 0)
            earnings = self.data.get("earnings", {}).get(name, 0)
            brands = ", ".join(info.get("brands", [])[:3])
            tbl3.add_row(name, info["category"], info["commission"],
                         info.get("avg_epc", "—"), str(clicks), f"${earnings:.2f}", brands)
        console.print(tbl3)

        # Totals
        total_clicks = sum(self.data.get("clicks", {}).values())
        total_earnings = sum(self.data.get("earnings", {}).values())
        total_programs = len(ALL_AFFILIATES)
        console.print(Panel(
            f"[bold]Total Programs:[/bold] {total_programs}\n"
            f"[bold]Total Clicks:[/bold] {total_clicks}\n"
            f"[bold]Total Earnings:[/bold] [green]${total_earnings:.2f}[/green]",
            title=f"[bold {PRIMARY}]📊 AFFILIATE EMPIRE TOTALS[/bold {PRIMARY}]",
            border_style=PRIMARY,
        ))

    def display_content_preview(self, sport: str, pick: str, confidence: float,
                                 edge: str, book: str):
        for platform in CONTENT_TEMPLATES:
            content = self.generate_content(platform, sport, pick, confidence, edge, book)
            console.print(Panel(content,
                                title=f"[bold {PRIMARY}]{platform.upper()}[/bold {PRIMARY}]",
                                border_style=PRIMARY))

    def get_all_programs(self) -> dict:
        return ALL_AFFILIATES

    def get_programs_by_category(self, category: str) -> dict:
        return {k: v for k, v in ALL_AFFILIATES.items() if v.get("category") == category}

    def top_earners(self, n: int = 10) -> list[tuple[str, float]]:
        earnings = self.data.get("earnings", {})
        return sorted(earnings.items(), key=lambda x: x[1], reverse=True)[:n]
