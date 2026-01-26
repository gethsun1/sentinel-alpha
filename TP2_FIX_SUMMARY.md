# TP2 Execution Issue - Fix Summary

## Problem Identified

After TP2 (40% of position) executes, the remaining runner position (30%) was left **without a Take Profit order**. Only a trailing stop loss was being placed.

### Current Situation
- **3 SHORT positions** without TP protection:
  - `cmt_ethusdt`: 0.021 @ entry (unknown, avgPrice shows 0.0000)
  - `cmt_xrpusdt`: 30.0 @ entry 1.9316
  - `cmt_bnbusdt`: 0.1 @ entry 886.58

### Root Cause

In `live_trading_bot.py`, the `manage_active_trades()` function was only placing a trailing stop loss when TP2 was hit, but **not placing a new TP order** for the runner position.

**Before Fix (line 531-540):**
```python
# Trail after TP2 hit using 1× ATR offset
if trade.get('breakeven_set') and not trade.get('trailing_set') and self._hit_target(current_price, trade.get('tp2'), direction):
    # Only placed trailing stop, NO TP for runner!
    self.adapter.place_tp_sl_order('loss_plan', trailing_trigger, runner_size, ...)
    trade['trailing_set'] = True
```

## Fix Applied

### 1. Code Fix (`live_trading_bot.py`)

Updated `manage_active_trades()` to:
- Place trailing stop loss (as before)
- **Also place a new TP order** for the runner at 4.5× ATR from entry price
- Add proper error handling and retry logic
- Log TP placement for monitoring

**New TP Calculation:**
- **LONG**: Runner TP = entry_price + (ATR × 4.5)
- **SHORT**: Runner TP = entry_price - (ATR × 4.5)

This gives the runner a more aggressive target (4.5× ATR) compared to TP2 (3.0× ATR), allowing for larger profits on the remaining position.

### 2. Immediate Fix Script (`fix_missing_tp.py`)

Created a script to fix the current positions without TP:
- Uses provided entry prices (BNB: 886.58, XRP: 1.9316)
- Calculates runner TP at 4.5× ATR from entry
- Places both TP and trailing SL orders

## How to Use

### Fix Current Positions
```bash
python3 fix_missing_tp.py
```

This will:
1. Find XRP and BNB SHORT positions
2. Calculate appropriate TP levels (4.5× ATR from entry)
3. Place TP and SL orders

### Verify TP/SL Status
```bash
python3 check_positions_tpsl.py
```

## TP/SL Strategy Summary

### Initial Position (100%)
- **TP1**: 30% @ 1.5× ATR (first profit target)
- **TP2**: 40% @ 3.0× ATR (second profit target)
- **Runner**: 30% (no TP initially, managed dynamically)

### After TP1 Hits
- Runner gets **breakeven stop** at entry price
- No new TP yet (waits for TP2)

### After TP2 Hits (FIXED)
- Runner gets **trailing stop** at current_price ± 1× ATR
- **Runner gets NEW TP** at entry_price ± 4.5× ATR ✅

## Testing

The fix will be automatically applied when:
1. A new trade is executed
2. TP1 is hit (breakeven set)
3. TP2 is hit (trailing stop + new TP placed)

For existing positions, run `fix_missing_tp.py` to set TP immediately.

## Monitoring

Check logs for:
- `"[symbol] Runner TP placed @ {price} for runner ({size}) after TP2 execution"`
- `"CRITICAL: Failed to place runner TP after TP2 execution"` (if TP placement fails)

## Notes

- The runner TP (4.5× ATR) is more aggressive than TP2 (3.0× ATR) to maximize profit on remaining position
- If calculated TP is invalid (e.g., below current price for SHORT), it adjusts to 2% below current price
- Retry logic ensures TP placement is attempted twice if first attempt fails
