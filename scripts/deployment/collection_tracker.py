#!/usr/bin/env python3
"""
Law Review Collection Tracker - Aggregates results from parallel collection agents.

Tracks progress across 30+ sub-agents collecting HTML-PDF pairs from law reviews.
Provides real-time dashboard, final report, and data quality validation.

Usage:
    uv run python scripts/deployment/collection_tracker.py --mode dashboard
    uv run python scripts/deployment/collection_tracker.py --mode report
    uv run python scripts/deployment/collection_tracker.py --mode validate
"""

import json
import sys
from contextlib import suppress
from datetime import datetime
from pathlib import Path


class CollectionTracker:
    """Track progress of parallel collection agents."""

    def __init__(self, config_path: str = "scripts/deployment/agent_config.json"):
        """Initialize tracker with agent configuration.

        Args:
            config_path: Path to agent_config.json
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.log_dir = Path("data/collection_logs")
        self.html_dir = Path("data/raw_html")
        self.pdf_dir = Path("data/raw_pdf")

    def _load_config(self) -> dict:
        """Load agent configuration from JSON."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        with open(self.config_path) as f:
            return json.load(f)

    def get_agent_status(self, agent_id: int) -> dict:
        """Get status for a specific agent.

        Args:
            agent_id: Agent ID (1-32)

        Returns:
            Dict with agent status info
        """
        if agent_id < 1 or agent_id > len(self.config["agents"]):
            raise ValueError(f"Invalid agent ID: {agent_id}")

        agent = self.config["agents"][agent_id - 1]
        slug = agent["slug"]
        progress_file = self.log_dir / slug / "progress.txt"

        status = {
            "id": agent_id,
            "journal": agent["journal"],
            "base_url": agent["base_url"],
            "target": agent["target_pairs"],
            "collected": 0,
            "success_rate": 0,
            "status": "not_started",
            "error": None,
        }

        # Read progress file if exists
        if progress_file.exists():
            status = self._parse_progress_file(progress_file, status)

        # Count actual files
        html_files = list(self.html_dir.glob(f"{slug}_*.html"))
        pdf_files = list(self.pdf_dir.glob(f"{slug}_*.pdf"))
        pairs = min(len(html_files), len(pdf_files))

        status["collected"] = pairs
        status["html_files"] = len(html_files)
        status["pdf_files"] = len(pdf_files)
        status["success_rate"] = (pairs / status["target"] * 100) if pairs > 0 else 0

        if pairs >= status["target"]:
            status["status"] = "complete"
        elif pairs > 0:
            status["status"] = "in_progress"

        return status

    def _parse_progress_file(self, progress_file: Path, status: dict) -> dict:
        """Parse progress.txt file for status.

        Args:
            progress_file: Path to progress.txt
            status: Status dict to update

        Returns:
            Updated status dict
        """
        try:
            content = progress_file.read_text()
            if "SUCCESS_RATE:" in content:
                for line in content.split("\n"):
                    if "SUCCESS_RATE:" in line:
                        rate_str = line.split(":")[-1].strip().rstrip("%")
                        with suppress(ValueError):
                            status["success_rate"] = float(rate_str)
                    if "BLOCKERS:" in line and "None" not in line:
                        status["error"] = line.split(":", 1)[-1].strip()
        except Exception as e:
            status["error"] = f"Could not parse progress: {str(e)}"

        return status

    def get_all_status(self) -> dict:
        """Get status for all agents.

        Returns:
            Dict with overall and per-agent status
        """
        statuses = []
        for agent_id in range(1, len(self.config["agents"]) + 1):
            statuses.append(self.get_agent_status(agent_id))

        total_target = sum(s["target"] for s in statuses)
        total_collected = sum(s["collected"] for s in statuses)

        return {
            "timestamp": datetime.now().isoformat(),
            "total_agents": len(self.config["agents"]),
            "total_target_pairs": total_target,
            "total_collected_pairs": total_collected,
            "overall_success_rate": (
                total_collected / total_target * 100 if total_target > 0 else 0
            ),
            "agents": statuses,
        }

    def print_dashboard(self) -> None:
        """Print real-time collection dashboard."""
        status = self.get_all_status()

        print("\n" + "=" * 100)
        print("LAW REVIEW COLLECTION DASHBOARD")
        print("=" * 100)
        print(f"Timestamp: {status['timestamp']}")
        print(
            f"Overall Progress: {status['total_collected_pairs']}/{status['total_target_pairs']} pairs "
            f"({status['overall_success_rate']:.1f}%)"
        )
        print("-" * 100)

        # Group by tier
        tiers = {"tier1": [], "tier2": [], "tier3": []}
        for agent in status["agents"]:
            tier = self.config["agents"][agent["id"] - 1]["tier"]
            tiers[tier].append(agent)

        for tier_name in ["tier1", "tier2", "tier3"]:
            tier_agents = tiers[tier_name]
            tier_total = sum(a["collected"] for a in tier_agents)
            tier_target = sum(a["target"] for a in tier_agents)

            tier_label = {
                "tier1": "TIER 1: Top Law Reviews (6 agents)",
                "tier2": "TIER 2: Major Law Reviews (9 agents)",
                "tier3": "TIER 3: Established Reviews (17 agents)",
            }[tier_name]

            print(f"\n{tier_label}")
            print(
                f"  Subtotal: {tier_total}/{tier_target} pairs ({tier_total / tier_target * 100:.1f}%)"
            )
            print("  " + "-" * 90)

            for agent in tier_agents:
                status_indicator = {
                    "complete": "✓",
                    "in_progress": "⏳",
                    "not_started": "○",
                }[agent["status"]]

                print(
                    f"  {status_indicator} Agent {agent['id']:2d}: {agent['journal']:45s} "
                    f"{agent['collected']:2d}/{agent['target']:2d} "
                    f"({agent['success_rate']:5.1f}%)"
                )
                if agent.get("error"):
                    print(f"      ⚠️  {agent['error']}")

        print("\n" + "=" * 100 + "\n")

    def generate_report(self, output_file: str | None = None) -> str:
        """Generate detailed collection report.

        Args:
            output_file: Optional path to save report

        Returns:
            Report as string
        """
        status = self.get_all_status()

        report = []
        report.append("# Law Review Collection Report\n")
        report.append(f"**Generated:** {status['timestamp']}\n")
        report.append(
            f"**Overall Progress:** {status['total_collected_pairs']}/{status['total_target_pairs']} "
            f"pairs ({status['overall_success_rate']:.1f}%)\n\n"
        )

        report.append("## Summary Statistics\n")
        report.append(f"- Total Agents: {status['total_agents']}\n")
        report.append(
            f"- Agents Complete: {sum(1 for a in status['agents'] if a['status'] == 'complete')}\n"
        )
        report.append(
            f"- Agents In Progress: {sum(1 for a in status['agents'] if a['status'] == 'in_progress')}\n"
        )
        report.append(
            f"- Agents Not Started: {sum(1 for a in status['agents'] if a['status'] == 'not_started')}\n\n"
        )

        # Detailed per-agent status
        report.append("## Agent Status Details\n\n")

        for tier_name in ["tier1", "tier2", "tier3"]:
            tier_agents = [
                a
                for a in status["agents"]
                if self.config["agents"][a["id"] - 1]["tier"] == tier_name
            ]
            if not tier_agents:
                continue

            tier_label = {
                "tier1": "### Tier 1: Top Law Reviews",
                "tier2": "### Tier 2: Major Law Reviews",
                "tier3": "### Tier 3: Established Reviews",
            }[tier_name]

            report.append(f"{tier_label}\n\n")

            for agent in tier_agents:
                status_emoji = {"complete": "✓", "in_progress": "⏳", "not_started": "○"}[
                    agent["status"]
                ]
                report.append(f"{status_emoji} **Agent {agent['id']}:** {agent['journal']}\n")
                report.append(
                    f"   - Collected: {agent['collected']}/{agent['target']} "
                    f"({agent['success_rate']:.1f}%)\n"
                )
                report.append(f"   - HTML Files: {agent.get('html_files', 0)}\n")
                report.append(f"   - PDF Files: {agent.get('pdf_files', 0)}\n")
                if agent.get("error"):
                    report.append(f"   - Error: {agent['error']}\n")
                report.append("\n")

        report_text = "".join(report)

        if output_file:
            Path(output_file).write_text(report_text)
            print(f"✓ Report saved to {output_file}")

        return report_text

    def validate_files(self) -> dict:
        """Validate collected HTML and PDF files.

        Returns:
            Dict with validation results
        """
        results = {
            "html_files": {"total": 0, "valid": 0, "invalid": []},
            "pdf_files": {"total": 0, "valid": 0, "invalid": []},
            "pairs": {"total": 0, "valid": 0, "mismatched": []},
        }

        # Check HTML files
        for html_file in self.html_dir.glob("*.html"):
            results["html_files"]["total"] += 1
            try:
                content = html_file.read_text()
                if len(content) > 5000 and (
                    "article" in content.lower() or "text" in content.lower()
                ):
                    results["html_files"]["valid"] += 1
                else:
                    results["html_files"]["invalid"].append(html_file.name)
            except Exception as e:
                results["html_files"]["invalid"].append(f"{html_file.name}: {str(e)}")

        # Check PDF files
        for pdf_file in self.pdf_dir.glob("*.pdf"):
            results["pdf_files"]["total"] += 1
            try:
                if pdf_file.stat().st_size > 50000:  # Should be > 50KB
                    results["pdf_files"]["valid"] += 1
                else:
                    results["pdf_files"]["invalid"].append(pdf_file.name)
            except Exception as e:
                results["pdf_files"]["invalid"].append(f"{pdf_file.name}: {str(e)}")

        # Check for pairs
        html_names = {f.stem for f in self.html_dir.glob("*.html")}
        pdf_names = {f.stem for f in self.pdf_dir.glob("*.pdf")}
        pairs = html_names & pdf_names

        results["pairs"]["total"] = len(pairs)
        results["pairs"]["valid"] = len(pairs)
        results["pairs"]["mismatched"] = list(html_names ^ pdf_names)

        return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Law Review Collection Tracker")
    parser.add_argument(
        "--mode",
        choices=["dashboard", "report", "validate"],
        default="dashboard",
        help="Display mode",
    )
    parser.add_argument("--output", help="Output file for report")

    args = parser.parse_args()

    try:
        tracker = CollectionTracker()

        if args.mode == "dashboard":
            tracker.print_dashboard()

        elif args.mode == "report":
            report = tracker.generate_report(args.output)
            if not args.output:
                print(report)

        elif args.mode == "validate":
            results = tracker.validate_files()
            print("\n" + "=" * 60)
            print("FILE VALIDATION RESULTS")
            print("=" * 60)
            print(
                f"HTML Files: {results['html_files']['valid']}/{results['html_files']['total']} valid"
            )
            print(
                f"PDF Files: {results['pdf_files']['valid']}/{results['pdf_files']['total']} valid"
            )
            print(f"Pairs: {results['pairs']['valid']}/{results['pairs']['total']} valid")
            if results["pairs"]["mismatched"]:
                print(f"Mismatched: {results['pairs']['mismatched']}")
            print("=" * 60 + "\n")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
