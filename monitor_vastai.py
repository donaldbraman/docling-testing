#!/usr/bin/env python3
"""Monitor vast.ai instance until running."""

import subprocess
import sys
import time

INSTANCE_ID = "27233335"
MAX_CHECKS = 60
CHECK_INTERVAL = 15  # seconds

print(f"Monitoring instance {INSTANCE_ID} until running...")
print("This typically takes 3-5 minutes for Docker image download\n")

for i in range(1, MAX_CHECKS + 1):
    try:
        result = subprocess.run(
            ["vastai", "show", "instances"], capture_output=True, text=True, check=True
        )

        # Find our instance in the output
        for line in result.stdout.split("\n"):
            if INSTANCE_ID in line:
                parts = line.split()
                if len(parts) >= 3:
                    status = parts[2]
                    uptime = parts[18] if len(parts) > 18 else "-"

                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] Check {i}/{MAX_CHECKS}: Status={status}, Uptime={uptime}")

                    if status == "running":
                        print("\n✅ Instance is RUNNING!\n")
                        print(result.stdout)
                        sys.exit(0)
                break

        if i < MAX_CHECKS:
            time.sleep(CHECK_INTERVAL)

    except Exception as e:
        print(f"Error checking status: {e}")
        sys.exit(1)

print("\n⚠️  Instance still not running after 15 minutes")
print("Current status:")
subprocess.run(["vastai", "show", "instances"])
