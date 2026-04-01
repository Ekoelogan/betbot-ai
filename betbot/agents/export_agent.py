"""ExportAgent — exports swarm data to JSON/CSV for analysis and records."""
from __future__ import annotations
import json
import time
from pathlib import Path
from betbot.agents.base import BaseAgent, MessageBus, Leaderboard, DATA_DIR


class ExportAgent(BaseAgent):
    name = "📤 Export"
    emoji = "📤"
    description = "Data exporter — saves swarm cycle data to JSON/CSV for records & analysis"
    role = "operations"
    publishes = ["export_complete"]
    subscribes = ["bets_placed", "settle_results", "value_bets",
                  "content_generated", "system_health"]

    EXPORT_DIR = DATA_DIR / "exports"

    def __init__(self, bus: MessageBus, leaderboard: Leaderboard):
        super().__init__(bus, leaderboard)
        self.EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    def think(self, context: dict) -> dict:
        fmt = context.get("export_format", "json")
        auto_export = context.get("auto_export", True)
        return {"format": fmt, "auto_export": auto_export}

    def act(self, plan: dict) -> dict:
        if not plan["auto_export"]:
            self.log("Auto-export disabled")
            return {"exported": False, "file": ""}

        # Collect all bus data
        cycle_data = {
            "timestamp": time.time(),
            "cycle_id": int(time.time()),
        }

        for topic in ["bets_placed", "settle_results", "value_bets",
                       "content_generated", "system_health", "arb_opportunities",
                       "predictions", "trends_data", "affiliate_stats"]:
            msg = self.bus.latest(topic)
            if msg:
                cycle_data[topic] = msg.data

        # Add leaderboard snapshot
        cycle_data["leaderboard"] = self.board.scores

        # Save
        ts = int(time.time())
        if plan["format"] == "json":
            filepath = self.EXPORT_DIR / f"cycle_{ts}.json"
            filepath.write_text(json.dumps(cycle_data, indent=2, default=str))
        else:
            import csv
            filepath = self.EXPORT_DIR / f"cycle_{ts}.csv"
            with open(filepath, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["topic", "data"])
                for k, v in cycle_data.items():
                    w.writerow([k, json.dumps(v, default=str)])

        self.send("export_complete", {"file": str(filepath), "size": filepath.stat().st_size}, priority=1)
        self.log(f"Exported cycle data → {filepath.name} ({filepath.stat().st_size} bytes)")

        return {"exported": True, "file": str(filepath),
                "size": filepath.stat().st_size, "topics": len(cycle_data) - 2}

    def score(self, results: dict) -> float:
        if results.get("exported"):
            return 3.0 + results.get("topics", 0) * 0.5
        return 0.5
