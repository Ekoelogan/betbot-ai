"""Base agent class + message bus + leaderboard for BetBot multi-agent swarm."""
from __future__ import annotations

import time
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
PRIMARY = "#ff2d78"
ACCENT = "#ff85b3"
DATA_DIR = Path.home() / ".betbot"


# ── Message Bus ──────────────────────────────────────────────────────────────

@dataclass
class Message:
    sender: str
    topic: str
    data: Any
    timestamp: float = field(default_factory=time.time)
    priority: int = 0  # higher = more important


class MessageBus:
    """Shared communication channel for all agents."""

    def __init__(self):
        self.messages: list[Message] = []
        self.subscribers: dict[str, list[str]] = {}  # topic -> [agent_names]

    def publish(self, sender: str, topic: str, data: Any, priority: int = 0):
        msg = Message(sender=sender, topic=topic, data=data, priority=priority)
        self.messages.append(msg)

    def subscribe(self, agent_name: str, topics: list[str]):
        for t in topics:
            self.subscribers.setdefault(t, []).append(agent_name)

    def get_messages(self, topic: str, since: float = 0) -> list[Message]:
        return sorted(
            [m for m in self.messages if m.topic == topic and m.timestamp > since],
            key=lambda m: m.priority, reverse=True,
        )

    def latest(self, topic: str) -> Message | None:
        msgs = [m for m in self.messages if m.topic == topic]
        return msgs[-1] if msgs else None

    def clear(self):
        self.messages.clear()

    @property
    def stats(self) -> dict:
        by_sender = {}
        for m in self.messages:
            by_sender[m.sender] = by_sender.get(m.sender, 0) + 1
        return {"total": len(self.messages), "by_sender": by_sender}


# ── Leaderboard ──────────────────────────────────────────────────────────────

class Leaderboard:
    """Competition tracker — every agent earns points for contributing to profit."""

    SAVE_FILE = DATA_DIR / "leaderboard.json"

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.scores: dict[str, dict] = self._load()

    def _load(self) -> dict:
        if self.SAVE_FILE.exists():
            return json.loads(self.SAVE_FILE.read_text())
        return {}

    def _save(self):
        self.SAVE_FILE.write_text(json.dumps(self.scores, indent=2))

    def register(self, agent_name: str):
        if agent_name not in self.scores:
            self.scores[agent_name] = {
                "points": 0.0,
                "actions": 0,
                "wins": 0,
                "losses": 0,
                "revenue": 0.0,
                "streak": 0,
                "best_streak": 0,
                "cycles": 0,
            }
            self._save()

    def award(self, agent_name: str, points: float, reason: str = ""):
        if agent_name not in self.scores:
            self.register(agent_name)
        self.scores[agent_name]["points"] += points
        self.scores[agent_name]["actions"] += 1
        self._save()

    def record_win(self, agent_name: str, revenue: float = 0):
        s = self.scores.setdefault(agent_name, {"points": 0, "actions": 0, "wins": 0,
                                                  "losses": 0, "revenue": 0, "streak": 0,
                                                  "best_streak": 0, "cycles": 0})
        s["wins"] += 1
        s["revenue"] += revenue
        s["streak"] += 1
        s["best_streak"] = max(s["best_streak"], s["streak"])
        self._save()

    def record_loss(self, agent_name: str):
        s = self.scores.get(agent_name, {})
        s["losses"] = s.get("losses", 0) + 1
        s["streak"] = 0
        self._save()

    def bump_cycle(self, agent_name: str):
        if agent_name in self.scores:
            self.scores[agent_name]["cycles"] += 1
            self._save()

    def rankings(self) -> list[tuple[int, str, dict]]:
        ranked = sorted(self.scores.items(), key=lambda x: x[1].get("points", 0), reverse=True)
        return [(i + 1, name, data) for i, (name, data) in enumerate(ranked)]

    def display(self):
        rankings = self.rankings()
        if not rankings:
            console.print("[dim]No agents registered yet[/dim]")
            return

        tbl = Table(title=f"[bold {PRIMARY}]🏆 AGENT LEADERBOARD[/bold {PRIMARY}]",
                    border_style=PRIMARY, show_lines=True)
        tbl.add_column("#", justify="center", style="bold")
        tbl.add_column("Agent", style="cyan bold")
        tbl.add_column("Points", justify="right", style="green bold")
        tbl.add_column("Actions", justify="center")
        tbl.add_column("W/L", justify="center")
        tbl.add_column("Revenue", justify="right", style="green")
        tbl.add_column("Win Rate", justify="center")
        tbl.add_column("Streak", justify="center")
        tbl.add_column("Cycles", justify="center")

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for rank, name, data in rankings:
            total = data.get("wins", 0) + data.get("losses", 0)
            wr = f"{data['wins'] / total * 100:.0f}%" if total else "—"
            streak_str = f"🔥{data.get('streak', 0)}" if data.get("streak", 0) > 0 else "—"
            tbl.add_row(
                medals.get(rank, str(rank)),
                name,
                f"{data.get('points', 0):.1f}",
                str(data.get("actions", 0)),
                f"{data.get('wins', 0)}W-{data.get('losses', 0)}L",
                f"${data.get('revenue', 0):.2f}",
                wr,
                streak_str,
                str(data.get("cycles", 0)),
            )
        console.print(tbl)

    def reset(self):
        self.scores.clear()
        self._save()


# ── Base Agent ───────────────────────────────────────────────────────────────

class BaseAgent(ABC):
    """Abstract base for all 12 BetBot swarm agents."""

    name: str = "base"
    emoji: str = "🤖"
    description: str = ""
    role: str = "worker"

    # Topics this agent publishes to / subscribes to
    publishes: list[str] = []
    subscribes: list[str] = []

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        self.bus = bus
        self.board = leaderboard
        self.board.register(self.name)
        self.bus.subscribe(self.name, self.subscribes)
        self._last_read: float = 0
        self.cycle_data: dict = {}

    def log(self, msg: str):
        console.print(f"  [{ACCENT}]{self.emoji} {self.name}[/{ACCENT}] {msg}")

    def inbox(self, topic: str) -> list[Message]:
        msgs = self.bus.get_messages(topic, since=self._last_read)
        return msgs

    def send(self, topic: str, data: Any, priority: int = 0):
        self.bus.publish(self.name, topic, data, priority)

    @abstractmethod
    def think(self, context: dict) -> dict:
        """Analyze current state, decide what to do. Returns action plan."""
        ...

    @abstractmethod
    def act(self, plan: dict) -> dict:
        """Execute the action plan. Returns results."""
        ...

    @abstractmethod
    def score(self, results: dict) -> float:
        """Self-score this cycle's contribution. Returns points earned."""
        ...

    def run_cycle(self, context: dict) -> dict:
        """Full cycle: think → act → score."""
        plan = self.think(context)
        results = self.act(plan)
        points = self.score(results)
        self.board.award(self.name, points)
        self.board.bump_cycle(self.name)
        self._last_read = time.time()
        self.cycle_data = results
        return results

    def status(self) -> dict:
        stats = self.board.scores.get(self.name, {})
        return {
            "name": self.name,
            "emoji": self.emoji,
            "role": self.role,
            "points": stats.get("points", 0),
            "cycles": stats.get("cycles", 0),
            "last_data": self.cycle_data,
        }
