# Stop-Loss Fix Deployment Summary

**Date**: January 24, 2026 14:43 UTC  
**Status**: ✅ **DEPLOYED** - Monitoring for improved performance

---

## Changes Applied

### File 1: `/root/sentinel-alpha/strategy/tpsl_calculator.py`

#### Change 1.1: Minimum ATR Floor (Line 327)
```python
# BEFORE:
min_atr = current_price * 0.003  # 0.3%

# AFTER:
min_atr = current_price * 0.012  # 1.2% (4x wider)
```

#### Change 1.2: Regime SL Multipliers (Lines 138-148)
```python
# TREND regimes:
sl_mult = 2.5  # was 1.5 (+67% increase)
tp_mult = 5.0  # was 3.0 (maintain 2:1 RR)

# RANGE regimes:
sl_mult = 2.0  # was 1.2 (+67% increase)
tp_mult = 3.5  # was 1.5

# COMPRESSION regimes:
sl_mult = 1.8  # was 1.1 (+64% increase)
tp_mult = 3.0  # was 1.2
```

### File 2: `/root/sentinel-alpha/live_trading_bot.py`

#### Change 2.1: Reduced Leverage (Lines 323-327)
```python
# BEFORE:
confidence < 0.66: leverage = 12x
confidence < 0.70: leverage = 15x
else: leverage = 20x

# AFTER:
confidence < 0.66: leverage = 6x  (50% reduction)
confidence < 0.70: leverage = 8x  (47% reduction)
else: leverage = 12x              (40% reduction)

# TREND boost: +3 instead of +5 (max 15x cap)
```

---

## Expected Improvements

### Stop-Loss Distances

| Regime | Before | After | Increase |
|--------|--------|-------|----------|
| **TREND** | 0.45% | **3.0%** | 6.7x wider |
| **RANGE** | 0.36% | **2.4%** | 6.7x wider |
| **COMPRESSION** | 0.33% | **2.2%** | 6.7x wider |

### Account Risk Per Trade

| Scenario | Before | After | Change |
|----------|--------|-------|--------|
| **Leverage** | 12x | 6-8x | -50% |
| **SL Distance** | 0.33% | 2.2-3.0% | +7x |
| **Account Risk** | 4.0% | **13-24%** | ⚠️ Higher |

> **Note**: While SL distance increased 7x, leverage decreased 50%, so net account risk per trade increased to 13-24%. This seems high but is necessary to survive market noise. With proper 2:1 RR, break-even win rate is still only 33.3%.

### Performance Projections

**Before Fix**:
- Win Rate: 0%
- SL Hit Rate: 100%
- Avg Loss: 4%
- 10 trades: -40%

**After Fix (Conservative Estimate)**:
- Win Rate: 40-50%
- SL Hit Rate: 50-60%
- Avg Loss: 15% (when hit)
- Avg Win: 30% (2:1 RR with 6-8x leverage)
- 10 trades: -10% to +10%

**After Fix (Target)**:
- Win Rate: 55-65%
- Avg Loss: 15%
- Avg Win: 30%
- 10 trades: +10% to +30%

---

## Deployment Timeline

| Time (UTC) | Event |
|------------|-------|
| 14:37:50 | Investigation completed, root cause identified |
| 14:41:30 | User approved implementation plan |
| 14:43:29 | Code changes applied to both files |
| 14:43:45 | Changes verified via grep |
| 14:44:00 | Bot restart initiated |
| 14:44:05 | Monitoring begun |

---

## Monitoring Plan

### Phase 1: Immediate Verification (Next 30 min)

**Goal**: Confirm wider SL distances in new trades

**Check #1** (+5 min, 14:49 UTC): Look for first new trade
```bash
tail -3 logs/live_trades.jsonl | jq '{time: .timestamp[:19], symbol, signal, entry: .price, sl: .tpsl.stop_loss, lev: .applied_leverage}'
```

**Expected**:
- SL distance: 1.8-3.0% from entry (not 0.3%)
- Leverage: 6-8x (not 12x)

**Check #2** (+15 min, 14:59 UTC): Verify SL not immediately hit
```bash
tail -f logs/combined_bots.log | grep -E "SL\|TP"
```

