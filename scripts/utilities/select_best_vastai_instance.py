#!/usr/bin/env python3
"""
Smart instance selection for vast.ai based on cost-effectiveness.

Selection Algorithm:
- Filters: reliability > 98%, CUDA >= 12.0, disk >= 50GB
- Scoring: Weighted formula balancing price, reliability, and network speed
- Returns top 3 candidates

Usage:
    uv run python scripts/utilities/select_best_vastai_instance.py --gpu RTX_4090
"""

import argparse
import json
import subprocess
import sys


def search_instances(gpu_name: str, max_price: float = 0.60) -> list[dict]:
    """Search for available instances."""
    print(f"Searching for {gpu_name} instances (max ${max_price}/hr)...")

    cmd = ["vastai", "search", "offers", f"gpu_name={gpu_name}", "-o", "dph+", "--raw"]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    instances = json.loads(result.stdout)

    # Filter by max price
    instances = [i for i in instances if i.get("dph_total", 999) <= max_price]

    print(f"Found {len(instances)} instances under ${max_price}/hr")
    return instances


def filter_instances(instances: list[dict]) -> list[dict]:
    """Filter instances by minimum requirements."""
    filtered = []

    for inst in instances:
        # Skip if missing critical fields
        if not all(k in inst for k in ["dph_total", "reliability2", "cuda_max_good"]):
            continue

        # Minimum requirements
        # reliability2 is stored as decimal (0.98 = 98%)
        if inst["reliability2"] < 0.98:  # 98% reliability minimum
            continue
        if inst["cuda_max_good"] < 12.0:  # CUDA 12.0+ required
            continue
        if inst.get("disk_space", 0) < 50:  # 50GB minimum disk
            continue

        filtered.append(inst)

    print(f"After filtering: {len(filtered)} instances meet requirements")
    return filtered


def score_instance(inst: dict) -> float:
    """
    Score instance for cost-effectiveness.

    Formula: score = (reliability * network_speed) / (price^2)

    Higher score = better value
    - Price squared to heavily favor cheaper instances
    - Reliability weighted heavily (multiplicative)
    - Network speed bonus for faster transfers
    """
    price = inst["dph_total"]
    reliability = inst["reliability2"]  # Already 0-1 decimal

    # Network speed in Gbps (download + upload average)
    net_down = inst.get("inet_down", 100) / 1000.0  # Mbps to Gbps
    net_up = inst.get("inet_up", 100) / 1000.0
    network_speed = (net_down + net_up) / 2.0

    # Normalize network speed (typical range: 0.1 - 10 Gbps)
    network_factor = min(network_speed / 1.0, 2.0)  # Cap at 2x bonus

    # Score formula
    score = (reliability * (1 + network_factor)) / (price**2)

    return score


def select_best_instances(instances: list[dict], top_n: int = 3) -> list[dict]:
    """Select top N instances by score."""
    # Score all instances
    for inst in instances:
        inst["_score"] = score_instance(inst)

    # Sort by score (descending)
    instances.sort(key=lambda x: x["_score"], reverse=True)

    return instances[:top_n]


def format_instance(inst: dict, rank: int) -> str:
    """Format instance for display."""
    location = inst.get("geolocation", "Unknown")

    return f"""
Rank {rank}: Instance {inst["id"]} (Score: {inst["_score"]:.2f})
  Price:       ${inst["dph_total"]:.4f}/hr
  Reliability: {inst["reliability2"] * 100:.1f}%
  CUDA:        {inst["cuda_max_good"]:.1f}
  Location:    {location}
  Network:     ↓{inst.get("inet_down", 0):.0f} Mbps / ↑{inst.get("inet_up", 0):.0f} Mbps
  Disk:        {inst.get("disk_space", 0):.0f} GB
  RAM:         {inst.get("gpu_ram", 0):.0f} GB
"""


def main():
    parser = argparse.ArgumentParser(
        description="Select best vast.ai instance for cost-effectiveness"
    )
    parser.add_argument(
        "--gpu", default="RTX_4090", help="GPU model to search for (default: RTX_4090)"
    )
    parser.add_argument(
        "--max-price", type=float, default=0.60, help="Maximum price per hour (default: 0.60)"
    )
    parser.add_argument(
        "--top-n", type=int, default=3, help="Number of top instances to show (default: 3)"
    )
    parser.add_argument(
        "--auto-select",
        action="store_true",
        help="Automatically return best instance ID (for scripts)",
    )

    args = parser.parse_args()

    # Search for instances
    instances = search_instances(args.gpu, args.max_price)

    if not instances:
        print(f"No {args.gpu} instances found under ${args.max_price}/hr")
        sys.exit(1)

    # Filter by requirements
    instances = filter_instances(instances)

    if not instances:
        print("No instances meet minimum requirements (98% reliability, CUDA 12+, 50GB disk)")
        sys.exit(1)

    # Select best instances
    best_instances = select_best_instances(instances, args.top_n)

    print("\n" + "=" * 70)
    print("TOP COST-EFFECTIVE INSTANCES")
    print("=" * 70)

    for i, inst in enumerate(best_instances, 1):
        print(format_instance(inst, i))

    print("=" * 70)
    print("\nSelection Algorithm:")
    print("  Score = (reliability × network_speed) / (price²)")
    print("  Higher score = better cost-effectiveness")
    print("=" * 70)

    if args.auto_select:
        # Return best instance ID for scripting
        print(f"\nBEST_INSTANCE_ID={best_instances[0]['id']}")
        return best_instances[0]["id"]
    else:
        print(f"\nRecommended: Instance {best_instances[0]['id']}")
        print(f"  To create: vastai create instance {best_instances[0]['id']}")
        return None


if __name__ == "__main__":
    main()
