# Vast.ai GPU Deployment Troubleshooting Guide

**Last Updated:** 2025-10-24

A comprehensive guide to common problems and solutions when deploying GPU workloads on Vast.ai.

---

## Table of Contents

1. [Connection Issues](#1-connection-issues)
2. [Instance Problems](#2-instance-problems)
3. [CUDA/GPU Errors](#3-cudagpu-errors)
4. [Installation Failures](#4-installation-failures)
5. [Performance Issues](#5-performance-issues)
6. [Data Transfer Problems](#6-data-transfer-problems)
7. [Cost Surprises](#7-cost-surprises)
8. [Recovery Strategies](#8-recovery-strategies)
9. [GPU-Specific Issues](#9-gpu-specific-issues)
10. [When to Contact Support](#10-when-to-contact-support)

---

## 1. Connection Issues

### SSH Connection Failures

**Common Error Messages:**
```
ssh: connect to host X.X.X.X port XXXXX: Connection timed out
Permission denied (publickey)
ssh: Could not resolve hostname
```

**Diagnostic Commands:**
```bash
# Test SSH connection with verbose output
ssh -vv -p PORT -i ~/.ssh/id_rsa root@HOST

# Check if SSH key is loaded
ssh-add -l

# Test basic network connectivity
ping -c 4 HOST
nc -zv HOST PORT
```

**Solutions:**

1. **SSH Key Not Configured Properly**
   - Vast.ai uses SSH key authentication only (no password)
   - Generate RSA key if needed: `ssh-keygen -t rsa`
   - Copy public key (`~/.ssh/id_rsa.pub`) to Vast.ai Keys section
   - Ensure private key has correct permissions: `chmod 600 ~/.ssh/id_rsa`

2. **SSH Agent Not Running**
   ```bash
   eval $(ssh-agent)
   ssh-add ~/.ssh/id_rsa
   ```

3. **Network/Firewall Issues**
   - Some networks block custom SSH ports
   - Try from different network or use VPN
   - Check if port 22 or custom ports are blocked on your network

4. **Proxy Connection Slow**
   - Default SSH uses proxy (slow for large transfers)
   - Enable "Direct SSH" option when creating instance for better performance

**Prevention:**
- Test SSH connection immediately after instance creation
- Keep backup of SSH private key in secure location
- Use consistent SSH configuration across machines

---

## 2. Instance Problems

### Instance Won't Start

**Common Error Messages:**
```
Instance stuck in "scheduling" state
Failed to create task for container
Credit balance insufficient
Spend rate limit exceeded
```

**Diagnostic Commands:**
```bash
# Check instance status
vastai show instances

# Check account balance
vastai show user

# View instance logs (if accessible)
vastai ssh-url INSTANCE_ID
```

**Solutions:**

1. **Credit Balance Issues**
   - Check balance in Vast.ai console
   - Add credits before instance starts
   - Instances stop automatically when balance hits zero

2. **Spend Rate Limits**
   - New accounts have very low spending limits
   - **Verify your email** (increases limit significantly)
   - Wait a few hours for limit to increase over time
   - Try cheaper instance until limit increases

3. **GPU Scheduling Failed**
   - When you stop an instance, GPUs may be reassigned
   - Restarting tries to reclaim same GPUs
   - If unavailable, instance stuck in "scheduling"
   - **Solution:** Destroy and create new instance

4. **Docker/Template Configuration Problems**
   - Some templates fail with certain Launch Modes
   - Try switching between:
     - "Run a jupyter-python notebook"
     - "SSH: use docker SSH daemon"
     - "Docker Run: use docker ENTRYPOINT"
   - Check template compatibility with GPU model

**Prevention:**
- Maintain sufficient credit balance
- Verify email immediately for higher spend limits
- Destroy instances when done (don't just stop them)
- Test template on cheaper instance first

### Instance Crashes or Unexpected Termination

**Common Causes:**
- Out of memory (OOM) errors
- Interruptible instance preempted by higher bid
- Host machine failure
- Storage full

**Diagnostic Commands:**
```bash
# Check system logs
dmesg | tail -50

# Check disk usage
df -h

# Check memory usage
free -h

# Check GPU status
nvidia-smi

# View Docker logs (if using containers)
docker logs CONTAINER_NAME
```

**Solutions:**

1. **Interruptible Instance Preempted**
   - Switch to on-demand instance for guaranteed uptime
   - Implement checkpoint saving (see Recovery Strategies)
   - Monitor instance status frequently

2. **Storage Full**
   - Choose adequate storage allocation when creating instance
   - **Note:** Cannot resize disk after creation
   - Monitor disk usage: `df -h`
   - Clean up unnecessary files regularly

3. **Host Machine Failure**
   - Contact Vast.ai support for refund
   - File issue with specific instance ID
   - Keep backups of critical data

**Prevention:**
- Use on-demand instances for critical workloads
- Allocate generous storage (you can't resize later)
- Implement automatic checkpointing
- Use startup script (`/root/onstart.sh`) for auto-recovery

---

## 3. CUDA/GPU Errors

### Driver Version Mismatch

**Common Error Messages:**
```
CUDA driver version is insufficient for CUDA runtime version
NVML: Driver/library version mismatch
RuntimeError: CUDA error: no kernel image is available for execution
cudaGetDeviceCount() failed. Status: CUDA driver version is insufficient
```

**Diagnostic Commands:**
```bash
# Check CUDA version
nvcc --version

# Check driver version
nvidia-smi

# Check PyTorch CUDA version
python -c "import torch; print(torch.version.cuda)"

# Check if GPU is detected
python -c "import torch; print(torch.cuda.is_available())"
```

**Solutions:**

1. **Driver/Library Version Mismatch**
   ```bash
   # Unload and reload NVIDIA modules
   sudo rmmod nvidia_drm
   sudo rmmod nvidia_modeset
   sudo rmmod nvidia_uvm
   sudo rmmod nvidia

   # Reboot often fixes the issue
   sudo reboot
   ```

2. **CUDA Toolkit Version Incompatible**
   - Check compatibility: [CUDA Compatibility Matrix](https://docs.nvidia.com/deploy/cuda-compatibility/)
   - Install matching CUDA toolkit version
   - Use Docker image with compatible CUDA version
   - Example: PyTorch 2.0 requires CUDA 11.7 or 11.8

3. **GPU Not Detected**
   ```bash
   # Verify GPU is visible to system
   lspci | grep -i nvidia

   # Check CUDA device count
   python -c "import torch; print(torch.cuda.device_count())"
   ```

**Prevention:**
- Use Docker images with matching CUDA/driver versions
- Check template CUDA version before deployment
- Verify GPU model supports required CUDA version
- Test with `nvidia-smi` immediately after connecting

### CUDA Memory Errors

**Common Error Messages:**
```
RuntimeError: CUDA out of memory
CUDA error: out of memory
```

**Diagnostic Commands:**
```bash
# Monitor GPU memory usage
nvidia-smi --query-gpu=memory.used,memory.total --format=csv -l 1

# Check memory fragmentation
nvidia-smi --query-compute-apps=pid,used_memory --format=csv

# Kill processes using GPU
fuser -v /dev/nvidia*
```

**Solutions:**

1. **Reduce Memory Usage**
   - Decrease batch size
   - Lower image resolution
   - Enable gradient checkpointing
   - Use mixed precision training (FP16/BF16)

2. **Clear GPU Cache**
   ```python
   import torch
   torch.cuda.empty_cache()
   ```

3. **Memory Fragmentation**
   - Restart Python kernel
   - Restart instance if persistent
   - Use CUDA allocator tuning (see PyTorch docs)

**Prevention:**
- Start with small batch size and increase gradually
- Monitor GPU memory throughout training
- Use GPUs with adequate VRAM for your model
- Check memory requirements before renting

---

## 4. Installation Failures

### Package Installation Errors

**Common Error Messages:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages
Could not find a version that satisfies the requirement
Package conflicts
ERROR: No matching distribution found
```

**Diagnostic Commands:**
```bash
# Check Python version
python --version

# Check pip version
pip --version

# List installed packages
pip list

# Check for dependency conflicts
pip check
```

**Solutions:**

1. **PyTorch Dependency Conflicts**
   - Install PyTorch first before other packages
   - Use official installation command from [pytorch.org](https://pytorch.org)
   - Match CUDA version with PyTorch version

   ```bash
   # Example for CUDA 11.8
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

2. **Python Version Incompatibility**
   - Check package Python requirements
   - PyTorch support varies by Python version
   - Some packages don't support Python 3.12+
   - Use `pyenv` or conda to manage Python versions

3. **Conflicting Package Versions**
   ```bash
   # Create clean virtual environment
   python -m venv venv
   source venv/bin/activate

   # Install packages one at a time
   pip install --no-cache-dir package_name
   ```

4. **Missing System Dependencies**
   ```bash
   # Update system packages
   apt-get update
   apt-get install -y build-essential
   ```

**Prevention:**
- Use Docker images with pre-installed dependencies
- Create requirements.txt with pinned versions
- Test installation on cheap instance first
- Use virtual environments

### Docker Build Failures

**Common Error Messages:**
```
Permission denied while building image
failed to create task for container
Docker daemon not accessible
```

**Diagnostic Commands:**
```bash
# Check Docker is running
docker ps

# Check user permissions
groups

# Test Docker access
docker run hello-world

# View Docker logs
docker logs CONTAINER_ID
```

**Solutions:**

1. **Permission Denied**
   ```bash
   # Add user to docker group
   sudo usermod -aG docker $USER

   # Reload group membership
   newgrp docker

   # Verify docker socket permissions
   ls -l /var/run/docker.sock
   ```

2. **Docker in Docker Not Supported**
   - Vast.ai does not support Docker-in-Docker for security
   - Use pre-built images instead
   - Build images locally and push to registry

**Prevention:**
- Use official Docker images when possible
- Test Dockerfiles locally before deployment
- Check Vast.ai template compatibility

---

## 5. Performance Issues

### Low GPU Utilization

**Common Symptoms:**
- Training slower than expected
- GPU utilization <50% in nvidia-smi
- CPU bottleneck

**Diagnostic Commands:**
```bash
# Monitor GPU utilization
nvidia-smi dmon -s u

# Check GPU compute processes
nvidia-smi pmon

# Monitor CPU usage
htop

# Check I/O wait
iostat -x 1
```

**Solutions:**

1. **CPU Bottleneck (Data Loading)**
   ```python
   # Increase DataLoader workers
   train_loader = DataLoader(
       dataset,
       batch_size=32,
       num_workers=8,  # Increase this
       pin_memory=True
   )
   ```

2. **I/O Bottleneck**
   - Pre-load data to local SSD
   - Use faster storage tier
   - Cache preprocessed data

3. **Small Batch Size**
   - Increase batch size to saturate GPU
   - Use gradient accumulation if memory limited

4. **Memory Bandwidth Limited**
   - Use mixed precision training
   - Enable tensor cores (for compatible GPUs)

**Prevention:**
- Benchmark performance on different GPU models
- Profile code to identify bottlenecks
- Choose GPU with adequate memory bandwidth

### Out of Memory (OOM) Despite Low Utilization

**Why This Happens:**
- High memory utilization (approaching 100%) leads to OOM
- Memory fragmentation causes insufficient contiguous memory
- Multiple processes sharing GPU memory

**Diagnostic Commands:**
```bash
# Check all GPU processes
nvidia-smi

# Monitor memory fragmentation
nvidia-smi --query-gpu=memory.free,memory.used --format=csv -l 1

# Find processes using GPU
fuser -v /dev/nvidia*
```

**Solutions:**

1. **Memory Fragmentation**
   - Restart Python kernel
   - Restart instance
   - Use PyTorch allocator tuning:
   ```bash
   export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
   ```

2. **Reduce Peak Memory**
   - Enable gradient checkpointing
   - Use 8-bit optimizers (bitsandbytes)
   - Reduce model size with quantization

3. **For Large Models (vLLM, etc.)**
   ```python
   # Reduce gpu_memory_utilization
   from vllm import LLM

   llm = LLM(
       model="model_name",
       gpu_memory_utilization=0.85,  # Lower from 0.90
       max_num_seqs=128  # Reduce if OOM persists
   )
   ```

**Prevention:**
- Monitor memory throughout training
- Start with conservative batch sizes
- Use GPUs with more VRAM if needed

---

## 6. Data Transfer Problems

### rsync Failures

**Common Error Messages:**
```
rsync: connection unexpectedly closed
rsync error: error in rsync protocol data stream
Corrupt packet error
rsync hanging indefinitely
```

**Diagnostic Commands:**
```bash
# Test rsync with verbose output
rsync -avz --progress -e "ssh -p PORT" file.txt root@HOST:/workspace/

# Check network connectivity
ping -c 10 HOST

# Monitor transfer speed
iftop
```

**Solutions:**

1. **Slow Transfer via Proxy**
   - Default SSH uses proxy (slow for large files)
   - Enable "Direct SSH" when creating instance
   - Expected: 10-100x faster for large transfers

2. **Transfer Speed Degradation**
   - Remove `-z` compression on fast networks
   - Compression overhead exceeds transfer time
   ```bash
   rsync -av --no-compress -e "ssh -p PORT" file.txt root@HOST:/workspace/
   ```

3. **Large File Transfers**
   - Use `--partial` for resumable transfers
   - Use `--whole-file` to skip delta algorithm
   ```bash
   rsync -avW --partial --progress -e "ssh -p PORT" file.txt root@HOST:/workspace/
   ```

4. **Corrupt Packet Errors**
   - Often caused by destination disk full
   - Check available space: `df -h`
   - Usually fixed by restarting the same command

5. **Hanging Transfers**
   - Add timeout options:
   ```bash
   rsync -av --timeout=300 --contimeout=60 -e "ssh -p PORT" file.txt root@HOST:/workspace/
   ```

**Prevention:**
- Use Direct SSH for large transfers
- Monitor destination disk space
- Use `--partial` for all large transfers
- Test transfer with small file first

### Bandwidth Throttling

**Symptoms:**
- Slower than expected transfer speeds
- Inconsistent transfer rates
- High bandwidth costs

**Diagnostic Commands:**
```bash
# Test bandwidth
iperf3 -c HOST -p PORT

# Monitor real-time bandwidth
nload
```

**Solutions:**

1. **Bandwidth Charges**
   - You are charged for every byte sent/received
   - Consider bandwidth costs in budget
   - Use compression for text files (but not for fast networks)

2. **Optimize Transfers**
   - Transfer only necessary files
   - Compress before transfer (for slow networks)
   - Use incremental backups

**Prevention:**
- Factor bandwidth costs into budget
- Use cloud storage for large datasets (S3, GCS)
- Download datasets once, save to instance storage

---

## 7. Cost Surprises

### Unexpected Charges

**Common Sources:**

1. **Storage Costs on Stopped Instances**
   - **CRITICAL:** Stopped instances still incur storage charges
   - Storage charged per second, even when instance offline
   - **Solution:** Destroy instances when done (not just stop)

2. **Bandwidth Overage**
   - Charged for every byte sent/received
   - Applies regardless of instance state
   - Can be significant for large dataset transfers

3. **Forgotten Instances**
   - Instances never free, even with zero balance
   - Automatic charging continues indefinitely
   - Check all instances regularly

**Diagnostic Commands:**
```bash
# List all instances (including stopped)
vastai show instances

# Check current balance and charges
vastai show user

# Destroy instance (stops all charges)
vastai destroy instance INSTANCE_ID
```

**Prevention Strategies:**

1. **Always Destroy When Done**
   ```bash
   # Stop instance (still charges storage)
   vastai stop instance INSTANCE_ID

   # Destroy instance (stops ALL charges)
   vastai destroy instance INSTANCE_ID
   ```

2. **Set Spending Alerts**
   - Monitor balance regularly
   - Set up notifications (if available)

3. **Calculate Total Costs**
   - GPU cost per hour
   - Storage cost per hour (applies when stopped too)
   - Bandwidth estimate
   - Buffer for unexpected time

4. **Use On-Demand for Predictable Costs**
   - Interruptible instances can extend time unexpectedly
   - On-demand has guaranteed uptime

**Cost Optimization:**
- Destroy instances immediately when done
- Use interruptible for non-critical workloads
- Transfer data during off-peak times
- Allocate only needed storage

---

## 8. Recovery Strategies

### Checkpoint and Recovery Best Practices

**Critical for Interruptible Instances:**
- Instances can be stopped when higher bid placed
- Host machine failures can occur
- Must save work periodically

**Implementation:**

1. **Implement Periodic Checkpointing**
   ```python
   # PyTorch example
   checkpoint = {
       'epoch': epoch,
       'model_state_dict': model.state_dict(),
       'optimizer_state_dict': optimizer.state_dict(),
       'loss': loss,
   }
   torch.save(checkpoint, f'checkpoint_epoch_{epoch}.pth')
   ```

2. **Save to Cloud Storage**
   ```bash
   # After each checkpoint
   aws s3 sync /workspace/checkpoints/ s3://bucket/checkpoints/

   # Or use rclone
   rclone sync /workspace/checkpoints/ remote:checkpoints/
   ```

3. **Checkpoint Frequency**
   - End of each epoch (minimum)
   - Every N steps for long epochs
   - Before any risky operation

4. **Use Startup Scripts**
   ```bash
   # Create /root/onstart.sh
   #!/bin/bash

   # Restore from cloud storage
   aws s3 sync s3://bucket/checkpoints/ /workspace/checkpoints/

   # Resume training
   cd /workspace
   python train.py --resume-from-checkpoint checkpoints/latest.pth
   ```

   Make executable: `chmod +x /root/onstart.sh`

5. **Validation and Checkpoint Intervals**
   ```python
   # Example: Save every 1000 steps
   if global_step % 1000 == 0:
       save_checkpoint(f'step_{global_step}.pth')
   ```

**Recovery Procedure:**

1. **When Instance Fails:**
   ```bash
   # Create new instance
   vastai create instance OFFER_ID

   # Restore checkpoints from cloud
   aws s3 sync s3://bucket/checkpoints/ /workspace/checkpoints/

   # Resume training
   python train.py --resume
   ```

2. **Verify Checkpoint Integrity:**
   ```python
   # Load and validate checkpoint
   checkpoint = torch.load('checkpoint.pth')
   assert 'model_state_dict' in checkpoint
   assert 'optimizer_state_dict' in checkpoint
   print(f"Checkpoint from epoch {checkpoint['epoch']}")
   ```

**Prevention:**
- Always implement checkpointing before starting
- Test recovery procedure on cheap instance
- Store critical data in cloud storage
- Document resume commands in README

---

## 9. GPU-Specific Issues

### RTX 4090 Problems

**Known Issues:**
- CUDA SDK Toolkit detection errors
- Kernel build failures with hashcat
- Thermal issues in multi-GPU setups
- Driver crashes when idle

**Solutions:**
- Use latest CUDA drivers
- Test with single GPU first
- Monitor temperatures: `nvidia-smi dmon -s t`
- Report hardware issues to Vast.ai support

**Alternatives:**
- RTX 3090 (more stable, proven track record)
- A100 (enterprise-grade reliability)

### RTX 3090 vs A100

**RTX 3090:**
- Good for: Single-GPU training, inference
- NVLink support (48GB with 2x GPUs)
- Lower cost
- Consumer-grade reliability

**A100:**
- Good for: Large-scale training, multi-GPU
- High bandwidth memory
- Enterprise reliability
- Higher cost but better scaling

**Recommendation:**
- RTX 3090: Development, small models, inference
- A100: Production training, large models, critical workloads

---

## 10. When to Contact Support

### Self-Solve First (Check Docs/Discord)

**Good Candidates for Self-Solving:**
- SSH configuration issues
- Common CUDA errors
- Package installation conflicts
- Instance scheduling problems
- General setup questions

**Resources:**
- Official docs: [docs.vast.ai](https://docs.vast.ai)
- Discord community (active, helpful)
- GitHub issues: [github.com/vast-ai/vast-cli/issues](https://github.com/vast-ai/vast-cli/issues)

### Contact Vast.ai Support

**Contact When:**
- Account-specific issues (billing, refunds)
- Suspected fraudulent hardware listings
- Instance problems after troubleshooting
- Spend rate limit issues (after email verification)
- Need quick resolution (5-10 min response time)

**How to Contact:**
- **Chat:** Online support chat (lower right corner)
- **Email:** support@vast.ai
- **Contact form:** [vast.ai/contact](https://vast.ai/contact)

**Support Hours:**
- Limited to Pacific Time working hours
- Response time typically 5-10 minutes during business hours
- Discord community available 24/7

**What to Include:**
- Instance ID (if applicable)
- Error messages (exact text)
- Steps to reproduce
- System information (`nvidia-smi` output)
- What you've already tried

**Expected Response:**
- Support staff are knowledgeable and helpful
- Usually provide specific solutions, not generic responses
- Willing to investigate deeper issues
- Can issue refunds for hardware failures

---

## Quick Reference: Common Commands

### Instance Management
```bash
# List all instances
vastai show instances

# SSH into instance
vastai ssh-url INSTANCE_ID

# Stop instance (still charges storage)
vastai stop instance INSTANCE_ID

# Destroy instance (stops all charges)
vastai destroy instance INSTANCE_ID
```

### GPU Diagnostics
```bash
# Check GPU status
nvidia-smi

# Monitor GPU utilization
nvidia-smi dmon

# Check CUDA version
nvcc --version

# Test GPU in Python
python -c "import torch; print(torch.cuda.is_available())"
```

### System Diagnostics
```bash
# Check disk space
df -h

# Check memory
free -h

# Monitor processes
htop

# View system logs
dmesg | tail -50
```

### Data Transfer
```bash
# rsync with resume support
rsync -avW --partial --progress -e "ssh -p PORT -i ~/.ssh/id_rsa" \
  /local/path/ root@HOST:/remote/path/

# Check transfer speed
iftop
```

---

## Summary: Top 10 Issues and Quick Fixes

1. **Instance won't start** → Verify email, check balance, try cheaper instance
2. **SSH connection fails** → Check SSH key in Vast.ai dashboard, use `ssh -vv` for debugging
3. **CUDA out of memory** → Reduce batch size, enable mixed precision, use gradient checkpointing
4. **Slow data transfer** → Enable Direct SSH, remove compression flag, use `--whole-file`
5. **Unexpected charges** → Destroy instances (not stop), monitor storage costs
6. **Driver version mismatch** → Reboot instance, check CUDA compatibility
7. **PyTorch install fails** → Install PyTorch first, match CUDA version
8. **Instance crashes** → Implement checkpointing, use on-demand instances
9. **Low GPU utilization** → Increase DataLoader workers, increase batch size
10. **Storage full** → Allocate more storage at creation (can't resize later)

---

**Contributing:**
Found a solution not listed here? Encountered a new issue? Please contribute by:
- Opening an issue in this repo
- Submitting a PR with updates
- Sharing in Vast.ai Discord community

**Disclaimer:**
This guide is community-maintained and not officially affiliated with Vast.ai. Information may become outdated as the platform evolves. Always check official documentation for latest guidance.
