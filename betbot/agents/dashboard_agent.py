"""DashboardAgent — monitors all agents, displays live swarm status."""
from __future__ import annotations
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard, console, PRIMARY, ACCENT


class DashboardAgent(BaseAgent):
    name = "🖥️ Dashboard"
    emoji = "🖥️"
    description = "Swarm monitor — displays live status of all 12 agents and system health"
    role = "monitor"
    publishes = ["system_health"]
    subscribes = ["bets_placed", "settle_results", "pnl_update",
                  "content_generated", "affiliate_stats", "arb_opportunities"]

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        self.agents_registry: list = []

    def set_agents(self, agents: list):
        self.agents_registry = agents

    def think(self, context: dict) -> dict:
        return {"show_full": context.get("show_dashboard", True)}

    def act(self, plan: dict) -> dict:
        from rich.table import Table
        from rich.panel import Panel
        from rich.columns import Columns

        # System health
        pnl_msg = self.bus.latest("pnl_update")
        bets_msg = self.bus.latest("bets_placed")
        content_msg = self.bus.latest("content_generated")
        aff_msg = self.bus.latest("affiliate_stats")
        arb_msg = self.bus.latest("arb_opportunities")

        balance = pnl_msg.data.get("balance", 0) if pnl_msg else 0
        roi = pnl_msg.data.get("roi", 0) if pnl_msg else 0
        bets_placed = len(bets_msg.data) if bets_msg else 0
        content_count = len(content_msg.data) if content_msg and isinstance(content_msg.data, list) else 0
        arb_count = len(arb_msg.data) if arb_msg and isinstance(arb_msg.data, list) else 0
        total_clicks = aff_msg.data.get("total_clicks", 0) if aff_msg else 0
        total_earnings = aff_msg.data.get("total_earnings", 0) if aff_msg else 0

        health = {
            "balance": balance, "roi": roi, "bets_this_cycle": bets_placed,
            "content_pieces": content_count, "arb_found": arb_count,
            "aff_clicks": total_clicks, "aff_earnings": total_earnings,
            "bus_messages": len(self.bus.messages),
        }
        self.send("system_health", health, priority=1)

        if plan["show_full"]:
            self._render(health)

        self.log(f"System OK — {len(self.bus.messages)} bus msgs | {bets_placed} bets | ${balance:.2f} balance")
        return health

    def _render(self, health: dict):
        from rich.table import Table
        from rich.panel import Panel

        # Header
        console.print()
        console.print(f"[bold {PRIMARY}]{'═' * 70}[/bold {PRIMARY}]")
        console.print(f"[bold {PRIMARY}]   🐝 BETBOT SWARM — MULTI-AGENT AI SYSTEM[/bold {PRIMARY}]")
        console.print(f"[bold {PRIMARY}]{'═' * 70}[/bold {PRIMARY}]")

        # System stats
        roi_color = "green" if health["roi"] >= 0 else "red"
        stats = (
            f"[bold]💰 Balance:[/bold] [green]${health['balance']:.2f}[/green]  │  "
            f"[bold]📊 ROI:[/bold] [{roi_color}]{health['roi']:+.1f}%[/{roi_color}]  │  "
            f"[bold]🎲 Bets:[/bold] {health['bets_this_cycle']}  │  "
            f"[bold]⚡ Arbs:[/bold] {health['arb_found']}  │  "
            f"[bold]📝 Content:[/bold] {health['content_pieces']}\n"
            f"[bold]📎 Clicks:[/bold] {health['aff_clicks']}  │  "
            f"[bold]💵 Aff Rev:[/bold] [green]${health['aff_earnings']:.2f}[/green]  │  "
            f"[bold]📡 Bus:[/bold] {health['bus_messages']} msgs"
        )
        console.print(Panel(stats, title=f"[bold {ACCENT}]SYSTEM STATUS[/bold {ACCENT}]",
                           border_style=ACCENT))

        # Agent status table
        if self.agents_registry:
            tbl = Table(title=f"[bold {PRIMARY}]🤖 AGENT STATUS[/bold {PRIMARY}]",
                       border_style=PRIMARY, show_lines=True)
            tbl.add_column("Agent", style="cyan bold")
            tbl.add_column("Role", style="dim")
            tbl.add_column("Status", justify="center")
            tbl.add_column("Points", justify="right", style="green")
            tbl.add_column("Cycles", justify="center")

            for agent in self.agents_registry:
                status = agent.status()
                pts = status.get("points", 0)
                cycles = status.get("cycles", 0)
                tbl.add_row(
                    f"{status['emoji']} {status['name']}",
                    agent.role,
                    "[green]●[/green] Active",
                    f"{pts:.1f}",
                    str(cycles),
                )
            console.print(tbl)

        # Leaderboard
        self.board.display()
        console.print()

    def score(self, results: dict) -> float:
        return 2.0  # Always earns for monitoring
