# Sentinel Alpha - Architecture Diagram

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SENTINEL ALPHA TRADING SYSTEM                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         1. DATA INGESTION LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐         ┌──────────────────┐                          │
│  │  Binance API     │────────▶│  MarketStream    │                          │
│  │  (Mock/Real)     │         │  fetch_tick()    │                          │
│  └──────────────────┘         └──────────────────┘                          │
│                                         │                                    │
│                                         ▼                                    │
│                            [timestamp, price, quantity]                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      2. FEATURE ENGINEERING LAYER                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  FeatureEngineering                                                 │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │  • compute_returns()            → Log returns                       │    │
│  │  • compute_volatility()         → Rolling std dev                   │    │
│  │  • compute_volume_acceleration()→ Volume momentum                   │    │
│  │  • compute_regime_stability()   → Inverse variance                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                         │                                    │
│                                         ▼                                    │
│              [price, returns, volatility, volume_accel, stability]           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       3. AI INTELLIGENCE LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │  REGIME CLASSIFIER                                         │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │  Input: Features                                           │             │
│  │  Output: [TREND_UP, TREND_DOWN, RANGE,                    │             │
│  │           VOLATILITY_EXPANSION, VOLATILITY_COMPRESSION]    │             │
│  │                                                            │             │
│  │  Logic:                                                    │             │
│  │  • High vol + positive returns → TREND_UP                 │             │
│  │  • High vol + negative returns → TREND_DOWN               │             │
│  │  • Low vol → RANGE                                        │             │
│  │  • Extreme vol → VOLATILITY_EXPANSION                     │             │
│  └────────────────────────────────────────────────────────────┘             │
│                               │                                             │
│                               ▼                                             │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │  CONFIDENCE MODEL                                          │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │  Input: Features + Regimes                                 │             │
│  │  Output: Confidence scores [0.0 - 1.0]                     │             │
│  │                                                            │             │
│  │  Formula:                                                  │             │
│  │  • TREND: min(1.0, stability × (1 - volatility))          │             │
│  │  • RANGE: min(1.0, stability × (1 - volatility/2))        │             │
│  │  • Volatility regimes: [0.3 - 0.8]                        │             │
│  └────────────────────────────────────────────────────────────┘             │
│                               │                                             │
│                               ▼                                             │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │  RISK FILTER                                               │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │  Input: Features + Regimes + Confidence                    │             │
│  │  Output: [LONG, SHORT, NO-TRADE]                           │             │
│  │                                                            │             │
│  │  Gates:                                                    │             │
│  │  ✓ Confidence > 0.5                                        │             │
│  │  ✓ Volatility cooldown (2 ticks after spike)              │             │
│  │  ✓ Regime-based signal mapping                            │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         4. SIGNAL ENGINE LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │  SignalEngine                                              │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │  generate_signals()                                        │             │
│  │  ├─ Orchestrates: Features → Regime → Confidence → Filter │             │
│  │  └─ Output: [timestamp, price, regime, confidence, signal] │             │
│  │                                                            │             │
│  │  execute_signals()                                         │             │
│  │  ├─ Loads config (competition.yaml)                       │             │
│  │  ├─ Checks risk thresholds                                │             │
│  │  ├─ Validates execution guards                            │             │
│  │  └─ Places orders via adapter                             │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      5. RISK MANAGEMENT LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │  PolicyRules     │  │  ExecutionGuard  │  │  PnLGuard        │          │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤          │
│  │ • Min confidence │  │ • Cooldown: 180s │  │ • Max DD: 2.0%   │          │
│  │ • Max leverage   │  │ • Position limit │  │ • Auto halt      │          │
│  │ • Vol threshold  │  │ • Trade tracking │  │                  │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                  │                                           │
│                                  ▼                                           │
│                         ┌─────────────────┐                                 │
│                         │  PositionSizer  │                                 │
│                         ├─────────────────┤                                 │
│                         │ size = base ×   │                                 │
│                         │ confidence ×    │                                 │
│                         │ adaptive_factor │                                 │
│                         └─────────────────┘                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        6. EXECUTION LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │  WeexExecutionAdapter                                      │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │  • API: https://api-contract.weex.com                      │             │
│  │  • Authentication: HMAC-SHA256                             │             │
│  │  • Symbols: cmt_btcusdt, cmt_ethusdt, ...                 │             │
│  │  • Order types: Limit only                                 │             │
│  │  • Leverage: ≤ 20×                                         │             │
│  │  • Dry-run mode: Available                                 │             │
│  │                                                            │             │
│  │  Methods:                                                  │             │
│  │  • set_leverage()                                          │             │
│  │  • place_order(direction, size, price)                    │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       7. AGENT ORCHESTRATION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │  SentinelAlphaAgent                                        │             │
│  ├────────────────────────────────────────────────────────────┤             │
│  │                                                            │             │
│  │  step(market_data):                                        │             │
│  │      1. signal = perceive(market_data)                     │             │
│  │         ↓                                                  │             │
│  │      2. decision = decide(signal)                          │             │
│  │         ↓                                                  │             │
│  │      3. action = act(decision, price)                      │             │
│  │         ├─ Check PnLGuard                                  │             │
│  │         ├─ Check ExecutionGuard                            │             │
│  │         └─ Execute via adapter                             │             │
│  │         ↓                                                  │             │
│  │      4. audit_logger.log_step(...)                         │             │
│  │                                                            │             │
│  └────────────────────────────────────────────────────────────┘             │
│                               │                                             │
│  ┌────────────────────┐  ┌─────────────────┐  ┌────────────────────┐       │
│  │  AgentMemory       │  │  Explainer      │  │  JsonLogger        │       │
│  ├────────────────────┤  ├─────────────────┤  ├────────────────────┤       │
│  │ • Recent PnLs      │  │ • Rationale     │  │ • audit.jsonl      │       │
│  │ • Recent confidence│  │   generation    │  │ • compliance.jsonl │       │
│  │ • Adaptive factor  │  │                 │  │                    │       │
│  └────────────────────┘  └─────────────────┘  └────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      8. EVALUATION & REPORTING                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                  ┌──────────────────┐                 │
│  │  Metrics         │                  │  VisualReports   │                 │
│  ├──────────────────┤                  ├──────────────────┤                 │
│  │ • Directional    │                  │ • Price chart    │                 │
│  │   accuracy       │                  │   with signals   │                 │
│  │ • Max drawdown   │                  │ • Regime dist.   │                 │
│  │ • Signal count   │                  │ • Confidence     │                 │
│  │ • Signal/noise   │                  │   over time      │                 │
│  └──────────────────┘                  └──────────────────┘                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

