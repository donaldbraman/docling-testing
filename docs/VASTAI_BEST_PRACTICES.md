# Vast.ai Best Practices & Troubleshooting Guide

**Complete guide based on official docs and community solutions (2025)**

## Table of Contents
1. [SCP/File Transfer Issues](#scpfile-transfer-issues)
2. [Instance Status Problems](#instance-status-problems)
3. [Best Practices](#best-practices)
4. [Automation Tips](#automation-tips)

---

## SCP/File Transfer Issues

### Problem: "Connection Closed" with SCP

**Root Cause:** Vast.ai displays ASCII art/welcome messages that interfere with SCP protocol.

**Solutions (in order of preference):**

#### 1. Use Correct SCP Syntax ⭐ FIRST TRY
```bash
# CORRECT: Capital -P for port
scp -P 12345 myfile.txt root@ssh8.vast.ai:/workspace/

# WRONG: Lowercase -p (this is for ssh, not scp)
scp -p 12345 myfile.txt root@ssh8.vast.ai:/workspace/
```

#### 2. Use Legacy SCP Protocol (OpenSSH 8.8+)
```bash
# Add -O flag to use old SCP protocol instead of SFTP
scp -O -P 12345 myfile.txt root@ssh8.vast.ai:/workspace/
```

Since OpenSSH 8.8, scp uses SFTP protocol by default which can fail with vast.ai's welcome messages.

#### 3. Use rsync (RECOMMENDED for automation)
```bash
# rsync is more robust and resumable
rsync -avz --partial -e "ssh -i ~/.ssh/id_ed25519 -p 12345" \
  myfile.txt root@ssh8.vast.ai:/workspace/

# Benefits:
# - Resumable with --partial flag
# - Better error handling
# - Works with vast.ai welcome messages
# - Shows progress
```

#### 4. Use SSH Pipe (for single files)
```bash
# Upload via stdin/stdout (bypasses SCP entirely)
cat myfile.txt | ssh -i ~/.ssh/id_ed25519 -p 12345 root@ssh8.vast.ai \
  "cat > /workspace/myfile.txt"

# Upload directory as tar
tar czf - mydir/ | ssh -i ~/.ssh/id_ed25519 -p 12345 root@ssh8.vast.ai \
  "tar xzf - -C /workspace/"
```

#### 5. Use Vast.ai CLI (built-in)
```bash
# Uses rsync internally
vastai copy 12345678 myfile.txt /workspace/myfile.txt
```

### Critical Warning: Destination Paths

**❌ NEVER copy to these destinations:**
```bash
# These BREAK SSH permissions!
scp file.txt root@host:/root/     # BAD
scp file.txt root@host:/          # BAD
```

**✅ ALWAYS use these safe destinations:**
```bash
scp file.txt root@host:/workspace/      # GOOD
scp file.txt root@host:/workspace/data/ # GOOD
scp file.txt root@host:/tmp/            # GOOD
```

Copying to `/root` or `/` can mess up SSH folder permissions, breaking future operations.

---

## Instance Status Problems

### Problem: Instance Stuck in "created" Status

**Possible Causes:**
1. **Provider infrastructure issues** - Host machine problems
2. **Docker image pull timeout** - Large images take time
3. **Resource conflicts** - GPU/memory allocation issues
4. **Account limits** - Unverified accounts have strict limits

**Solutions:**

#### 1. Check Account Verification
```bash
# Verify your email first!
# Unverified accounts have VERY small resource limits
```
Log into vast.ai console → Settings → Verify Email

#### 2. Wait Longer for Large Images
```bash
# Our body-extractor image is ~4GB
# Can take 5-10 minutes to pull on first launch
# Check instance age vs uptime:
vastai show instances

# If age > 10 min and uptime is still blank, there's a problem
```

#### 3. Destroy and Recreate
```bash
# Don't wait forever - recreate if stuck > 10 min
vastai destroy instance <ID>

# Try different provider/machine
vastai search offers '<your_criteria>' --order 'reliability-'
```

#### 4. Choose More Reliable Providers
```bash
# Sort by reliability (100% = best)
vastai search offers 'reliability > 0.99 ...' --order 'reliability-'

# Our experience:
# - Provider 37257 (China): Stuck instances, avoid
# - Provider 78246 (Poland): 100% reliability, works great
# - Provider 59017 (Texas): 100% reliability, more expensive
```

### Problem: Instance Stuck in "scheduling" Status

**Cause:** Instance is trying to reclaim the same GPU(s) from a previous session, but they're busy.

**Solutions:**
1. **Wait** - Usually resolves in <30 seconds if GPU becomes available
2. **Destroy and create new** - Don't restart stopped instances unless you're willing to wait
3. **Use on-demand pricing** - Higher priority than spot instances

**Best Practice:** Don't stop instances unless you're OK waiting for restart. Destroy when done.

---

## Best Practices

### File Transfers

#### For Small Files (<100MB)
```bash
# SCP with legacy protocol
scp -O -P <port> file.txt root@host:/workspace/
```

#### For Medium Files (100MB-1GB)
```bash
# rsync with compression and resume
rsync -avz --partial --progress \
  -e "ssh -i ~/.ssh/id_ed25519 -p <port>" \
  file.dat root@host:/workspace/
```

#### For Large Files/Datasets (>1GB)
```bash
# Method 1: Cloud storage (FASTEST)
# Upload to S3/GCS/gdrive first, then:
ssh -p <port> root@host "aws s3 cp s3://bucket/data.tar.gz /workspace/"

# Method 2: rsync with compression
rsync -avz --partial --progress --bwlimit=10000 \
  -e "ssh -p <port>" \
  largefile.tar.gz root@host:/workspace/

# Method 3: Split and transfer
split -b 500M largefile.tar.gz part_
for part in part_*; do
  rsync -avz --partial -e "ssh -p <port>" \
    $part root@host:/workspace/
done
```

### Instance Management

#### Creating Instances
```bash
# Always specify disk size explicitly
vastai create instance <offer_id> \
  --image yourimage:latest \
  --disk 100  # GB allocated

# Monitor creation
watch -n 5 'vastai show instances'
```

#### Stopping vs Destroying
```bash
# Stop: Keeps data, tries to reclaim same GPU (may get stuck)
vastai stop instance <ID>

# Destroy: Deletes everything, stops billing immediately
vastai destroy instance <ID>  # RECOMMENDED when done
```

#### Monitoring Costs
```bash
# Check current hourly rate
vastai show instances | grep '$/hr'

# Always destroy when done to stop charges!
```

### SSH Connection

#### Generate SSH Key
```bash
# Create key for vast.ai
ssh-keygen -t ed25519 -f ~/.ssh/vastai_key -C "vastai-deployment"

# Add to vast.ai
vastai attach ssh <instance_id> ~/.ssh/vastai_key.pub
```

#### SSH Config for Easy Access
```bash
# Add to ~/.ssh/config
Host vastai-*
    User root
    IdentityFile ~/.ssh/vastai_key
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    ServerAliveInterval 60
    ServerAliveCountMax 3

# Then connect with:
ssh -p <port> vastai-instance@ssh8.vast.ai
```

#### Keep SSH Connections Alive
```bash
# In ~/.ssh/config:
ServerAliveInterval 60
ServerAliveCountMax 3

# Or use tmux/screen on remote:
ssh -p <port> root@host "tmux new -s work"
# Detach: Ctrl+b d
# Reattach: ssh -p <port> root@host "tmux attach -t work"
```

---

## Automation Tips

### Automated File Upload Script

```bash
#!/bin/bash
# upload_to_vastai.sh - Robust file upload with retry

INSTANCE_ID=$1
LOCAL_FILE=$2
REMOTE_PATH=$3

# Get SSH info
SSH_INFO=$(vastai show instances | grep $INSTANCE_ID)
SSH_HOST=$(echo "$SSH_INFO" | awk '{print $10}')
SSH_PORT=$(echo "$SSH_INFO" | awk '{print $11}')

# Try methods in order of preference
echo "Attempting rsync..."
if rsync -avz --partial --timeout=300 \
     -e "ssh -i ~/.ssh/id_ed25519 -p $SSH_PORT -o ConnectTimeout=10" \
     "$LOCAL_FILE" root@$SSH_HOST:$REMOTE_PATH; then
    echo "✅ rsync succeeded"
    exit 0
fi

echo "rsync failed, trying legacy SCP..."
if scp -O -P $SSH_PORT -o ConnectTimeout=10 \
     "$LOCAL_FILE" root@$SSH_HOST:$REMOTE_PATH; then
    echo "✅ SCP succeeded"
    exit 0
fi

echo "SCP failed, trying SSH pipe..."
if cat "$LOCAL_FILE" | ssh -i ~/.ssh/id_ed25519 -p $SSH_PORT \
     -o ConnectTimeout=10 root@$SSH_HOST \
     "cat > $REMOTE_PATH"; then
    echo "✅ SSH pipe succeeded"
    exit 0
fi

echo "❌ All methods failed"
exit 1
```

### Wait for Instance Script

```bash
#!/bin/bash
# wait_for_vastai.sh - Wait for instance to be fully ready

INSTANCE_ID=$1
MAX_WAIT=600  # 10 minutes
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    STATUS=$(vastai show instances | grep $INSTANCE_ID | awk '{print $3}')

    if [ "$STATUS" = "running" ]; then
        echo "✅ Instance running, waiting 60s for SSH..."
        sleep 60

        # Test SSH connection
        SSH_INFO=$(vastai show instances | grep $INSTANCE_ID)
        SSH_HOST=$(echo "$SSH_INFO" | awk '{print $10}')
        SSH_PORT=$(echo "$SSH_INFO" | awk '{print $11}')

        if ssh -i ~/.ssh/id_ed25519 -p $SSH_PORT \
             -o ConnectTimeout=5 -o BatchMode=yes \
             root@$SSH_HOST "echo OK" 2>/dev/null; then
            echo "✅ SSH ready!"
            exit 0
        fi

        echo "SSH not ready, waiting..."
        sleep 30
        ELAPSED=$((ELAPSED + 30))
    elif [ "$STATUS" = "created" ] || [ "$STATUS" = "loading" ]; then
        echo "[$(date +%H:%M:%S)] Status: $STATUS (waited ${ELAPSED}s)"
        sleep 15
        ELAPSED=$((ELAPSED + 15))
    else
        echo "❌ Unexpected status: $STATUS"
        exit 1
    fi
done

echo "❌ Timeout after ${MAX_WAIT}s"
exit 1
```

### Cleanup Script

```bash
#!/bin/bash
# cleanup_vastai.sh - Destroy all instances to stop billing

echo "🔍 Finding all instances..."
INSTANCES=$(vastai show instances | tail -n +2 | awk '{print $1}')

if [ -z "$INSTANCES" ]; then
    echo "✅ No instances running"
    exit 0
fi

echo "Found instances: $INSTANCES"
echo "Destroying all instances..."

for ID in $INSTANCES; do
    echo "  Destroying $ID..."
    vastai destroy instance $ID
done

echo "✅ All instances destroyed"
```

---

## Common Errors and Fixes

### Error: "Connection closed by remote host"
**Problem:** SCP incompatibility with vast.ai welcome message
**Fix:** Use `scp -O` (legacy protocol) or rsync instead

### Error: "Permission denied"
**Problem:** SSH key not attached or wrong key
**Fix:**
```bash
vastai attach ssh <instance_id> ~/.ssh/id_ed25519.pub
```

### Error: "No space left on device"
**Problem:** Didn't allocate enough disk when creating instance
**Fix:** Destroy and recreate with `--disk 100` (or higher)

### Error: "Instance stuck in 'created' for 10+ minutes"
**Problem:** Provider infrastructure issue
**Fix:** Destroy and try different provider (sort by reliability)

### Error: "SSH works but SCP fails immediately"
**Problem:** ASCII art/welcome message breaking SCP protocol
**Fix:** Use rsync or `scp -O` flag

---

## Quick Reference

### File Upload (Choose One)
```bash
# Method 1: rsync (best for automation)
rsync -avz --partial -e "ssh -p <PORT>" file root@<HOST>:/workspace/

# Method 2: SCP with legacy protocol
scp -O -P <PORT> file root@<HOST>:/workspace/

# Method 3: SSH pipe (always works)
cat file | ssh -p <PORT> root@<HOST> "cat > /workspace/file"
```

### Instance Lifecycle
```bash
# Create
vastai create instance <ID> --image <IMAGE> --disk 100

# Monitor
watch -n 5 'vastai show instances'

# SSH
SSH_PORT=$(vastai show instances | grep <ID> | awk '{print $11}')
SSH_HOST=$(vastai show instances | grep <ID> | awk '{print $10}')
ssh -p $SSH_PORT root@$SSH_HOST

# Destroy (stops billing!)
vastai destroy instance <ID>
```

### Troubleshooting Checklist
- [ ] Email verified?
- [ ] Used capital `-P` for SCP port?
- [ ] Tried `-O` flag for legacy SCP?
- [ ] Tried rsync instead of SCP?
- [ ] Instance age > 10 min but still "created"?
- [ ] Checked provider reliability (>99%)?
- [ ] Not copying to /root or /?
- [ ] Allocated enough disk space?

---

## Links
- **Official Docs**: https://docs.vast.ai
- **CLI Reference**: https://vast.ai/docs/cli/commands
- **Support Chat**: https://cloud.vast.ai (lower right corner)
- **Status Page**: https://vast.ai/status

---

**Last Updated:** 2025-01-24
**Tested With:** vast.ai CLI 0.x, OpenSSH 8.8+, body-extractor project
