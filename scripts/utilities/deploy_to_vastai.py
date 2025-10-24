#!/usr/bin/env python3
"""
Automated deployment script for vast.ai GPU instances.

Usage:
    # OCR deployment
    uv run python scripts/utilities/deploy_to_vastai.py --mode ocr --instance-id 12345

    # Training deployment
    uv run python scripts/utilities/deploy_to_vastai.py --mode training --instance-id 12345

    # Search for suitable instances
    uv run python scripts/utilities/deploy_to_vastai.py --search ocr
    uv run python scripts/utilities/deploy_to_vastai.py --search training
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, check=True, capture_output=True):
    """Run shell command and return output."""
    print(f"Running: {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        check=check,
        capture_output=capture_output,
        text=True,
    )
    return result


def search_instances(mode: str):
    """Search for suitable vast.ai instances."""
    print(f"\n{'=' * 80}")
    print(f"SEARCHING FOR {mode.upper()} INSTANCES")
    print(f"{'=' * 80}\n")

    if mode == "ocr":
        query = "reliability > 0.95 cuda_vers >= 12.0 gpu_ram >= 16 num_gpus=1"
    elif mode == "training":
        query = "reliability > 0.95 cuda_vers >= 12.4 gpu_name ~ A100|RTX_4090|RTX_3090|H100"
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)

    cmd = f"vastai search offers '{query}' -o 'dph+'"
    result = run_command(cmd, check=False)

    if result.returncode == 0:
        print("\n" + result.stdout)
        print("\nUse --instance-id <ID> to deploy to selected instance")
    else:
        print(f"Error searching instances: {result.stderr}")
        sys.exit(1)


def get_instance_info(instance_id: int):
    """Get SSH connection info for instance."""
    print(f"\nGetting connection info for instance {instance_id}...")

    # Get SSH URL
    result = run_command(f"vastai ssh-url {instance_id}", check=False)
    if result.returncode != 0:
        print(f"Error: Instance {instance_id} not found or not running")
        print(result.stderr)
        sys.exit(1)

    # Parse SSH connection details from output
    # Format: ssh -p PORT root@IP -L 8080:localhost:8080
    ssh_cmd = result.stdout.strip()
    print(f"SSH command: {ssh_cmd}")

    # Extract port and IP
    parts = ssh_cmd.split()
    port_idx = parts.index("-p")
    port = parts[port_idx + 1]
    host = parts[port_idx + 2].split("@")[1]

    return {"port": port, "host": host, "ssh_cmd": ssh_cmd}


def deploy_code(instance_info: dict, mode: str):
    """Deploy code to vast.ai instance."""
    print(f"\n{'=' * 80}")
    print("DEPLOYING CODE")
    print(f"{'=' * 80}\n")

    port = instance_info["port"]
    host = instance_info["host"]

    # Get project root
    project_root = Path(__file__).parent.parent.parent

    # Build rsync command
    exclude_patterns = [
        ".venv",
        "__pycache__",
        "*.pyc",
        ".git",
        "archive*",
        "results/",
        "models/*/pytorch_model.bin",
        "*.tar.gz",
    ]

    if mode == "ocr":
        # For OCR, we need the PDF data
        exclude_patterns.extend(
            [
                "models/",  # Don't need trained models for OCR
            ]
        )
    elif mode == "training":
        # For training, we need the corpus but not raw PDFs
        exclude_patterns.extend(
            [
                "data/v3_data/raw_pdf/",  # Don't need raw PDFs for training
            ]
        )

    exclude_flags = " ".join([f"--exclude='{pattern}'" for pattern in exclude_patterns])

    rsync_cmd = (
        f"rsync -avz -e 'ssh -p {port}' {exclude_flags} "
        f"{project_root}/ root@{host}:/workspace/docling-testing/"
    )

    result = run_command(rsync_cmd, check=False)
    if result.returncode != 0:
        print(f"Error deploying code: {result.stderr}")
        sys.exit(1)

    print("\nCode deployed successfully!")


def setup_environment(instance_info: dict, mode: str):
    """Setup Python environment on instance."""
    print(f"\n{'=' * 80}")
    print("SETTING UP ENVIRONMENT")
    print(f"{'=' * 80}\n")

    port = instance_info["port"]
    host = instance_info["host"]

    setup_commands = [
        # Install uv
        "curl -LsSf https://astral.sh/uv/install.sh | sh",
        "source $HOME/.cargo/env",
        # Install dependencies
        "cd /workspace/docling-testing && $HOME/.cargo/bin/uv sync",
        # Verify PyTorch CUDA
        "cd /workspace/docling-testing && $HOME/.cargo/bin/uv run python -c \"import torch; print(f'CUDA available: {torch.cuda.is_available()}')\"",
    ]

    if mode == "training":
        # Install Flash Attention 2 for training
        setup_commands.extend(
            [
                # Install ninja for faster compilation
                "apt-get update && apt-get install -y ninja-build",
                # Install Flash Attention 2
                "cd /workspace/docling-testing && $HOME/.cargo/bin/uv pip install flash-attn --no-build-isolation",
                # Verify Flash Attention
                "cd /workspace/docling-testing && $HOME/.cargo/bin/uv run python -c \"import flash_attn; print(f'Flash Attention: {flash_attn.__version__}')\"",
            ]
        )

    if mode == "ocr":
        # Install additional OCR dependencies
        setup_commands.extend(
            [
                # Install poppler for pdf2image
                "apt-get update && apt-get install -y poppler-utils",
                # Verify EasyOCR
                "cd /workspace/docling-testing && $HOME/.cargo/bin/uv run python -c \"import easyocr; print('EasyOCR installed')\"",
            ]
        )

    # Combine commands into single SSH call
    remote_cmd = " && ".join(setup_commands)
    ssh_cmd = f"ssh -p {port} root@{host} '{remote_cmd}'"

    print("Installing dependencies (this may take 5-10 minutes)...")
    result = run_command(ssh_cmd, check=False, capture_output=False)

    if result.returncode != 0:
        print("\nWarning: Some setup commands failed. Check output above.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != "y":
            sys.exit(1)

    print("\nEnvironment setup complete!")


def create_deployment_script(instance_info: dict, mode: str):
    """Create helper script for running jobs on instance."""
    print(f"\n{'=' * 80}")
    print("CREATING DEPLOYMENT HELPER SCRIPT")
    print(f"{'=' * 80}\n")

    port = instance_info["port"]
    host = instance_info["host"]

    if mode == "ocr":
        script_content = f"""#!/bin/bash
