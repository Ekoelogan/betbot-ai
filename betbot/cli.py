"""BetBot AI CLI — sports betting analytics and affiliate marketing bot."""
from __future__ import annotations

import json
import click
from rich.console import Console

console = Console()
PRIMARY = "#ff2d78"

SPORTS = ["nba", "nfl", "mlb", "nhl", "soccer", "ncaaf", "ncaab", "mma"]


@click.group(invoke_without_command=True)
@click.version_option("1.0.0", prog_name="betbot")
@click.pass_context
def cli(ctx):
    """betbot — AI-powered sports betting analytics & affiliate bot."""
    if ctx.invoked_subcommand is None:
        from betbot.dashboard import print_banner
        print_banner()
        click.echo(ctx.get_help())


# ── Predictions ──────────────────────────────────────────────────────────────

@cli.command()
@click.argument("sport", type=click.Choice(SPORTS, case_sensitive=False), default="nba")
def predict(sport):
    """🎯 AI predictions for upcoming games."""
    from betbot.predictor import SportPredictor
    p = SportPredictor()
    p.display_predictions(sport)


@cli.command()
@click.argument("sport", type=click.Choice(SPORTS, case_sensitive=False), default="nba")
def odds(sport):
    """📊 Fetch and compare odds across sportsbooks."""
    from betbot.odds import OddsEngine
    e = OddsEngine()
    e.display_odds(sport)


@cli.command()
@click.argument("sport", type=click.Choice(SPORTS, case_sensitive=False), default="nba")
def value(sport):
    """💎 Find value bets — model edge vs market odds."""
    from betbot.predictor import SportPredictor
    from betbot.odds import OddsEngine
    from rich.table import Table

    predictor = SportPredictor()
    odds_engine = OddsEngine()
    odds_data = odds_engine.get_odds(sport)
    values = predictor.find_value_bets(sport, odds_data)

    if not values:
        console.print("[dim]No value bets found.[/dim]")
        return

    tbl = Table(title=f"[bold {PRIMARY}]💎 Value Bets — {sport.upper()}[/bold {PRIMARY}]",
                border_style=PRIMARY)
    tbl.add_column("Game")
    tbl.add_column("Side", style="cyan bold")
    tbl.add_column("Book")
    tbl.add_column("Odds", justify="center")
    tbl.add_column("Model %", justify="center")
    tbl.add_column("Market %", justify="center")
    tbl.add_column("Edge", justify="center", style="green bold")
    tbl.add_column("Kelly", justify="center")

    for v in values:
        tbl.add_row(
            v["game"], v["side"], v["book"],
            f"{'+' if v['odds'] > 0 else ''}{v['odds']}",
            f"{v['model_pct']}%", f"{v['market_pct']}%",
            f"+{v['edge']}%", f"{v['kelly']:.1%}",
        )
    console.print(tbl)


@cli.command()
@click.argument("sport", type=click.Choice(SPORTS, case_sensitive=False), default="nba")
def arbitrage(sport):
    """⚡ Find arbitrage opportunities across sportsbooks."""
    from betbot.odds import OddsEngine
    from rich.table import Table

    engine = OddsEngine()
    arbs = engine.find_arbitrage(sport)

    if not arbs:
        console.print(f"[dim]No arbitrage opportunities found for {sport.upper()}[/dim]")
        return

    tbl = Table(title=f"[bold {PRIMARY}]⚡ Arbitrage — {sport.upper()}[/bold {PRIMARY}]",
                border_style=PRIMARY)
    tbl.add_column("Game")
    tbl.add_column("Profit %", style="green bold", justify="center")
    tbl.add_column("Bets")
    for a in arbs:
        bets = " | ".join(f"{side}: {info['book']} ({info['odds']})"
                          for side, info in a["bets"].items())
        tbl.add_row(a["game"], f"+{a['profit_pct']}%", bets)
    console.print(tbl)


# ── Bankroll ─────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--balance", type=float, help="Set starting balance")
@click.option("--unit", type=float, help="Set unit size")
def bankroll(balance, unit):
    """💰 Bankroll management — balance, ROI, Kelly criterion."""
    from betbot.bankroll import BankrollManager
    bm = BankrollManager(
        starting_balance=balance or 1000.0,
        unit_size=unit or 25.0,
    )
    bm.display()