```

## Component Interaction Flow

```
Market Data
    │
    ├─▶ FeatureEngineering ─▶ RegimeClassifier
    │                              │
    │                              ▼
    │                         ConfidenceModel
    │                              │
    │                              ▼
    │                         RiskFilter
    │                              │
    └──────────────────────────────┴─▶ SignalEngine
                                            │
                                            ├─▶ PolicyRules (check)
                                            ├─▶ ExecutionGuard (check)
                                            ├─▶ PnLGuard (check)
                                            ├─▶ PositionSizer (calculate)
                                            │
                                            ▼
                                    WeexExecutionAdapter
                                            │
                                            ├─▶ JsonLogger (audit)
                                            └─▶ JsonLogger (compliance)
```

## Risk Control Cascade

```
Signal Request
    │
    ├─▶ [Layer 1] AI Risk Filter
    │   ├─ Confidence threshold (0.5)
    │   ├─ Volatility cooldown (2 ticks)
    │   └─ Regime gating
    │
    ├─▶ [Layer 2] Policy Rules
    │   ├─ Min confidence (0.65 in config)
    │   ├─ Max leverage (20×)
    │   └─ Prohibited strategies
    │
    ├─▶ [Layer 3] Execution Guard
    │   ├─ Cooldown check (180s)
    │   └─ Position limit check
    │
    ├─▶ [Layer 4] PnL Guard
    │   └─ Drawdown check (2.0%)
    │
    └─▶ [Layer 5] WEEX Adapter
        ├─ Direction validation
        ├─ Size validation
        ├─ Price validation
        └─ Symbol validation
```

## Data Schema Flow

### 1. Market Data
```
DataFrame: [timestamp, price, quantity]
```

### 2. Features
```
DataFrame: [price, returns, volatility, volume_acceleration, regime_stability]
```

### 3. AI Outputs
```
Series: [regime_labels]
Series: [confidence_scores]
Series: [filtered_signals]
```

### 4. Final Signals
```
DataFrame: [timestamp, price, regime, confidence, signal]
```

### 5. Audit Logs
```json
{
  "event": "signal_evaluated",
  "direction": "LONG",
  "confidence": 0.78,
  "price": 50125.50,
  "timestamp": 1735131600000
}
```

## Configuration Dependencies

```
competition.yaml
    │
    ├─▶ ExecutionGuard (cooldown_seconds, max_position_size)
    ├─▶ WeexExecutionAdapter (symbol, leverage, dry_run)
    ├─▶ JsonLogger (audit_path, compliance_path)
    └─▶ SignalEngine (min_confidence, max_drawdown_pct)
```

## Module Dependencies

```
utils/logger.py
    └─▶ strategy/signal_engine.py

data/market_stream.py
    └─▶ data/feature_engineering.py
        └─▶ models/regime_classifier.py
            └─▶ models/confidence_model.py
                └─▶ models/risk_filter.py
                    └─▶ strategy/signal_engine.py

execution/execution_guard.py
    └─▶ strategy/signal_engine.py
        └─▶ agent/sentinel_agent.py

execution/weex_adapter.py
    └─▶ strategy/signal_engine.py
        └─▶ agent/sentinel_agent.py

risk/pnl_guard.py
    └─▶ agent/sentinel_agent.py

agent/memory.py
    └─▶ strategy/position_sizer.py

agent/explainer.py
    └─▶ agent/sentinel_agent.py (optional)

strategy/policy_rules.py
    └─▶ Independent validation module

evaluation/metrics.py
    └─▶ demo/historical_replay.py

evaluation/visual_reports.py
    └─▶ demo/historical_replay.py
```

---

## Key Design Patterns

### 1. Pipeline Pattern
Each layer transforms data and passes it to the next stage.

### 2. Guard Pattern
Multiple validation layers that can block execution.

### 3. Strategy Pattern
Different execution modes (dry_run, competition, live).

### 4. Observer Pattern
Logging at every critical decision point.

### 5. Adapter Pattern
Exchange-agnostic execution layer (WEEX adapter, can add others).

---

## Execution Modes

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Dry Run    │     │ Competition │     │    Live     │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ No API calls│     │ WEEX API    │     │ Real money  │
│ Mock data   │     │ Test capital│     │ Full risk   │
│ Full logging│     │ Full logging│     │ Full logging│
└─────────────┘     └─────────────┘     └─────────────┘
```

---

**Legend:**
- `─▶` : Data flow
- `├─` : Branching logic
- `└─` : Terminal flow
- `[ ]` : Processing stage
- `( )` : Parameters/config


