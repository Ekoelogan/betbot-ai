"""Bankroll management — Kelly criterion, unit betting, drawdown protection."""
from __future__ import annotations

import json
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
PRIMARY = "#ff2d78"
DATA_DIR = Path.home() / ".betbot"
BANKROLL_FILE = DATA_DIR / "bankroll.json"


def kelly_criterion(win_prob: float, decimal_odds: float) -> float:
    """Calculate optimal Kelly fraction. Returns fraction of bankroll to wager."""
    b = decimal_odds - 1
    q = 1 - win_prob
    if b <= 0:
        return 0.0
    k = (win_prob * b - q) / b
    return max(0.0, round(k, 4))


def units_from_confidence(confidence: float) -> int:
    """Map confidence % to unit size (1-5)."""
    if confidence >= 80:
        return 5
    elif confidence >= 65:
        return 4
    elif confidence >= 50:
        return 3
    elif confidence >= 35:
        return 2
    return 1


class BankrollManager:
    """Track bankroll, bets, and enforce risk management."""

    def __init__(self, starting_balance: float = 1000.0, unit_size: float = 25.0):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()
        if not self.data.get("balance"):
            self.data["balance"] = starting_balance
            self.data["starting"] = starting_balance
            self.data["unit_size"] = unit_size
            self.data.setdefault("bets", [])
            self.data.setdefault("daily_pnl", 0)
            self.data.setdefault("daily_stop_loss", -0.20)
            self._save()

    def _load(self) -> dict:
        if BANKROLL_FILE.exists():
            return json.loads(BANKROLL_FILE.read_text())
        return {}

    def _save(self):
        BANKROLL_FILE.write_text(json.dumps(self.data, indent=2))

    @property
    def balance(self) -> float:
        return self.data.get("balance", 0)

    @property
    def unit_size(self) -> float:
        return self.data.get("unit_size", 25.0)

    @property
    def total_bets(self) -> int:
        return len(self.data.get("bets", []))

    @property
    def wins(self) -> int:
        return sum(1 for b in self.data.get("bets", []) if b.get("result") == "win")

    @property
    def losses(self) -> int:
        return sum(1 for b in self.data.get("bets", []) if b.get("result") == "loss")

    @property
    def roi(self) -> float:
        starting = self.data.get("starting", 1000)
        if starting == 0:
            return 0
        return round((self.balance - starting) / starting * 100, 2)

    @property
    def win_rate(self) -> float:
        settled = self.wins + self.losses
        return round(self.wins / settled * 100, 1) if settled else 0

    def can_bet(self) -> bool:
        """Check if daily stop-loss allows more betting."""
        daily_pnl_pct = self.data.get("daily_pnl", 0) / max(self.data.get("starting", 1000), 1)
        return daily_pnl_pct > self.data.get("daily_stop_loss", -0.20)

    def place_bet(self, game: str, side: str, odds: int, units: int, confidence: float):
        """Record a bet."""
        if not self.can_bet():
            console.print(f"[bold red]⛔ STOP-LOSS HIT[/bold red] — daily drawdown limit reached")
            return
        amount = units * self.unit_size
        if amount > self.balance:
            console.print(f"[bold red]⛔ Insufficient balance[/bold red] — ${self.balance:.2f} < ${amount:.2f}")
            return
        bet = {
            "game": game, "side": side, "odds": odds, "units": units,
            "amount": amount, "confidence": confidence,
            "time": time.time(), "result": "pending",
        }
        self.data["bets"].append(bet)
        self.data["balance"] -= amount
        self._save()
        console.print(f"[bold {PRIMARY}]✓[/] Placed {units}u (${amount:.2f}) on [cyan]{side}[/cyan] — {game}")

    def settle_bet(self, index: int, result: str):
        """Settle a pending bet as win/loss."""
        bets = self.data.get("bets", [])
        if index >= len(bets):
            return
        bet = bets[index]
        bet["result"] = result
        if result == "win":
            from betbot.odds import american_to_decimal
            payout = bet["amount"] * american_to_decimal(bet["odds"])
            self.data["balance"] += payout
            profit = payout - bet["amount"]
            self.data["daily_pnl"] = self.data.get("daily_pnl", 0) + profit
        else:
            self.data["daily_pnl"] = self.data.get("daily_pnl", 0) - bet["amount"]
        self._save()

    def reset_daily(self):
        self.data["daily_pnl"] = 0
        self._save()

    def display(self):
        """Show bankroll dashboard."""
        roi_color = "green" if self.roi >= 0 else "red"
        console.print(Panel(
            f"[bold]Balance:[/bold] [green]${self.balance:.2f}[/green]\n"
            f"[bold]Unit Size:[/bold] ${self.unit_size:.2f}\n"
            f"[bold]ROI:[/bold] [{roi_color}]{self.roi:+.1f}%[/{roi_color}]\n"
            f"[bold]Record:[/bold] {self.wins}W - {self.losses}L ({self.win_rate}%)\n"
            f"[bold]Total Bets:[/bold] {self.total_bets}\n"
            f"[bold]Stop-Loss:[/bold] {'[green]OK[/green]' if self.can_bet() else '[red]HIT[/red]'}",
            title=f"[bold {PRIMARY}]💰 Bankroll[/bold {PRIMARY}]",
            border_style=PRIMARY,
        ))

        pending = [b for b in self.data.get("bets", []) if b.get("result") == "pending"]
        if pending:
            tbl = Table(title="Pending Bets", border_style=PRIMARY)
            tbl.add_column("#", justify="center")
            tbl.add_column("Game")
            tbl.add_column("Side", style="cyan")
            tbl.add_column("Units", justify="center")
            tbl.add_column("Amount", justify="right")
            for i, b in enumerate(pending):
                tbl.add_row(str(i), b["game"], b["side"],
                           str(b["units"]), f"${b['amount']:.2f}")
            console.print(tbl)