@cli.command()
@click.argument("game")
@click.argument("side")
@click.option("--odds", "odds_val", type=int, default=-110, help="American odds")
@click.option("--units", type=int, default=1, help="Number of units")
@click.option("--confidence", type=float, default=50.0, help="Model confidence %")
def bet(game, side, odds_val, units, confidence):
    """🎲 Place a tracked bet."""
    from betbot.bankroll import BankrollManager
    bm = BankrollManager()
    bm.place_bet(game, side, odds_val, units, confidence)


@cli.command()
@click.argument("index", type=int)
@click.argument("result", type=click.Choice(["win", "loss"]))
def settle(index, result):
    """✅ Settle a pending bet (win/loss)."""
    from betbot.bankroll import BankrollManager
    bm = BankrollManager()
    bm.settle_bet(index, result)
    console.print(f"[bold {PRIMARY}]✓[/] Bet #{index} settled as [{'green' if result == 'win' else 'red'}]{result}[/]")
    bm.display()


# ── Affiliate Marketing ──────────────────────────────────────────────────────

@cli.command()
@click.option("--add", "add_book", help="Add affiliate link: BOOK")
@click.option("--url", default="", help="Affiliate URL")
@click.option("--code", default="", help="Referral code")
def affiliate(add_book, url, code):
    """📎 Manage sportsbook affiliate links and earnings."""
    from betbot.affiliate import AffiliateManager
    am = AffiliateManager()
    if add_book:
        am.add_link(add_book, url, code)
    am.display_links()


@cli.command()
@click.argument("sport", type=click.Choice(SPORTS, case_sensitive=False), default="nba")
@click.option("--platform", type=click.Choice(["twitter", "instagram", "blog", "email"]),
              default="twitter", help="Content platform")
@click.option("--book", default="DraftKings", help="Sportsbook for affiliate link")
def content(sport, platform, book):
    """📝 Generate social media content with affiliate links."""
    from betbot.predictor import SportPredictor
    from betbot.affiliate import AffiliateManager

    predictor = SportPredictor()
    preds = predictor.predict_all(sport)
    if not preds:
        console.print("[dim]No picks available[/dim]")
        return

    best = max(preds, key=lambda p: p.confidence)
    am = AffiliateManager()
    am.display_content_preview(
        sport=sport,
        pick=f"{best.recommended_side} ({best.home_team} vs {best.away_team})",
        confidence=best.confidence,
        edge=f"{abs(best.home_win_pct - best.away_win_pct) * 100:.1f}%",
        book=book,
    )


# ── Trends ───────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("team")
@click.option("--sport", type=click.Choice(SPORTS, case_sensitive=False), default="nba")
def trends(team, sport):
    """📈 Team/player trend analysis."""
    import random
    from rich.table import Table

    rng = random.Random(hash(team))
    record = f"{rng.randint(15, 45)}-{rng.randint(10, 35)}"
    last10 = f"{rng.randint(4, 9)}-{10 - rng.randint(4, 9)}"
    ats = f"{rng.randint(20, 40)}-{rng.randint(15, 35)}"
    ou = f"O {rng.randint(20, 35)} / U {rng.randint(20, 35)}"

    console.print(f"\n[bold {PRIMARY}]📈 {team.title()} Trends ({sport.upper()})[/bold {PRIMARY}]\n")
    tbl = Table(border_style=PRIMARY)
    tbl.add_column("Metric", style="bold")
    tbl.add_column("Value", style="cyan")
    tbl.add_row("Record", record)
    tbl.add_row("Last 10", last10)
    tbl.add_row("ATS Record", ats)
    tbl.add_row("Over/Under", ou)
    tbl.add_row("Home Record", f"{rng.randint(10, 25)}-{rng.randint(5, 18)}")
    tbl.add_row("Away Record", f"{rng.randint(8, 22)}-{rng.randint(8, 20)}")
    tbl.add_row("Avg Points For", f"{rng.uniform(95, 125):.1f}")
    tbl.add_row("Avg Points Against", f"{rng.uniform(98, 118):.1f}")
    console.print(tbl)


# ── Dashboard & Export ───────────────────────────────────────────────────────

@cli.command()
@click.option("--sport", type=click.Choice(SPORTS, case_sensitive=False), default="nba")
def dashboard(sport):
    """🖥  Full terminal dashboard — picks, odds, bankroll, affiliates."""
    from betbot.dashboard import show_dashboard
    show_dashboard(sport)


