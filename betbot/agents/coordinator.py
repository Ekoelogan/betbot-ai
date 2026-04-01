"""Swarm Coordinator — orchestrates 12 agents in cooperative/competitive cycles."""
from __future__ import annotations

import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table

from betbot.agents.base import MessageBus, Leaderboard, PRIMARY, ACCENT

console = Console()

# Execution order — agents run in dependency order so bus data flows correctly
AGENT_ORDER = [
    "predictor",   # 1. Generate predictions for all sports
    "odds",        # 2. Fetch odds across all sportsbooks
    "trends",      # 3. Analyze team trends
    "value",       # 4. Find value bets (needs predictions + odds)
    "arbitrage",   # 5. Scan for arb (needs odds)
    "bankroll",    # 6. Assess risk capacity (needs value + arb)
    "bet",         # 7. Place bets (needs sizing + risk)
    "settle",      # 8. Settle pending bets
    "affiliate",   # 9. Optimize affiliate links (needs bet data)
    "content",     # 10. Generate content (needs picks + affiliate)
    "export",      # 11. Export cycle data
    "dashboard",   # 12. Display everything
]


class SwarmCoordinator:
    """Runs 12 AI agents cooperatively — competing on a shared leaderboard."""

    def __init__(self):
        self.bus = MessageBus()
        self.board = Leaderboard()
        self.agents = {}
        self.cycle_count = 0
        self._init_agents()

    def _init_agents(self):
        from betbot.agents.predictor_agent import PredictorAgent
        from betbot.agents.odds_agent import OddsAgent
        from betbot.agents.value_agent import ValueAgent
        from betbot.agents.arbitrage_agent import ArbitrageAgent
        from betbot.agents.bankroll_agent import BankrollAgent
        from betbot.agents.bet_agent import BetAgent
        from betbot.agents.settle_agent import SettleAgent
        from betbot.agents.affiliate_agent import AffiliateAgent
        from betbot.agents.content_agent import ContentAgent
        from betbot.agents.trends_agent import TrendsAgent
        from betbot.agents.dashboard_agent import DashboardAgent
        from betbot.agents.export_agent import ExportAgent

        self.agents = {
            "predictor": PredictorAgent(self.bus, self.board),
            "odds": OddsAgent(self.bus, self.board),
            "value": ValueAgent(self.bus, self.board),
            "arbitrage": ArbitrageAgent(self.bus, self.board),
            "bankroll": BankrollAgent(self.bus, self.board),
            "bet": BetAgent(self.bus, self.board),
            "settle": SettleAgent(self.bus, self.board),
            "affiliate": AffiliateAgent(self.bus, self.board),
            "content": ContentAgent(self.bus, self.board),
            "trends": TrendsAgent(self.bus, self.board),
            "dashboard": DashboardAgent(self.bus, self.board),
            "export": ExportAgent(self.bus, self.board),
        }

        # Give dashboard reference to all agents
        self.agents["dashboard"].set_agents(list(self.agents.values()))

    @property
    def _quiet(self) -> bool:
        return os.environ.get("BETBOT_DAEMON") == "1"

    def run_cycle(self, context: dict | None = None, show_dashboard: bool = True) -> dict:
        """Run one full swarm cycle — all 12 agents in order."""
        self.cycle_count += 1
        ctx = context or {}
        ctx.setdefault("sports", ["nba", "nfl", "mlb", "nhl", "soccer"])
        ctx.setdefault("auto_settle", True)
        ctx.setdefault("auto_export", True)
        ctx.setdefault("show_dashboard", show_dashboard and not self._quiet)
        ctx.setdefault("max_bets_per_cycle", 3)

        if not self._quiet:
            console.print(f"\n[bold {PRIMARY}]{'━' * 70}[/bold {PRIMARY}]")
            console.print(f"[bold {PRIMARY}]  🐝 SWARM CYCLE #{self.cycle_count}[/bold {PRIMARY}]")
            console.print(f"[bold {PRIMARY}]{'━' * 70}[/bold {PRIMARY}]\n")

        results = {}
        for agent_key in AGENT_ORDER:
            agent = self.agents.get(agent_key)
            if not agent:
                continue
            try:
                result = agent.run_cycle(ctx)
                results[agent_key] = result
            except Exception as e:
                if not self._quiet:
                    console.print(f"  [red]✗ {agent.emoji} {agent.name} FAILED: {e}[/red]")
                results[agent_key] = {"error": str(e)}

        if not self._quiet:
            console.print(f"\n[bold {PRIMARY}]  ✓ Cycle #{self.cycle_count} complete — "
                          f"{len(self.bus.messages)} bus messages[/bold {PRIMARY}]\n")

        # Record to profit tracker
        try:
            from betbot.profit_tracker import ProfitTracker
            tracker = ProfitTracker()
            settle = results.get("settle", {})
            bet = results.get("bet", {})
            tracker.record_cycle(
                profit=settle.get("profit", 0),
                wagered=bet.get("wagered", 0) or bet.get("placed", 0) * 25.0,
                wins=settle.get("wins", 0),
                losses=settle.get("losses", 0),
            )
        except Exception:
            pass

        return results

    def run(self, cycles: int = 1, delay: float = 0, **kwargs):
        """Run multiple swarm cycles."""
        self._print_banner()

        for i in range(cycles):
            self.run_cycle(**kwargs)
            if delay > 0 and i < cycles - 1:
                console.print(f"[dim]Next cycle in {delay}s...[/dim]")
                time.sleep(delay)

        self._print_summary()

    def _print_banner(self):
        banner = """
[bold #ff2d78]
 ███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗
 ██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║
 ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║
 ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║
 ███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
 ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
[/bold #ff2d78]"""
        console.print(banner)
        console.print(f"  [bold {ACCENT}]BetBot AI Swarm[/bold {ACCENT}] [dim]— 12 Autonomous Agents | Cooperative + Competitive[/dim]")
        console.print(f"  [dim]Agents: {' → '.join(a.emoji for a in self.agents.values())}[/dim]")
        console.print()

    def _print_summary(self):
        console.print(f"\n[bold {PRIMARY}]{'═' * 70}[/bold {PRIMARY}]")
        console.print(f"[bold {PRIMARY}]   📊 SWARM SESSION SUMMARY — {self.cycle_count} CYCLES COMPLETE[/bold {PRIMARY}]")
        console.print(f"[bold {PRIMARY}]{'═' * 70}[/bold {PRIMARY}]\n")

        # Bus stats
        stats = self.bus.stats
        console.print(f"  [bold]Total Messages:[/bold] {stats['total']}")
        console.print(f"  [bold]Messages by Agent:[/bold]")
        for sender, count in sorted(stats["by_sender"].items(), key=lambda x: x[1], reverse=True):
            console.print(f"    {sender}: {count}")
        console.print()

        # Final leaderboard
        self.board.display()

        # Winner announcement
        rankings = self.board.rankings()
        if rankings:
            _, winner_name, winner_data = rankings[0]
            console.print(Panel(
                f"[bold green]🏆 {winner_name}[/bold green]\n"
                f"[bold]{winner_data.get('points', 0):.1f} pts[/bold] | "
                f"{winner_data.get('wins', 0)}W-{winner_data.get('losses', 0)}L | "
                f"${winner_data.get('revenue', 0):.2f} revenue",
                title=f"[bold {PRIMARY}]👑 CYCLE MVP[/bold {PRIMARY}]",
                border_style="green",
            ))

    def leaderboard(self):
        """Show current leaderboard."""
        self.board.display()

    def reset(self):
        """Reset all agent scores and bus."""
        self.board.reset()
        self.bus.clear()
        self.cycle_count = 0
        console.print(f"[bold {PRIMARY}]✓ Swarm reset[/bold {PRIMARY}]")