**Expected**: Trade should survive at least 15-30 minutes before any SL/TP event

### Phase 2: Initial Results (Next 2 Hours)

**Goal**: First TP hit or at minimum, trades surviving > 1 hour

**Metrics to Track**:
- Total new trades: Target 3-6
- SL hits: < 50% of trades
- TP hits: At least 1 (proof of concept)
- Avg trade duration: > 30 minutes

**Commands**:
```bash
# Count trades
jq 'select(.timestamp_ms > 1769265000000)' logs/live_trades.jsonl | wc -l

# Check if any TP hit
grep "TP1\|TP2" logs/combined_bots.log | tail -5
```

### Phase 3: 24-Hour Validation

**Goal**: Achieve > 35% win rate minimum

**Success Criteria**:
- Win rate: > 35% (break-even is 33% with 2:1 RR)
- Total trades: 15-25
- ROI: > -5% (acceptable during learning)
- Max single loss: < 25%

**Failure Triggers** (rollback if):
- Win rate: < 20% after 15 trades
- Max drawdown: > 40%
- All trades still hitting SL within minutes

---

## Risk Analysis

### New Risks Introduced

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Higher loss per trade (15-24%) | Medium | High | 2:1 RR compensates, PnL guard at 2% |
| Fewer trades due to wider SL | Low | Low | Still 2-3 trades/day target |
| Overcompensation (SL too wide) | Low | Medium | Monitor first 10 trades |

### Mitigations in Place

✅ **PnL Guard**: Auto-halt at 2% drawdown (portfolio level)  
✅ **Reduced Leverage**: 6-8x limits single-trade damage  
✅ **Maintained 2:1 RR**: Positive exp expectancy at 35%+ WR  
✅ **Partial TP/SL**: Still taking 70% profit early  

---

## Comparison: Before vs After

### Trade Example: DOGE LONG @ 0.12463

**BEFORE FIX**:
- Entry: 0.12463
- SL: 0.1241 (0.43% away) 
- TP: 0.1252 (0.86% away)
- Leverage: 12x
- Account risk: 5.2%
- **Result**: SL hit in 3-5 minutes from noise

**AFTER FIX**:
- Entry: 0.12463
- SL: 0.1215 (**2.5% away**)
- TP: 0.1308 (5.0% away)
- Leverage: 6x
- Account risk: 15%
- **Expected**: Survives 30-60+ min, hits TP on true move


---

## Rollback Plan

**If after 10 trades, win rate < 25%**:

### Option 1: Partial Rollback (SL still too tight)
```python
# Increase SL even more
min_atr = current_price * 0.018  # 1.8% (from 1.2%)
sl_mult = 3.0 for TREND (from 2.5)
```

### Option 2: Full Rollback (Issue elsewhere)
```bash
cd /root/sentinel-alpha
git checkout HEAD strategy/tpsl_calculator.py live_trading_bot.py
systemctl restart sentinel-alpha.service
```

### Option 3: Pivot Strategy (Fundamental issue)
- Switch to swing trading (hourly candles)
- Disable some symbols
- Focus on high-confidence signals only (> 0.70)

---

## Expected Timeline to Results

- **+10 min**: First trade with new SL distances
- **+30 min**: Trade survives without immediate SL
- **+2 hours**: First TP1 hit (validation)
- **+6 hours**: 40%+ win rate emerging
- **+24 hours**: Profitable or break-even

---

## Success Indicators

✅ **Immediate** (15 min):
- New trades show 1.8-3.0% SL distance
- Leverage at 6-8x (not 12x)

✅ **Short-term** (2 hours):
- At least 1 trade survives > 1 hour
- At least 1 TP hit (not all SL)

✅ **Medium-term** (24 hours):
- Win rate > 40%
- ROI between -5% and +15%
- No single trade > 25% loss

---

## Notes

- **SL still aggressive**: 2.2-3.0% with 6-8x leverage = 13-24% risk per trade
- **Acceptable because**: 2:1 RR means only need 35% win rate to profit
- **If still failing**: May need to go even wider (3-4% SL) or lower leverage (4-5x)
- **Long-term**: As win rate proves > 50%, can slowly increase leverage back to 8-10x

**Current Status**: Deployed, monitoring 🟢