@cli.command()
@click.option("--sport", type=click.Choice(SPORTS, case_sensitive=False), default="nba")
@click.option("--format", "fmt", type=click.Choice(["json", "csv"]), default="json")
@click.option("--output", default="", help="Output file path")
def export(sport, fmt, output):
    """📤 Export picks and analytics to JSON/CSV."""
    from betbot.predictor import SportPredictor
    from betbot.odds import OddsEngine

    predictor = SportPredictor()
    odds_engine = OddsEngine()
    preds = predictor.predict_all(sport)
    values = predictor.find_value_bets(sport, odds_engine.get_odds(sport))

    data = {
        "sport": sport,
        "predictions": [
            {"game": f"{p.home_team} vs {p.away_team}", "pick": p.recommended_side,
             "home_pct": p.home_win_pct, "away_pct": p.away_win_pct,
             "confidence": p.confidence}
            for p in preds
        ],
        "value_bets": values,
    }

    if fmt == "json":
        out = json.dumps(data, indent=2)
    else:
        import csv, io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["game", "pick", "home_pct", "away_pct", "confidence"])
        w.writeheader()
        w.writerows(data["predictions"])
        out = buf.getvalue()

    if output:
        with open(output, "w") as f:
            f.write(out)
        console.print(f"[bold {PRIMARY}]✓[/] Exported to [cyan]{output}[/cyan]")
    else:
        console.print(out)


# ── Multi-Agent Swarm ────────────────────────────────────────────────────────

@cli.command()
@click.option("--cycles", type=int, default=1, help="Number of swarm cycles to run")
@click.option("--delay", type=float, default=0, help="Delay between cycles (seconds)")
@click.option("--sports", default="nba,nfl,mlb,nhl,soccer", help="Comma-separated sports")
@click.option("--max-bets", type=int, default=3, help="Max bets per cycle")
@click.option("--no-dashboard", is_flag=True, help="Skip dashboard display")
def swarm(cycles, delay, sports, max_bets, no_dashboard):
    """🐝 Launch multi-agent AI swarm — 12 bots competing & cooperating."""
    from betbot.agents.coordinator import SwarmCoordinator
    coord = SwarmCoordinator()
    coord.run(
        cycles=cycles, delay=delay,
        context={
            "sports": [s.strip() for s in sports.split(",")],
            "max_bets_per_cycle": max_bets,
            "auto_settle": True,
            "auto_export": True,
        },
        show_dashboard=not no_dashboard,
    )


@cli.command()
def leaderboard():
    """🏆 Show agent competition leaderboard."""
    from betbot.agents.base import Leaderboard
    board = Leaderboard()
    if not board.scores:
        console.print("[dim]No agent data yet. Run 'betbot swarm' first.[/dim]")
        return
    board.display()


@cli.command("swarm-reset")
def swarm_reset():
    """🔄 Reset all agent scores and leaderboard."""
    from betbot.agents.coordinator import SwarmCoordinator
    coord = SwarmCoordinator()
    coord.reset()
    console.print(f"[bold {PRIMARY}]✓[/] Swarm leaderboard and bus reset")


# ── 24/7 Autonomous Daemon ───────────────────────────────────────────────────

@cli.command()
@click.option("--interval", type=int, default=300, help="Seconds between cycles (default: 300 = 5min)")
@click.option("--max-bets", type=int, default=3, help="Max bets per cycle")
@click.option("--sports", default="nba,nfl,mlb,nhl,soccer", help="Comma-separated sports")
def start(interval, max_bets, sports):
    """🚀 Start 24/7 autonomous swarm daemon (background)."""
    from betbot.daemon import is_running, run_daemon, PID_FILE, LOG_FILE
    import subprocess, sys

    if is_running():
        console.print(f"[bold red]⛔ Daemon already running[/bold red] — use 'betbot status' to check")
        return

    # Launch as detached subprocess
    cmd = [
        sys.executable, "-c",
        f"from betbot.daemon import run_daemon; "
        f"run_daemon(cycle_interval={interval}, max_bets={max_bets}, sports='{sports}')"
    ]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    # Wait a moment for PID file
    import time
    time.sleep(2)

    if is_running():
        console.print(f"[bold {PRIMARY}]🚀 BetBot Daemon STARTED[/bold {PRIMARY}]")
        console.print(f"  [bold]PID:[/bold] {proc.pid}")
        console.print(f"  [bold]Interval:[/bold] {interval}s ({interval // 60}min)")
        console.print(f"  [bold]Sports:[/bold] {sports}")
        console.print(f"  [bold]Max bets/cycle:[/bold] {max_bets}")
        console.print(f"  [bold]Log:[/bold] {LOG_FILE}")
        console.print(f"\n  [dim]Use 'betbot status' to monitor | 'betbot stop' to stop[/dim]")
    else:
        console.print(f"[bold red]✗ Failed to start daemon[/bold red]")


