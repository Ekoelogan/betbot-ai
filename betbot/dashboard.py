"""Dashboard — rich terminal dashboard for BetBot AI."""
from __future__ import annotations

from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table

console = Console()
PRIMARY = "#ff2d78"
ACCENT = "#ff85b3"

BANNER_LINES = [
    " ██████╗ ███████╗████████╗██████╗  ██████╗ ████████╗",
    " ██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗╚══██╔══╝",
    " ██████╔╝█████╗     ██║   ██████╔╝██║   ██║   ██║   ",
    " ██╔══██╗██╔══╝     ██║   ██╔══██╗██║   ██║   ██║   ",
    " ██████╔╝███████╗   ██║   ██████╔╝╚██████╔╝   ██║   ",
    " ╚═════╝ ╚══════╝   ╚═╝   ╚═════╝  ╚═════╝    ╚═╝   ",
]

GRADIENT = ["#ff2d78", "#ff3d80", "#ff4d88", "#ff5e90", "#ff6e99", "#ff85b3"]


def print_banner():
    console.print()
    for line, color in zip(BANNER_LINES, GRADIENT):
        console.print(f"[bold {color}]{line}[/bold {color}]")
    console.print(f"  [bold {ACCENT}]BetBot AI[/bold {ACCENT}] [dim]v1.0.0 — Sports Betting Analytics & Affiliate Bot[/dim]")
    console.print()


def show_dashboard(sport: str = "nba"):
    """Full terminal dashboard with picks, bankroll, and affiliate stats."""
    print_banner()

    from betbot.predictor import SportPredictor
    from betbot.odds import OddsEngine
    from betbot.bankroll import BankrollManager
    from betbot.affiliate import AffiliateManager

    predictor = SportPredictor()
    odds_engine = OddsEngine()
    bankroll = BankrollManager()
    affiliate = AffiliateManager()

    # ── Predictions ──
    preds = predictor.predict_all(sport)
    picks_tbl = Table(title=f"[bold {PRIMARY}]🎯 Today's {sport.upper()} Picks[/bold {PRIMARY}]",
                      border_style=PRIMARY)
    picks_tbl.add_column("Game", style="bold")
    picks_tbl.add_column("Pick", style="cyan bold")
    picks_tbl.add_column("Win %", justify="center")
    picks_tbl.add_column("Conf", justify="center")
    picks_tbl.add_column("Units", justify="center")

    for p in preds:
        conf_color = "green" if p.confidence > 60 else "yellow" if p.confidence > 40 else "red"
        from betbot.bankroll import units_from_confidence
        units = units_from_confidence(p.confidence)
        picks_tbl.add_row(
            f"{p.home_team} vs {p.away_team}",
            p.recommended_side,
            f"{max(p.home_win_pct, p.away_win_pct) * 100:.1f}%",
            f"[{conf_color}]{p.confidence}%[/{conf_color}]",
            f"{'⭐' * units} ({units}u)",
        )
    console.print(picks_tbl)
    console.print()

    # ── Value Bets ──
    odds_data = odds_engine.get_odds(sport)
    values = predictor.find_value_bets(sport, odds_data)
    if values:
        val_tbl = Table(title=f"[bold {PRIMARY}]💎 Value Bets[/bold {PRIMARY}]", border_style=PRIMARY)
        val_tbl.add_column("Game")
        val_tbl.add_column("Side", style="cyan")
        val_tbl.add_column("Book")
        val_tbl.add_column("Odds", justify="center")
        val_tbl.add_column("Model", justify="center")
        val_tbl.add_column("Market", justify="center")
        val_tbl.add_column("Edge", justify="center", style="green bold")
        for v in values[:5]:
            val_tbl.add_row(
                v["game"], v["side"], v["book"],
                f"{'+' if v['odds'] > 0 else ''}{v['odds']}",
                f"{v['model_pct']}%", f"{v['market_pct']}%",
                f"+{v['edge']}%",
            )
        console.print(val_tbl)
        console.print()

    # ── Bankroll ──
    bankroll.display()
    console.print()

    # ── Affiliates ──
    affiliate.display_links()
