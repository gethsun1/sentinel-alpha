#!/bin/bash
# Wrapper to load environment and start bot
cd /root/sentinel-alpha

# Lightweight size-based log rotation to avoid disk exhaustion while
# keeping audit history. Threshold: 50MB; retention: 5 rotated copies.
rotate_if_big() {
  local file="$1"
  local max_mb="${2:-50}"
  local keep="${3:-5}"
  [ -f "$file" ] || return 0

  local bytes
  bytes=$(stat -c%s "$file" 2>/dev/null || echo 0)
  local limit=$((max_mb * 1024 * 1024))

  if [ "$bytes" -gt "$limit" ]; then
    # shift older rotations
    local i
    for i in $(seq "$keep" -1 1); do
      if [ -f "${file}.${i}" ]; then
        mv "${file}.${i}" "${file}.$((i+1))"
      fi
    done
    mv "$file" "${file}.1"
    touch "$file"
    echo "Rotated $file (was $bytes bytes)"
  fi
}

# Rotate high-volume logs before starting
rotate_if_big "logs/combined_bots.log"
rotate_if_big "logs/live_trades.jsonl"
rotate_if_big "logs/live_signals.jsonl"
rotate_if_big "logs/performance.jsonl"
rotate_if_big "logs/ai_logs_submitted.jsonl"
rotate_if_big "logs/dashboard_systemd.log"

set -a
source .env
set +a

echo "Starting Sentinel Alpha with preserved audit logs..."
exec /root/sentinel-alpha/venv/bin/python3 live_trading_bot.py --skip-prompt