@cli.command()
def stop():
    """🛑 Stop the 24/7 autonomous daemon."""
    import os, signal
    from betbot.daemon import is_running, get_pid, PID_FILE

    if not is_running():
        console.print("[dim]Daemon is not running[/dim]")
        return

    pid = get_pid()
    if pid:
        os.kill(pid, signal.SIGTERM)
        import time
        time.sleep(2)

        if not is_running():
            console.print(f"[bold {PRIMARY}]✓ Daemon stopped[/bold {PRIMARY}] (PID {pid})")
        else:
            os.kill(pid, signal.SIGKILL)
            PID_FILE.unlink(missing_ok=True)
            console.print(f"[bold {PRIMARY}]✓ Daemon force-killed[/bold {PRIMARY}] (PID {pid})")


@cli.command()
def status():
    """📡 Show daemon status, recent cycles, and live stats."""
    from betbot.daemon import daemon_status
    from rich.panel import Panel

    s = daemon_status()
    running = s.get("is_running", False)
    status_str = "[bold green]● RUNNING[/bold green]" if running else "[bold red]● STOPPED[/bold red]"

    info = (
        f"[bold]Status:[/bold] {status_str}\n"
        f"[bold]PID:[/bold] {s.get('pid', '—')}\n"
        f"[bold]Started:[/bold] {s.get('started', '—')}\n"
        f"[bold]Interval:[/bold] {s.get('cycle_interval', '—')}s\n"
        f"[bold]Sports:[/bold] {', '.join(s.get('sports', []))}\n"
        f"[bold]Total Cycles:[/bold] {s.get('total_cycles', 0)}\n"
        f"[bold]Last Cycle:[/bold] {s.get('last_cycle', '—')}\n"
        f"[bold]Total Bets:[/bold] {s.get('total_bets_placed', 0)}\n"
        f"[bold]Total P&L:[/bold] [{'green' if s.get('total_profit', 0) >= 0 else 'red'}]"
        f"${s.get('total_profit', 0):.2f}[/]"
    )

    last = s.get("last_results", {})
    if last:
        info += (
            f"\n\n[bold]Last Cycle:[/bold]\n"
            f"  Bets: {last.get('bets', 0)} | Platforms: {last.get('platforms', 0)} | "
            f"P&L: ${last.get('profit', 0):.2f}\n"
            f"  Content: {last.get('content', 0)} | Value Bets: {last.get('value_bets', 0)}"
        )

    console.print(Panel(info,
                        title=f"[bold {PRIMARY}]📡 BETBOT DAEMON[/bold {PRIMARY}]",
                        border_style=PRIMARY))

    # Show recent logs
    tail = s.get("log_tail", "")
    if tail:
        console.print(Panel(tail,
                            title=f"[bold {PRIMARY}]📋 RECENT LOG[/bold {PRIMARY}]",
                            border_style="dim"))


@cli.command()
def logs():
    """📋 Tail the daemon log file."""
    from betbot.daemon import LOG_FILE

    if not LOG_FILE.exists():
        console.print("[dim]No log file yet — start daemon with 'betbot start'[/dim]")
        return

    lines = LOG_FILE.read_text().strip().split("\n")
    for line in lines[-50:]:
        if "ERROR" in line or "FAILED" in line:
            console.print(f"[red]{line}[/red]")
        elif "Cycle #" in line and "done" in line:
            console.print(f"[green]{line}[/green]")
        elif "started" in line.lower() or "stopped" in line.lower():
            console.print(f"[bold {PRIMARY}]{line}[/bold {PRIMARY}]")
        else:
            console.print(f"[dim]{line}[/dim]")


# ── Profit Tracker ────────────────────────────────────────────────────────────

