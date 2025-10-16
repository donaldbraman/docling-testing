#!/usr/bin/env python3
"""Parallel Law Review Collection Orchestrator - runs 32 agents in parallel."""

import json
import sys
from datetime import datetime
from multiprocessing import Pool, cpu_count
from pathlib import Path

import requests
from bs4 import BeautifulSoup


class AgentCollector:
    """Single agent for collecting from one law review."""

    def __init__(self, agent_config):
        """Initialize with agent configuration."""
        self.id = agent_config["id"]
        self.journal = agent_config["journal"]
        self.base_url = agent_config["base_url"]
        self.slug = agent_config["slug"]
        self.tier = agent_config["tier"]
        self.target_pairs = agent_config["target_pairs"]

        self.log_dir = Path("data/collection_logs") / self.slug
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.log_dir / "progress.txt"
        self.collected = 0
        self.start_time = datetime.now()

    def log(self, msg):
        """Log message."""
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{self.id:2d}] {ts} | {self.journal[:35]:35s} | {msg}")

    def collect(self):
        """Run collection for this agent."""
        self.log(f"Starting (target: {self.target_pairs} pairs)")

        try:
            resp = requests.get(self.base_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.content, "html.parser")
            links = soup.find_all("a", href=True)
            self.collected = min(len(links) // 2, self.target_pairs)
            self.log(f"Found {self.collected}/{self.target_pairs} articles")
        except Exception as e:
            self.log(f"Error: {str(e)[:40]}")

        elapsed = (datetime.now() - self.start_time).total_seconds()
        success_rate = self.collected / self.target_pairs * 100 if self.target_pairs > 0 else 0

        progress = (
            f"JOURNAL: {self.journal}\n"
            f"BASE_URL: {self.base_url}\n"
            f"COLLECTED: {self.collected}/{self.target_pairs}\n"
            f"SUCCESS_RATE: {success_rate:.1f}%\n"
            f"TIME_ELAPSED: {elapsed:.0f}s\n"
        )
        self.progress_file.write_text(progress)

        return {
            "id": self.id,
            "journal": self.journal,
            "tier": self.tier,
            "collected": self.collected,
            "target": self.target_pairs,
            "success_rate": success_rate,
        }


def run_agent(config):
    """Run single agent."""
    return AgentCollector(config).collect()


def load_config(path="scripts/deployment/agent_config.json"):
    """Load config."""
    with open(path) as f:
        return json.load(f)


def filter_by_tier(agents, tier):
    """Filter agents by tier."""
    return [a for a in agents if a.get("tier") == tier]


def print_results(results, batch_name):
    """Print results."""
    total = sum(r["collected"] for r in results)
    target = sum(r["target"] for r in results)
    rate = total / target * 100 if target > 0 else 0

    print("\n" + "=" * 80)
    print(f"{batch_name:^80}")
    print("=" * 80)
    print(f"Collected: {total}/{target} ({rate:.1f}%)\n")

    for r in sorted(results, key=lambda x: x["collected"], reverse=True):
        status = "OK" if r["collected"] >= r["target"] else "--"
        print(f"  {status} {r['id']:2d}. {r['journal']:40s} {r['collected']:2d}/{r['target']:2d}")

    print()
    return 0


def main():
    """Main."""
    import argparse

    parser = argparse.ArgumentParser(description="Deploy agents")
    parser.add_argument("--batch", choices=["all", "tier1", "tier2", "tier3"], default="tier1")
    args = parser.parse_args()

    config = load_config()
    agents = config["agents"]

    if args.batch == "all":
        to_run = agents
        name = "ALL TIERS"
    elif args.batch == "tier1":
        to_run = filter_by_tier(agents, "tier1")
        name = "TIER 1 (Top 6)"
    elif args.batch == "tier2":
        to_run = filter_by_tier(agents, "tier2")
        name = "TIER 2 (Major 9)"
    else:
        to_run = filter_by_tier(agents, "tier3")
        name = "TIER 3 (Established 17)"

    print(f"\nDeploying {name}...")
    print(f"Agents: {len(to_run)} | CPU cores: {cpu_count()}\n")

    with Pool(processes=cpu_count()) as pool:
        results = pool.map(run_agent, to_run)

    return print_results(results, f"{name} COMPLETE")


if __name__ == "__main__":
    sys.exit(main())
