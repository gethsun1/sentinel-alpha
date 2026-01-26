# Active Position Stop-Loss Adjustments

**Date**: January 24, 2026 14:50 UTC  
**Purpose**: Update existing positions from old tight SL (0.33-0.45%) to new wide SL (3.0%)

---

## Positions Requiring Adjustment

### 1. DOGE SHORT
- **Symbol**: cmt_dogeusdt
- **Side**: SHORT
- **Entry Price**: 0.1241
- **Old SL** (estimated): 0.1245 (~0.35% away)
- **NEW SL**: **0.1278** (3.01% away)
- **NEW TP**: 0.1082
- **Improvement**: **8.6x wider** stop-loss

### 2. SOL SHORT  
- **Symbol**: cmt_solusdt
- **Side**: SHORT
- **Entry Price**: 127.15
- **Old SL** (estimated): 127.57 (~0.33% away)
- **NEW SL**: **130.96** (3.00% away)
- **NEW TP**: 110.92
- **Improvement**: **9.1x wider** stop-loss

### 3. XRP LONG
- **Symbol**: cmt_xrpusdt
- **Side**: LONG
- **Entry Price**: 1.9196
- **Old SL** (estimated): 1.911 (~0.45% away)
- **NEW SL**: **1.8620** (3.00% away)
- **NEW TP**: 2.1647
- **Improvement**: **6.7x wider** stop-loss

### 4. SOL LONG
- **Symbol**: cmt_solusdt
- **Side**: LONG
- **Entry Price**: 126.98
- **Old SL** (estimated): 126.41 (~0.45% away)
- **NEW SL**: **123.17** (3.00% away)
- **NEW TP**: 143.19
- **Improvement**: **6.7x wider** stop-loss

---

## Summary Table

| Symbol | Side | Entry | Old SL (~%) | NEW SL | NEW Distance | Improvement |
|--------|------|-------|-------------|--------|--------------|-------------|
| DOGE | SHORT | 0.1241 | 0.35% | **0.1278** | 3.01% | 8.6x wider |
| SOL | SHORT | 127.15 | 0.33% | **130.96** | 3.00% | 9.1x wider |
| XRP | LONG | 1.9196 | 0.45% | **1.8620** | 3.00% | 6.7x wider |
| SOL | LONG | 126.98 | 0.45% | **123.17** | 3.00% | 6.7x wider |

---

## Why This Is Critical

**Before Adjustment**:
- Stop-losses are 0.33-0.45% from entry
- Normal market noise is 0.5-1.0%
- **Result**: Positions will likely hit SL within minutes/hours

**After Adjustment**:
- Stop-losses are 3.0% from entry  
- Survives normal market volatility
- **Result**: Give trades room to develop and hit TP

**Risk**: Without adjusting these SL levels, these 4 positions will almost certainly hit their tight stop-losses before they can profit, continuing the 100% loss pattern.

---

## How to Adjust

### Option 1: Use WEEX Dashboard (Manual)
1. Log into WEEX
2. Go to "Positions" tab
3. For each position, click "Modify TP/SL"
4. Update stop-loss to the NEW SL values above
5. Optionally update take-profit to NEW TP values

### Option 2: Run Adjustment Script
```bash
cd /root/sentinel-alpha
source venv/bin/activate
python3 adjust_active_positions_sl.py
```

**Note**: The script may require additional setup to modify existing positions via API. Manual adjustment via dashboard is recommended for reliability.

---

## Expected Results After Adjustment

-Positions survive normal market fluctuations
- Stop-losses only hit on true trend reversals (not noise)
- Improved chance of hitting take-profit targets
- Consistent with new bot parameters (all future trades will use these wider SL)

---

## Risk/Reward Analysis

All positions maintain **4.26:1** risk/reward ratio:
- Risk: 3.0% (stop-loss distance)
- Reward: 12.78% average (take-profit distance)

With this RR, only need **19% win rate** to break even (much better than 50% with 1:1 RR).

---

## Urgency

⚠️ **HIGH PRIORITY** - These positions should be adjusted ASAP:
- Current tight SL could trigger any moment
- Market volatility can cause 0.5-1% moves in minutes
- Once SL hits, position is closed at a loss (irreversible)

**Recommended**: Adjust within next 15-30 minutes
