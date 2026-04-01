"""Affiliate marketing engine — manage sportsbook referral links and content."""
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

DEFAULT_BOOKS = {
    "DraftKings": {"base_url": "https://www.draftkings.com", "commission": "25-40%", "cookie_days": 30},
    "FanDuel": {"base_url": "https://www.fanduel.com", "commission": "25-35%", "cookie_days": 30},
    "BetMGM": {"base_url": "https://www.betmgm.com", "commission": "20-30%", "cookie_days": 30},
    "Caesars": {"base_url": "https://www.caesars.com/sportsbook", "commission": "25%", "cookie_days": 14},
    "PointsBet": {"base_url": "https://www.pointsbet.com", "commission": "30%", "cookie_days": 30},
    "BetRivers": {"base_url": "https://www.betrivers.com", "commission": "25-30%", "cookie_days": 30},
    "Bet365": {"base_url": "https://www.bet365.com", "commission": "20-30%", "cookie_days": 30},
    "Bovada": {"base_url": "https://www.bovada.lv", "commission": "25-45%", "cookie_days": 60},
}

CONTENT_TEMPLATES = {
    "twitter": "🔥 {sport} PICK: {pick} ({confidence}% confidence)\n\n{edge} edge vs the market\n\n🎯 Best odds at {book}\n👉 Sign up: {link}\n\n#SportsBetting #{sport} #GamblingTwitter",
    "instagram": "🏆 TODAY'S {sport} PICK 🏆\n\n✅ {pick}\n📊 Model confidence: {confidence}%\n💰 Value edge: {edge}\n🎰 Best odds: {book}\n\n🔗 Link in bio for {book} signup bonus!\n\n#SportsBetting #{sport} #BettingPicks #FreePicks #GamblingPicks",
    "blog": "## {sport} Pick of the Day\n\n**{pick}** — {confidence}% model confidence\n\nOur AI model has identified a **{edge} edge** against the market on this pick. Best available odds are at **{book}**.\n\n[Sign up at {book} and get your welcome bonus →]({link})\n\n*Disclaimer: Betting involves risk. Please gamble responsibly.*",
    "email": "Subject: 🔥 {sport} Value Pick — {confidence}% Confidence\n\nHey,\n\nOur AI model just flagged a high-value {sport} pick:\n\n→ {pick} ({confidence}% confidence, {edge} edge)\n→ Best odds at {book}\n\nSign up here to claim your bonus: {link}\n\nGood luck!\n— BetBot AI",
}


class AffiliateManager:
    """Manage sportsbook affiliate links, tracking, and content generation."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if AFFILIATE_FILE.exists():
            return json.loads(AFFILIATE_FILE.read_text())
        return {"links": {}, "clicks": {}, "earnings": {}}

    def _save(self):
        AFFILIATE_FILE.write_text(json.dumps(self.data, indent=2))

    def add_link(self, book: str, url: str, code: str = ""):
        """Register an affiliate link for a sportsbook."""
        self.data["links"][book] = {"url": url, "code": code, "added": time.time()}
        self._save()
        console.print(f"[bold {PRIMARY}]✓[/] Added affiliate link for [cyan]{book}[/cyan]")

    def get_links(self) -> dict:
        return self.data["links"]

    def get_link_url(self, book: str) -> str:
        link = self.data["links"].get(book, {})
        url = link.get("url", DEFAULT_BOOKS.get(book, {}).get("base_url", ""))
        code = link.get("code", "")
        if code and "?" in url:
            return f"{url}&ref={code}"
        elif code:
            return f"{url}?ref={code}"
        return url

    def track_click(self, book: str):
        clicks = self.data.setdefault("clicks", {})
        clicks[book] = clicks.get(book, 0) + 1
        self._save()

    def log_earning(self, book: str, amount: float):
        earnings = self.data.setdefault("earnings", {})
        earnings[book] = earnings.get(book, 0) + amount
        self._save()

    def generate_content(self, platform: str, sport: str, pick: str,
                         confidence: float, edge: str, book: str) -> str:
        """Generate social media / blog content with affiliate link."""
        template = CONTENT_TEMPLATES.get(platform, CONTENT_TEMPLATES["twitter"])
        link = self.get_link_url(book)
        self.track_click(book)
        return template.format(
            sport=sport.upper(), pick=pick, confidence=confidence,
            edge=edge, book=book, link=link,
        )

    def display_links(self):
        """Show all affiliate links and stats."""
        tbl = Table(title=f"[bold {PRIMARY}]📎 Affiliate Links[/bold {PRIMARY}]", border_style=PRIMARY)
        tbl.add_column("Sportsbook", style="bold")
        tbl.add_column("Commission")
        tbl.add_column("Clicks", justify="center")
        tbl.add_column("Earnings", justify="right", style="green")
        tbl.add_column("Link")

        for book, info in DEFAULT_BOOKS.items():
            clicks = self.data.get("clicks", {}).get(book, 0)
            earnings = self.data.get("earnings", {}).get(book, 0)
            has_link = book in self.data.get("links", {})
            link_status = "[green]✓ Active[/green]" if has_link else "[dim]Not set[/dim]"
            tbl.add_row(
                book, info["commission"], str(clicks),
                f"${earnings:.2f}", link_status,
            )
        console.print(tbl)

    def display_content_preview(self, sport: str, pick: str, confidence: float,
                                 edge: str, book: str):
        """Show generated content for all platforms."""
        for platform in CONTENT_TEMPLATES:
            content = self.generate_content(platform, sport, pick, confidence, edge, book)
            console.print(Panel(
                content,
                title=f"[bold {PRIMARY}]{platform.upper()}[/bold {PRIMARY}]",
                border_style=PRIMARY,
            ))
