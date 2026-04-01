"""BetBot Daemon — runs the 12-agent swarm 24/7 autonomously in the background."""
from __future__ import annotations

import os
import sys
import time
import json
import signal
import logging
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / ".betbot"
PID_FILE = DATA_DIR / "daemon.pid"
LOG_FILE = DATA_DIR / "daemon.log"
STATE_FILE = DATA_DIR / "daemon_state.json"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("betbot-daemon")


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def is_running() -> bool:
    if not PID_FILE.exists():
        return False
    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        PID_FILE.unlink(missing_ok=True)
        return False


def get_pid() -> int | None:
    if PID_FILE.exists():
        return int(PID_FILE.read_text().strip())
    return None


def run_daemon(cycle_interval: int = 300, max_bets: int = 3,
               sports: str = "nba,nfl,mlb,nhl,soccer"):
    """Main daemon loop — runs swarm cycles forever."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Write PID
    PID_FILE.write_text(str(os.getpid()))

    # Graceful shutdown
    running = True

    def _shutdown(signum, frame):
        nonlocal running
        running = False
        log.info("Shutdown signal received — finishing current cycle...")

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    log.info("=" * 60)
    log.info("BetBot Daemon started — PID %d", os.getpid())
    log.info("Cycle interval: %ds | Max bets: %d | Sports: %s",
             cycle_interval, max_bets, sports)
    log.info("=" * 60)

    sport_list = [s.strip() for s in sports.split(",")]
    cycle_count = 0

    # Suppress Rich console output in daemon mode
    os.environ["BETBOT_DAEMON"] = "1"

    from betbot.agents.coordinator import SwarmCoordinator
    coord = SwarmCoordinator()

    state = {
        "status": "running",
        "pid": os.getpid(),
        "started": datetime.now().isoformat(),
        "cycle_interval": cycle_interval,
        "sports": sport_list,
        "max_bets": max_bets,
        "total_cycles": 0,
        "last_cycle": None,
        "total_bets_placed": 0,
        "total_profit": 0.0,
    }
    _save_state(state)

    while running:
        cycle_count += 1
        cycle_start = time.time()

        try:
            log.info("--- Cycle #%d starting ---", cycle_count)

            results = coord.run_cycle(
                context={
                    "sports": sport_list,
                    "max_bets_per_cycle": max_bets,
                    "auto_settle": True,
                    "auto_export": True,
                    "generate_retail_content": True,
                    "optimize_all_networks": True,
                    "multi_platform": True,
                },
                show_dashboard=False,
            )

            # Extract stats from results
            bets_placed = results.get("bet", {}).get("placed", 0)
            settle_profit = results.get("settle", {}).get("profit", 0)
            content_pieces = results.get("content", {}).get("pieces", 0)
            value_bets = results.get("value", {}).get("total_value_bets", 0)
            platforms = results.get("bet", {}).get("platforms", 0)
            settle_wins = results.get("settle", {}).get("wins", 0)
            settle_losses = results.get("settle", {}).get("losses", 0)
            wagered = results.get("bet", {}).get("wagered", 0)

            # Record in profit tracker
            from betbot.profit_tracker import ProfitTracker
            tracker = ProfitTracker()
            tracker.record_cycle(
                profit=settle_profit,
                wagered=wagered if wagered else bets_placed * 25.0,
                wins=settle_wins,
                losses=settle_losses,
            )
            pending = tracker.lifetime["pending_withdrawal"]
            if pending >= tracker.config["withdraw_threshold"]:
                log.info(
                    "💰 WITHDRAWAL READY: $%.2f pending → %s",
                    pending, tracker.config["cashapp_tag"],
                )

            state["total_cycles"] = cycle_count
            state["last_cycle"] = datetime.now().isoformat()
            state["total_bets_placed"] += bets_placed
            state["total_profit"] += settle_profit
            state["last_results"] = {
                "bets": bets_placed,
                "profit": settle_profit,
                "content": content_pieces,
                "value_bets": value_bets,
                "platforms": platforms,
            }
            _save_state(state)

            elapsed = time.time() - cycle_start
            log.info(
                "Cycle #%d done in %.1fs — %d bets across %d platforms | "
                "P&L: $%.2f | %d content | %d value bets",
                cycle_count, elapsed, bets_placed, platforms,
                settle_profit, content_pieces, value_bets,
            )

        except Exception as e:
            log.error("Cycle #%d FAILED: %s", cycle_count, e, exc_info=True)
            state["last_error"] = str(e)
            _save_state(state)

        # Sleep until next cycle
        if running:
            log.info("Sleeping %ds until next cycle...", cycle_interval)
            # Sleep in small increments so we can respond to signals
            for _ in range(cycle_interval):
                if not running:
                    break
                time.sleep(1)

    # Cleanup
    state["status"] = "stopped"
    state["stopped"] = datetime.now().isoformat()
    _save_state(state)
    PID_FILE.unlink(missing_ok=True)
    log.info("Daemon stopped after %d cycles", cycle_count)


def daemon_status() -> dict:
    """Get daemon status for display."""
    state = _load_state()
    state["is_running"] = is_running()
    state["pid"] = get_pid()
    state["log_file"] = str(LOG_FILE)
    state["log_tail"] = ""
    if LOG_FILE.exists():
        lines = LOG_FILE.read_text().strip().split("\n")
        state["log_tail"] = "\n".join(lines[-15:])
    return state