# OCR Pipeline Deployment Helper
# Generated by deploy_to_vastai.py

SSH_PORT={port}
SSH_HOST={host}

echo "=== OCR Pipeline Helper ==="
echo ""
echo "1. SSH into instance:"
echo "   ssh -p $SSH_PORT root@$SSH_HOST"
echo ""
echo "2. Run single PDF:"
echo '   ssh -p $SSH_PORT root@$SSH_HOST "cd /workspace/docling-testing && screen -S ocr -dm bash -c \\'uv run python scripts/corpus_building/extract_with_easyocr.py --pdf FILENAME --dpi 300\\'"'
echo ""
echo "3. Run batch processing:"
echo '   ssh -p $SSH_PORT root@$SSH_HOST "cd /workspace/docling-testing && screen -S ocr_batch -dm bash -c \\'for pdf in data/v3_data/raw_pdf/*.pdf; do uv run python scripts/corpus_building/extract_with_easyocr.py --pdf \\$(basename \\$pdf .pdf) --dpi 300; done\\'"'
echo ""
echo "4. Monitor progress:"
echo "   ssh -p $SSH_PORT root@$SSH_HOST 'screen -r ocr'"
echo "   ssh -p $SSH_PORT root@$SSH_HOST 'watch -n 1 nvidia-smi'"
echo ""
echo "5. Download results:"
echo "   rsync -avz -e 'ssh -p $SSH_PORT' root@$SSH_HOST:/workspace/docling-testing/results/ ./results_vastai/"
echo ""
"""
    else:  # training
        script_content = f"""#!/bin/bash
# ModernBERT Training Deployment Helper
# Generated by deploy_to_vastai.py

SSH_PORT={port}
SSH_HOST={host}

echo "=== ModernBERT Training Helper ==="
echo ""
echo "1. SSH into instance:"
echo "   ssh -p $SSH_PORT root@$SSH_HOST -L 6006:localhost:6006"
echo ""
echo "2. Start training:"
echo '   ssh -p $SSH_PORT root@$SSH_HOST "cd /workspace/docling-testing && screen -S training -dm bash -c \\'uv run python scripts/training/train_modernbert_classifier.py --output-dir /workspace/models/modernbert-v3\\'"'
echo ""
echo "3. Start TensorBoard:"
echo '   ssh -p $SSH_PORT root@$SSH_HOST "cd /workspace/docling-testing && screen -S tensorboard -dm bash -c \\'tensorboard --logdir /workspace/logs --port 6006 --bind_all\\'"'
echo "   Open: http://localhost:6006"
echo ""
echo "4. Monitor progress:"
echo "   ssh -p $SSH_PORT root@$SSH_HOST 'screen -r training'"
echo "   ssh -p $SSH_PORT root@$SSH_HOST 'tail -f /workspace/docling-testing/nohup.out'"
echo "   ssh -p $SSH_PORT root@$SSH_HOST 'watch -n 1 nvidia-smi'"
echo ""
echo "5. Download checkpoints (run periodically):"
echo "   rsync -avz -e 'ssh -p $SSH_PORT' root@$SSH_HOST:/workspace/models/modernbert-v3/checkpoint-* ./models_vastai/"
echo ""
echo "6. Download final model:"
echo "   rsync -avz -e 'ssh -p $SSH_PORT' root@$SSH_HOST:/workspace/models/modernbert-v3/ ./models_vastai/modernbert-v3/"
echo ""
"""

    # Write script to local file
    script_path = Path(f"vastai_{mode}_helper.sh")
    script_path.write_text(script_content)
    script_path.chmod(0o755)

    print(f"Helper script created: {script_path}")
    print(f"\nRun: ./{script_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy to vast.ai GPU instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for OCR instances
  python deploy_to_vastai.py --search ocr

  # Search for training instances
  python deploy_to_vastai.py --search training

  # Deploy OCR pipeline
  python deploy_to_vastai.py --mode ocr --instance-id 12345

  # Deploy training pipeline
  python deploy_to_vastai.py --mode training --instance-id 12345
        """,
    )

    parser.add_argument(
        "--search",
        choices=["ocr", "training"],
        help="Search for suitable instances",
    )

    parser.add_argument(
        "--mode",
        choices=["ocr", "training"],
        help="Deployment mode",
    )

    parser.add_argument(
        "--instance-id",
        type=int,
        help="Vast.ai instance ID to deploy to",
    )

    parser.add_argument(
        "--skip-code",
        action="store_true",
        help="Skip code deployment (useful for re-running setup)",
    )

    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip environment setup (useful for re-deploying code)",
    )

    args = parser.parse_args()

    # Handle search mode
    if args.search:
        search_instances(args.search)
        sys.exit(0)

    # Handle deployment mode
    if not args.mode or not args.instance_id:
        parser.print_help()
        print("\nError: --mode and --instance-id required for deployment")
        sys.exit(1)

    print(f"\n{'=' * 80}")
    print(f"VAST.AI DEPLOYMENT: {args.mode.upper()} MODE")
    print(f"Instance ID: {args.instance_id}")
    print(f"{'=' * 80}\n")

    # Get instance info
    instance_info = get_instance_info(args.instance_id)

    # Deploy code
    if not args.skip_code:
        deploy_code(instance_info, args.mode)
    else:
        print("Skipping code deployment")

    # Setup environment
    if not args.skip_setup:
        setup_environment(instance_info, args.mode)
    else:
        print("Skipping environment setup")

    # Create helper script
    create_deployment_script(instance_info, args.mode)

    print(f"\n{'=' * 80}")
    print("DEPLOYMENT COMPLETE!")
    print(f"{'=' * 80}\n")
    print("Next steps:")
    print(f"1. Run helper script: ./vastai_{args.mode}_helper.sh")
    print(f"2. Or SSH directly: {instance_info['ssh_cmd']}")
    print()


if __name__ == "__main__":
    main()
