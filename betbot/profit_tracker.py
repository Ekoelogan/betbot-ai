"""Profit Tracker — monitors earnings, thresholds, and withdrawal alerts."""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / ".betbot"
TRACKER_FILE = DATA_DIR / "profit_tracker.json"
ALERTS_FILE = DATA_DIR / "profit_alerts.log"

DEFAULT_CONFIG = {
    "withdraw_threshold": 50.00,      # Alert when profits hit this amount
    "daily_target": 100.00,           # Daily profit goal
    "weekly_target": 500.00,          # Weekly profit goal
    "monthly_target": 2000.00,        # Monthly profit goal
    "profit_split": 0.50,             # 50% earmarked for withdrawal
    "cashapp_tag": "$itfitzwell197",  # Cash App tag for reference
    "auto_alert": True,               # Log alerts when thresholds hit
}


class ProfitTracker:
    """Tracks profits, withdrawal thresholds, and generates payout alerts."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if TRACKER_FILE.exists():
            return json.loads(TRACKER_FILE.read_text())
        return {
            "config": DEFAULT_CONFIG.copy(),
            "lifetime": {
                "total_profit": 0.0,
                "total_wagered": 0.0,
                "total_withdrawn": 0.0,
                "pending_withdrawal": 0.0,
                "bets_won": 0,
                "bets_lost": 0,
            },
            "daily": {},     # date -> {profit, wagered, bets}
            "alerts": [],    # [{timestamp, type, amount, message}]
            "withdrawals": [],  # [{timestamp, amount, method, status}]
        }

    def save(self):
        TRACKER_FILE.write_text(json.dumps(self.data, indent=2, default=str))

    @property
    def config(self) -> dict:
        return self.data.setdefault("config", DEFAULT_CONFIG.copy())

    @property
    def lifetime(self) -> dict:
        return self.data["lifetime"]

    # ── Record Profits ────────────────────────────────────────────────────

    def record_cycle(self, profit: float, wagered: float, wins: int, losses: int):
        """Record a swarm cycle's results and check thresholds."""
        today = datetime.now().strftime("%Y-%m-%d")
        lt = self.lifetime

        lt["total_profit"] += profit
        lt["total_wagered"] += wagered

        split = self.config["profit_split"]
        if profit > 0:
            lt["pending_withdrawal"] += profit * split

        lt["bets_won"] += wins
        lt["bets_lost"] += losses

        # Daily tracking
        day = self.data["daily"].setdefault(today, {
            "profit": 0.0, "wagered": 0.0, "bets": 0, "wins": 0, "losses": 0,
        })
        day["profit"] += profit
        day["wagered"] += wagered
        day["bets"] += wins + losses
        day["wins"] += wins
        day["losses"] += losses

        self.save()
        self._check_thresholds()

    def _check_thresholds(self):
        """Check if any profit thresholds are hit and generate alerts."""
        cfg = self.config
        lt = self.lifetime
        pending = lt["pending_withdrawal"]
        threshold = cfg["withdraw_threshold"]

        if pending >= threshold and cfg["auto_alert"]:
            alert = {
                "timestamp": datetime.now().isoformat(),
                "type": "WITHDRAWAL_READY",
                "amount": round(pending, 2),
                "cashapp": cfg["cashapp_tag"],
                "message": (
                    f"💰 WITHDRAW READY: ${pending:.2f} available "
                    f"(50% of profits) → Send to {cfg['cashapp_tag']}"
                ),
            }
            self.data["alerts"].append(alert)
            self.save()

            # Also append to alerts log file
            with open(ALERTS_FILE, "a") as f:
                f.write(f"[{alert['timestamp']}] {alert['message']}\n")

        # Daily target check
        today = datetime.now().strftime("%Y-%m-%d")
        day = self.data["daily"].get(today, {})
        daily_profit = day.get("profit", 0)
        if daily_profit >= cfg["daily_target"]:
            alert = {
                "timestamp": datetime.now().isoformat(),
                "type": "DAILY_TARGET_HIT",
                "amount": round(daily_profit, 2),
                "message": f"🎯 DAILY TARGET HIT: ${daily_profit:.2f} / ${cfg['daily_target']:.2f}",
            }
            # Only alert once per day
            today_alerts = [a for a in self.data["alerts"]
                           if a.get("type") == "DAILY_TARGET_HIT"
                           and a["timestamp"].startswith(today)]
            if not today_alerts:
                self.data["alerts"].append(alert)
                self.save()

    # ── Withdrawals ───────────────────────────────────────────────────────

    def record_withdrawal(self, amount: float, method: str = "Cash App"):
        """Record a manual withdrawal."""
        lt = self.lifetime
        lt["total_withdrawn"] += amount
        lt["pending_withdrawal"] = max(0, lt["pending_withdrawal"] - amount)

        self.data["withdrawals"].append({
            "timestamp": datetime.now().isoformat(),
            "amount": amount,
            "method": method,
            "destination": self.config["cashapp_tag"],
            "status": "completed",
        })
        self.save()

    # ── Reporting ─────────────────────────────────────────────────────────

    def summary(self) -> dict:
        """Get full profit summary."""
        lt = self.lifetime
        cfg = self.config
        today = datetime.now().strftime("%Y-%m-%d")
        day = self.data["daily"].get(today, {"profit": 0, "wagered": 0, "bets": 0})

        total_bets = lt["bets_won"] + lt["bets_lost"]
        win_rate = (lt["bets_won"] / total_bets * 100) if total_bets > 0 else 0
        roi = (lt["total_profit"] / lt["total_wagered"] * 100) if lt["total_wagered"] > 0 else 0

        return {
            "lifetime_profit": lt["total_profit"],
            "lifetime_wagered": lt["total_wagered"],
            "lifetime_roi": roi,
            "win_rate": win_rate,
            "total_bets": total_bets,
            "pending_withdrawal": lt["pending_withdrawal"],
            "total_withdrawn": lt["total_withdrawn"],
            "cashapp_tag": cfg["cashapp_tag"],
            "withdraw_threshold": cfg["withdraw_threshold"],
            "profit_split": cfg["profit_split"],
            "today_profit": day.get("profit", 0),
            "today_bets": day.get("bets", 0),
            "daily_target": cfg["daily_target"],
            "daily_progress": (day.get("profit", 0) / cfg["daily_target"] * 100)
                              if cfg["daily_target"] > 0 else 0,
            "recent_alerts": self.data["alerts"][-5:],
            "recent_withdrawals": self.data["withdrawals"][-5:],
        }

    def daily_history(self, days: int = 7) -> list[dict]:
        """Get daily profit history."""
        items = sorted(self.data["daily"].items(), reverse=True)[:days]
        return [{"date": d, **v} for d, v in items]