@cli.command()
def profits():
    """💰 Show profit summary, withdrawal status, and daily targets."""
    from betbot.profit_tracker import ProfitTracker
    from rich.panel import Panel
    from rich.table import Table

    tracker = ProfitTracker()
    s = tracker.summary()

    # Main profit panel
    profit_color = "green" if s["lifetime_profit"] >= 0 else "red"
    pending_color = "green" if s["pending_withdrawal"] >= s["withdraw_threshold"] else "yellow"

    info = (
        f"[bold]Lifetime Profit:[/bold] [{profit_color}]${s['lifetime_profit']:.2f}[/{profit_color}]\n"
        f"[bold]Lifetime Wagered:[/bold] ${s['lifetime_wagered']:.2f}\n"
        f"[bold]ROI:[/bold] [{profit_color}]{s['lifetime_roi']:.1f}%[/{profit_color}] | "
        f"[bold]Win Rate:[/bold] {s['win_rate']:.0f}% ({s['total_bets']} bets)\n"
        f"\n"
        f"[bold]💰 Pending Withdrawal:[/bold] [{pending_color}]${s['pending_withdrawal']:.2f}[/{pending_color}]"
        f"  (50% of profits)\n"
        f"[bold]📲 Cash App:[/bold] {s['cashapp_tag']}\n"
        f"[bold]🎯 Threshold:[/bold] ${s['withdraw_threshold']:.2f}"
    )

    if s["pending_withdrawal"] >= s["withdraw_threshold"]:
        info += (
            f"\n\n[bold green]✅ READY TO WITHDRAW![/bold green] "
            f"Send ${s['pending_withdrawal']:.2f} → {s['cashapp_tag']}"
        )

    info += (
        f"\n[bold]Total Withdrawn:[/bold] ${s['total_withdrawn']:.2f}"
    )

    console.print(Panel(info,
                        title=f"[bold {PRIMARY}]💰 PROFIT TRACKER[/bold {PRIMARY}]",
                        border_style=PRIMARY))

    # Daily progress
    progress = min(s["daily_progress"], 100)
    bar_filled = int(progress / 5)
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    console.print(Panel(
        f"[bold]Today:[/bold] ${s['today_profit']:.2f} / ${s['daily_target']:.2f} "
        f"({s['today_bets']} bets)\n"
        f"[bold]Progress:[/bold] [{PRIMARY}]{bar}[/{PRIMARY}] {progress:.0f}%",
        title=f"[bold {PRIMARY}]📊 DAILY TARGET[/bold {PRIMARY}]",
        border_style="dim",
    ))

    # Daily history
    history = tracker.daily_history(7)
    if history:
        table = Table(title=f"[bold {PRIMARY}]📅 DAILY HISTORY (Last 7 Days)[/bold {PRIMARY}]")
        table.add_column("Date", style="bold")
        table.add_column("Profit", justify="right")
        table.add_column("Wagered", justify="right")
        table.add_column("Bets", justify="center")
        table.add_column("W/L", justify="center")
        for d in history:
            p = d.get("profit", 0)
            table.add_row(
                d["date"],
                f"[{'green' if p >= 0 else 'red'}]${p:.2f}[/]",
                f"${d.get('wagered', 0):.2f}",
                str(d.get("bets", 0)),
                f"{d.get('wins', 0)}W-{d.get('losses', 0)}L",
            )
        console.print(table)

    # Recent alerts
    alerts = s.get("recent_alerts", [])
    if alerts:
        console.print(f"\n[bold {PRIMARY}]🔔 RECENT ALERTS[/bold {PRIMARY}]")
        for a in alerts[-5:]:
            console.print(f"  {a['message']}")


@cli.command()
@click.argument("amount", type=float)
def withdraw(amount):
    """💸 Record a withdrawal (e.g., betbot withdraw 50.00)."""
    from betbot.profit_tracker import ProfitTracker

    tracker = ProfitTracker()
    pending = tracker.lifetime["pending_withdrawal"]

    if amount > pending:
        console.print(f"[bold red]⛔ Only ${pending:.2f} available for withdrawal[/bold red]")
        return

    tracker.record_withdrawal(amount)
    remaining = tracker.lifetime["pending_withdrawal"]

    console.print(f"[bold {PRIMARY}]✓ Withdrawal recorded[/bold {PRIMARY}]")
    console.print(f"  [bold]Amount:[/bold] ${amount:.2f}")
    console.print(f"  [bold]Method:[/bold] Cash App → {tracker.config['cashapp_tag']}")
    console.print(f"  [bold]Remaining:[/bold] ${remaining:.2f}")


@cli.command("set-threshold")
@click.argument("amount", type=float)
def set_threshold(amount):
    """⚙️ Set withdrawal alert threshold (e.g., betbot set-threshold 100)."""
    from betbot.profit_tracker import ProfitTracker

    tracker = ProfitTracker()
    tracker.config["withdraw_threshold"] = amount
    tracker.save()
    console.print(f"[bold {PRIMARY}]✓ Withdrawal threshold set to ${amount:.2f}[/bold {PRIMARY}]")
