#!/bin/bash
# System Resources Check Script
# Verifies sufficient RAM and swap for LLaMA-2-7B

echo "======================================================================"
echo "SYSTEM RESOURCE VERIFICATION"
echo "======================================================================"

# Check RAM
echo ""
echo "Memory (RAM):"
free -h

TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))
AVAIL_MEM_KB=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
AVAIL_MEM_GB=$((AVAIL_MEM_KB / 1024 / 1024))

echo ""
echo "Total RAM: ${TOTAL_MEM_GB}GB"
echo "Available RAM: ${AVAIL_MEM_GB}GB"

if [ $AVAIL_MEM_GB -lt 4 ]; then
    echo "⚠️  WARNING: Less than 4GB available RAM"
    echo "   LLaMA-2-7B 4-bit needs ~4-6GB RAM"
    echo "   Consider closing other applications"
else
    echo "✅ Sufficient RAM available"
fi

# Check Swap
echo ""
echo "Swap Space:"
swapon --show

TOTAL_SWAP_KB=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
TOTAL_SWAP_GB=$((TOTAL_SWAP_KB / 1024 / 1024))

echo ""
echo "Total Swap: ${TOTAL_SWAP_GB}GB"

if [ $TOTAL_SWAP_GB -lt 4 ]; then
    echo "⚠️  WARNING: Less than 4GB swap configured"
    echo "   Recommended: 8GB+ swap for safety"
    echo "   To add swap:"
    echo "     sudo fallocate -l 8G /swapfile"
    echo "     sudo chmod 600 /swapfile"
    echo "     sudo mkswap /swapfile"
    echo "     sudo swapon /swapfile"
else
    echo "✅ Adequate swap space configured"
fi

# Check CPU
echo ""
echo "CPU Information:"
CPU_CORES=$(nproc)
CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)

echo "CPU: $CPU_MODEL"
echo "Cores: $CPU_CORES"
echo ""
echo "Note: LLaMA inference configured to use 4 threads"

# Check disk space
echo ""
echo "Disk Space:"
df -h /root/sentinel-alpha

DISK_AVAIL=$(df /root/sentinel-alpha | tail -1 | awk '{print $4}')
echo ""
echo "Available for logs: $DISK_AVAIL"

# Summary
echo ""
echo "======================================================================"
echo "RESOURCE SUMMARY"
echo "======================================================================"

PASS_COUNT=0
WARN_COUNT=0

if [ $AVAIL_MEM_GB -ge 4 ]; then
    echo "✅ RAM: ${AVAIL_MEM_GB}GB available"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "⚠️  RAM: ${AVAIL_MEM_GB}GB available (need 4GB+)"
    WARN_COUNT=$((WARN_COUNT + 1))
fi

if [ $TOTAL_SWAP_GB -ge 4 ]; then
    echo "✅ Swap: ${TOTAL_SWAP_GB}GB configured"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "⚠️  Swap: ${TOTAL_SWAP_GB}GB configured (recommend 8GB+)"
    WARN_COUNT=$((WARN_COUNT + 1))
fi

echo "✅ CPU: $CPU_CORES cores available"
PASS_COUNT=$((PASS_COUNT + 1))

echo ""
if [ $WARN_COUNT -eq 0 ]; then
    echo "🎉 System resources: READY"
    exit 0
else
    echo "⚠️  System resources: ${WARN_COUNT} warnings"
    echo "   Bot may still work, monitor performance closely"
    exit 0
fi
