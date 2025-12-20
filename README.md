----------

# Sentinel Alpha

**Real-Time AI Market Regime Intelligence for Disciplined Crypto Trading**

----------

## Overview

**Sentinel Alpha** is an AI-driven market intelligence system that analyzes real-time cryptocurrency market data to detect short-term market regimes and generate **explainable, risk-aware trading signals**.

The project is designed with a strict separation between **market intelligence** and **trade execution**, prioritizing transparency, auditability, and risk discipline. Sentinel Alpha is submitted for the **AI Wars: WEEX Alpha Awakens** hackathon, using **Binance exchange market data** for demonstration and verification during the review phase.

----------

## Design Philosophy

> _The market speaks continuously.  
> Intelligence listens patiently and acts selectively._

Sentinel Alpha is built on four non-negotiable principles:

1.  **AI informs decisions; it does not gamble**
    
2.  **Risk controls dominate signal ambition**
    
3.  **Execution is external and rule-based**
    
4.  **Every signal must be explainable**
    

This philosophy aligns with professional trading system standards and WEEX competition requirements.

----------

## What Sentinel Alpha Is — and Is Not

### What It Is

-   A real-time AI **market regime detection** engine
    
-   A **signal-generation system**, not an autonomous trader
    
-   A research-grade, reviewable trading intelligence framework
    

### What It Is Not

-   Not a high-leverage trading bot
    
-   Not a black-box profit optimizer
    
-   Not a self-learning system reacting to live PnL
    

----------

## System Scope (Demo Phase)

-   **Market data source:** Binance (public market data via API)
    
-   **Assets:** High-liquidity pairs (BTC, ETH, SOL, etc.)
    
-   **Time horizon:** Short-term (seconds to minutes)
    
-   **Signal types:** LONG / SHORT / NO-TRADE
    
-   **Execution:** External, rule-based, and intentionally decoupled
    

No private account balances or sensitive credentials are required for review.

----------

## High-Level Architecture

Sentinel Alpha operates as a modular pipeline:

1.  **Market Data Ingestion**  
    Continuous collection of price, volume, and volatility data from Binance.
    
2.  **Feature Engineering**  
    Transformation of raw market data into normalized, model-ready signals.
    
3.  **AI Intelligence Layer**
    
    -   Market regime classification
        
    -   Confidence estimation
        
    -   Risk-aware filtering
        
4.  **Signal Engine**  
    Emits explainable trade signals only when all validation gates are passed.
    
5.  **Audit & Evaluation Layer**  
    Logs, metrics, and visual artifacts for review and reproducibility.
    

----------

## Market Regime Framework

The system models markets as evolving states rather than static indicators.

Example regimes include:

-   **TREND_UP** — sustained upward momentum
    
-   **TREND_DOWN** — sustained downward momentum
    
-   **RANGE** — mean-reverting price behavior
    
-   **VOLATILITY_EXPANSION** — rapid increase in price dispersion
    
-   **VOLATILITY_COMPRESSION** — low-energy consolidation
    

Signals are generated **only when a regime is stable and confidence exceeds predefined thresholds**.

----------

## AI Participation (Explicit Disclosure)

### Role of AI

Artificial Intelligence in Sentinel Alpha is used exclusively for:

-   Classifying short-term market regimes
    
-   Estimating confidence in detected patterns
    
-   Blocking signals during unstable or high-risk conditions
    

### Explicit AI Limitations

AI **does not**:

-   Determine position size
    
-   Modify leverage or risk limits
    
-   Execute trades autonomously
    
-   Self-optimize based on live profit or loss
    

This ensures **control, interpretability, and compliance**.

----------

## Risk & Compliance Controls

-   Conceptual leverage capped at **≤ 20×**
    
-   No martingale, grid, or averaging-down logic
    
-   Cooldown periods after consecutive losses
    
-   Volatility spike detection blocks signals
    
-   Minimum signal count enforced (≥ 10)
    

Risk management is embedded at the **system level**, not added as an afterthought.

----------

## Evaluation Metrics

System performance is assessed using:

-   Directional signal accuracy
    
-   Maximum drawdown
    
-   Volatility-adjusted return proxy
    
-   Signal-to-noise ratio
    
-   Regime stability duration
    
-   Trade frequency compliance
    

Metrics are designed to reflect **robustness and discipline**, not hype.

----------

## Repository Structure

```
sentinel-alpha/
│
├── data/
│   ├── market_stream.py          # Binance market data ingestion
│   └── feature_engineering.py    # Streaming feature extraction
│
├── models/
│   ├── regime_classifier.py      # Market regime AI model
│   ├── confidence_model.py       # Signal confidence estimation
│   └── risk_filter.py            # Volatility & cooldown gating
│
├── strategy/
│   ├── signal_engine.py          # Signal generation logic
│   └── policy_rules.py           # Risk & compliance rules
│
├── evaluation/
│   ├── metrics.py                # Performance & risk metrics
│   └── visual_reports.py         # Charts & visual summaries
│
├── demo/
│   ├── historical_replay.py      # Market data replay for demo
│   └── signal_logs.csv           # Time-stamped signal outputs
│
└── README.md

```

This structure reflects **production-grade engineering discipline** and clean separation of concerns.

----------

## Demonstration & Proof

For hackathon review, Sentinel Alpha provides:

-   Time-stamped signal logs
    
-   Annotated market charts
    
-   Risk and performance summaries
    
-   Optional screen recordings or visual walkthroughs
    

All demonstrations use **public Binance market data** and do not expose sensitive credentials.

----------

## Future Extension (Post-Approval)

After WEEX allowlisting:

-   The same intelligence engine can be connected to WEEX APIs
    
-   Execution adapters can be added without altering AI logic
    
-   Multi-exchange support can be enabled
    
-   Real-time streaming architectures (e.g., Kafka/Confluent) can be integrated
    

The system is intentionally **exchange-agnostic by design**.

----------

## Disclaimer

This project is provided for **research, demonstration, and hackathon evaluation purposes only**.  
It does not constitute financial advice and does not guarantee profitability.

----------

## Author

**Gethsun Misesi**  
AI • Web3 • Trading Systems Research  
AI Wars: WEEX Alpha Awakens

----------

