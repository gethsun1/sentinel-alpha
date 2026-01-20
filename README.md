# 🤖 Sentinel Alpha

**AI-Powered Autonomous Trading System for Cryptocurrency Markets**

![Status](https://img.shields.io/badge/status-live-brightgreen) ![Competition](https://img.shields.io/badge/WEEX-AI%20Wars-blue) ![Python](https://img.shields.io/badge/python-3.10+-blue)

---

## 🏆 Competition Entry

**WEEX AI Wars: Alpha Awakens**  
A fully autonomous, AI-driven trading system competing in the WEEX cryptocurrency trading competition.

**Live Trading:** ✅ Operational on VPS with static IP  
**Exchange:** WEEX Contract Trading API  
**Asset:** BTC/USDT Perpetual Contracts  
**Status:** 🟢 ACTIVE

---

## 🎯 Overview

**Sentinel Alpha** is a production-grade, AI-powered autonomous trading system that combines:

- 🧠 **Advanced AI Intelligence** - Enhanced regime classification with fuzzy logic
- 📊 **Real-Time Market Analysis** - Live data ingestion from WEEX API
- 🛡️ **5-Layer Risk Management** - Comprehensive capital protection
- 🔄 **Adaptive Learning** - Self-improving through online learning
- 📈 **Autonomous Execution** - 24/7 automated trading with full audit trail

### Key Features

✅ **Real-Time Market Intelligence**
- Live price/volume/volatility data streaming
- Advanced feature engineering (momentum, stability, acceleration)
- Multi-regime detection (TREND_UP/DOWN, RANGE, VOLATILITY_EXPANSION/COMPRESSION)

✅ **AI-Driven Decision Making**
- Enhanced regime classifier with fuzzy logic
- Confidence-based signal generation
- Adaptive learning from trade outcomes
- Pattern recognition and ensemble methods

✅ **Professional Risk Management**
- PnL Guard: 2% max drawdown auto-halt
- Execution Guard: Cooldown periods & position limits
- Policy Rules: Compliance enforcement
- Position Sizing: Confidence-based dynamic sizing
- Volatility Filter: Risk-aware signal blocking

✅ **24/7 Autonomous Operation**
- Deployed on VPS with static IP
- Self-monitoring and error handling
- Complete audit logging (JSON)
- Web dashboard for real-time monitoring

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SENTINEL ALPHA SYSTEM                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  WEEX Exchange  │
│   Market Data   │◄──────┐
└─────────────────┘       │
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                  DATA INGESTION LAYER                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • Real-time price/volume streaming (60s intervals)  │   │
│  │ • Feature engineering (momentum, volatility, accel) │   │
│  │ • Historical data buffer (100 data points)          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   AI INTELLIGENCE LAYER                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Enhanced Regime Classifier (Fuzzy Logic)            │   │
│  │ • TREND_UP / TREND_DOWN / RANGE                     │   │
│  │ • VOLATILITY_EXPANSION / COMPRESSION                │   │
│  │                                                      │   │
│  │ Adaptive Learning Agent                             │   │
│  │ • Track win rates per signal type                   │   │
│  │ • Dynamic confidence calibration                    │   │
│  │ • Online learning from outcomes                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    SIGNAL ENGINE LAYER                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Signal Generation → LONG / SHORT / NO-TRADE         │   │
│  │ Confidence Scoring → 0.0-1.0 (threshold: 0.70)      │   │
│  │ Explainable Reasoning → Human-readable rationale    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 RISK MANAGEMENT LAYER (5 Levels)             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. PnL Guard: Max 2% drawdown auto-halt             │   │
│  │ 2. Execution Guard: Cooldown & position limits      │   │
│  │ 3. Policy Rules: Leverage/compliance enforcement    │   │
│  │ 4. Position Sizer: Confidence-based sizing          │   │
│  │ 5. Volatility Filter: Spike detection & blocking    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   EXECUTION LAYER                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ WEEX API Integration                                 │   │
│  │ • Authenticated requests (HMAC-SHA256)              │   │
│  │ • Automatic leverage setting (4×)                   │   │
│  │ • Limit order placement                             │   │
│  │ • Order status tracking                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  MONITORING & LOGGING                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • JSON audit logs (signals, trades, performance)    │   │
│  │ • Real-time web dashboard (Flask)                   │   │
│  │ • Performance metrics tracking                      │   │
│  │ • Alert system for critical events                  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

See [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) for detailed system design.

---

## 🧠 AI Intelligence System

### Enhanced Regime Classifier

**Technology:** Fuzzy logic with weighted scoring system

**Regimes Detected:**
- `TREND_UP` - Sustained upward momentum with stability
- `TREND_DOWN` - Sustained downward momentum with stability
- `RANGE` - Mean-reverting price behavior
- `VOLATILITY_EXPANSION` - Rapid increase in price dispersion
- `VOLATILITY_COMPRESSION` - Low-energy consolidation phase

**Advantages over threshold-based systems:**
- Handles uncertain/transitional market states
- Gradual regime transitions vs hard boundaries
- More robust to noise and false signals

### Adaptive Learning Agent

**Capability:** Online learning from trade outcomes

**Features:**
- Tracks win rates for LONG/SHORT signals independently
- Dynamically calibrates confidence thresholds
- Adapts to changing market conditions
- Self-improves over time

**Learning Process:**
```
Trade → Outcome → Win Rate Update → Confidence Calibration → Better Signals
```

---

## 📊 Performance Metrics

### Target Performance (Competition)

| Metric | Target | Control |
|--------|--------|---------|
| Daily ROI | 0.5-2% | Conservative growth |
| Win Rate | 55-65% | Slight edge over random |
| Max Drawdown | <2% | Auto-halt protection |
| Trades/Day | 3-15 | Quality over quantity |
| Leverage | 4× | Moderate risk |

### Risk Controls

- ✅ Maximum position: 0.001 BTC
- ✅ Cooldown: 180s between trades
- ✅ Min confidence: 70% for execution
- ✅ Auto-halt: If drawdown ≥2%
- ✅ Volatility filter: Block during spikes

---

## 🚀 Deployment

### Infrastructure

- **Platform:** RackNerd KVM VPS
- **Location:** Los Angeles Data Center
- **IP:** Static (allowlisted with WEEX)
- **Uptime:** 24/7 operation in tmux sessions
- **Monitoring:** Web dashboard + JSON logs

### Technology Stack

```python
# Core
Python 3.10+
pandas, numpy          # Data processing
requests              # API communication

# Configuration
pyyaml                # Config management
python-dotenv         # Credential management

# Monitoring
Flask                 # Web dashboard
```

### Live Operation

```bash
# Bot runs in tmux
tmux attach -t trading

# Dashboard accessible at
http://[VPS_IP]:5000

# Logs stored in
logs/live_trades.jsonl
logs/live_signals.jsonl
logs/performance.jsonl
```

---

## 📁 Repository Structure

```
sentinel-alpha/
│
├── agent/
│   ├── sentinel_agent.py          # Main autonomous agent
│   ├── memory.py                  # Adaptive memory module
│   └── explainer.py               # Decision explainability
│
├── data/
│   ├── market_stream.py           # Real-time data ingestion
│   └── feature_engineering.py     # Feature extraction
│
├── models/
│   ├── regime_classifier.py       # Basic regime classifier
│   ├── enhanced_regime_classifier.py  # Fuzzy logic classifier
│   ├── confidence_model.py        # Confidence scoring
│   ├── adaptive_learning_agent.py # Online learning
│   └── risk_filter.py             # Risk filtering
│
├── strategy/
│   ├── signal_engine.py           # Signal generation
│   ├── policy_rules.py            # Compliance rules
│   └── position_sizer.py          # Position sizing
│
├── execution/
│   ├── weex_adapter.py            # WEEX API integration
│   └── execution_guard.py         # Execution controls
│
├── risk/
│   └── pnl_guard.py               # Drawdown protection
│
├── evaluation/
│   ├── metrics.py                 # Performance metrics
│   └── visual_reports.py          # Visualization
│
├── utils/
│   └── logger.py                  # JSON logging
│
├── config/
│   └── competition.yaml           # Competition config
│
├── live_trading_bot.py            # Main live trading script
├── monitor_dashboard.py           # Web monitoring dashboard
└── ai_enhanced_engine.py          # AI-enhanced demo
```

---

## 🛡️ Security & Compliance

### Credential Management

- ✅ API keys stored in `.env` (not in repository)
- ✅ Environment variables for sensitive data
- ✅ HMAC-SHA256 signature for API authentication
- ✅ IP allowlisting with WEEX

### Audit Trail

All trading activity is logged:
```json
{
  "timestamp": 1766774396,
  "signal": "LONG",
  "confidence": 0.752,
  "regime": "TREND_UP",
  "price": 87400.50,
  "order_id": "699502522531840447",
  "reasoning": "Strong uptrend with 75% confidence"
}
```

### Compliance

- ✅ Leverage ≤ 20× (competition requirement)
- ✅ No prohibited strategies (martingale, grid, etc.)
- ✅ Minimum 10 trades requirement
- ✅ Risk disclosure and transparency
- ✅ Explainable AI decisions

---

## 🎯 Competition Strategy

### Phase 1: Data Collection (Ticks 1-20)
Building market history for AI analysis

### Phase 2: Conservative Trading (Days 1-3)
- Low-frequency, high-confidence trades
- System calibration
- Risk validation

### Phase 3: Adaptive Trading (Days 4-7)
- Learning agent optimizes thresholds
- Increased trade frequency
- Performance acceleration

### Phase 4: Optimized Trading (Days 8-10)
- Fully calibrated system
- Maximum efficiency
- Competitive performance

---

## 📊 Monitoring Dashboard

Real-time web interface showing:

- 🟢 **Bot Status** - Active/Offline indicator
- 💰 **Account Balance** - Equity & P&L
- 📈 **Performance** - ROI & Drawdown
- 🎯 **Signals** - Recent decisions with reasoning
- 💼 **Trades** - Execution history

**Access:** Web browser at `http://[VPS_IP]:5000`  
**Updates:** Auto-refresh every 5 seconds

---

## 🔧 Configuration

### Competition Settings

```yaml
# config/competition.yaml
exchange:
  name: "WEEX"
  symbol: "cmt_btcusdt"
  leverage: 4
  max_position_size: 0.001

risk:
  max_trades_per_hour: 20
  min_confidence: 0.70
  max_drawdown_pct: 0.02
  cooldown_seconds: 180
```

### Environment Variables

```bash
# .env (not in repository)
WEEX_API_KEY=your_api_key_here
WEEX_SECRET_KEY=your_secret_key_here
WEEX_PASSPHRASE=your_passphrase_here
```

---

## 📈 Expected Performance

### Conservative Estimates

**Daily Performance:**
- ROI: 0.5-2%
- Trades: 3-15
- Win Rate: 55-65%

**10-Day Competition:**
- Starting Capital: $1,000
- Target ROI: 5-20%
- Expected Ending: $1,050-$1,200
- Max Drawdown: <2%

### Competitive Advantages

1. **AI Enhancement** - Advanced regime detection
2. **Adaptive Learning** - Self-improvement over time
3. **Risk Management** - 5-layer protection system
4. **Transparency** - Fully explainable decisions
5. **Reliability** - Professional infrastructure

---

## 🧪 Testing & Validation

### Pre-Deployment Testing

✅ API connectivity tests  
✅ Authentication verification  
✅ Order placement validation  
✅ Risk control verification  
✅ Logging system validation

### Live Validation

✅ Real-time data streaming  
✅ Signal generation accuracy  
✅ Execution reliability  
✅ Risk management activation  
✅ Performance tracking

---

## 📚 Documentation

- **README.md** - This file (system overview)
- **ARCHITECTURE_DIAGRAM.md** - Detailed system design
- **Code Comments** - Inline documentation throughout

---

## 🚦 System Status

| Component | Status | Notes |
|-----------|--------|-------|
| WEEX API | 🟢 Connected | IP allowlisted |
| Data Ingestion | 🟢 Active | 60s intervals |
| AI Engine | 🟢 Running | Enhanced classifier |
| Risk Guards | 🟢 Active | 5-layer protection |
| Execution | 🟢 Operational | Automated orders |
| Monitoring | 🟢 Live | Web dashboard |
| Logging | 🟢 Recording | JSON audit trail |

**Overall:** 🟢 **FULLY OPERATIONAL**

---

## 🏆 Competition Goals

### Primary Objectives
1. ✅ Achieve positive ROI (5-20%)
2. ✅ Maintain low drawdown (<2%)
3. ✅ Demonstrate AI capability
4. ✅ Provide full transparency
5. ✅ Complete competition duration

### Success Metrics
- **Technical:** System reliability & uptime
- **Performance:** ROI vs drawdown ratio
- **Innovation:** AI enhancement quality
- **Transparency:** Audit trail completeness

---

## ⚖️ Disclaimer

This project is developed for **competition and educational purposes**.

- ❌ Not financial advice
- ❌ No guaranteed profits
- ❌ Trading involves risk
- ✅ For research and demonstration only

**Past performance does not guarantee future results.**

---

## 👨‍💻 Author

**Gethsun Misesi**  
AI Researcher • Trading Systems Engineer  

**Competition:** WEEX AI Wars: Alpha Awakens  
**Contact:** [GitHub Profile]

---

## 📜 License

This project is proprietary software developed for the WEEX AI Wars competition.

**All rights reserved.**

---

## 🙏 Acknowledgments

- **WEEX Team** - For hosting the AI Wars competition
- **Python Community** - For excellent data science tools
- **Open Source Contributors** - For pandas, numpy, Flask

---

## 📞 Support

For competition-related inquiries:
- Review the documentation files
- Check system logs for debugging
- Verify API connectivity
- Monitor dashboard for status

---

<div align="center">

**🤖 Sentinel Alpha - Intelligent, Autonomous, Transparent**

![Built with Python](https://img.shields.io/badge/built%20with-Python-blue)
![AI Powered](https://img.shields.io/badge/AI-Powered-brightgreen)
![Status Live](https://img.shields.io/badge/status-LIVE-success)

**Competing in WEEX AI Wars 2025**

</div>
