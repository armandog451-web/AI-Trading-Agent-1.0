# D21 CONTROLLED PAPER RUNTIME ACTIVATION REPORT

**Execution Timestamp:** 2026-10-05 23:45:00 EST  
**System Core:** `ai_trading_agent v1.2.0 / Pro Engine`  
**Strategy ID:** `D21_RangeCompress_5d` (Family: `daily_range_compression_breakout`)  
**Fingerprint Lock:** `f885ec2db2422308` (Exact Match)  
**Lifecycle Status:** `StrategyStatus.PAPER`  
**Authorization Reference:** Human Explicit Authorization (`AUTHORIZE D21 CONTROLLED PAPER EXECUTION`)  

---

## 1. GLOBAL TRADING MODE STATE TRANSITION

Under explicit human authorization, the global operational trading mode has been formally transitioned:

- **Mode Before Transition:** `TradingMode.ANALYSIS_ONLY`
- **Mode After Transition:** `TradingMode.PAPER_TRADING`
- **Confirmation:** Confirmed in `.env`, `AgentSettings`, and active runtime endpoint (`http://127.0.0.1:8090/health` reports `"trading_mode": "PAPER_TRADING"`).
- **Physical Safety Guarantee:** Live trading capabilities remain **HARD-DISABLED**. Zero live exchange endpoints are configured, imported, or accessible.

---

## 2. STRATEGY SPECIFICATION & CRYPTOGRAPHIC ANCHOR

The strategy parameters remain 100% sealed without mutation:
- **Strategy ID:** `D21_RangeCompress_5d`
- **Frozen Fingerprint:** `f885ec2db2422308`
- **Current Fingerprint:** `f885ec2db2422308` (Match: EXACT)
- **Timeframe:** `1D` (Closed daily bars only)
- **Universe:** `['SPY', 'QQQ', 'IWM', 'DIA']` (Strict whitelist)
- **Entry Rules:**
  - Range Compression: $\text{High}_{t-1} - \text{Low}_{t-1} < 0.60 \times \text{ATR14}_{t-1}$
  - Trend Filter: $\text{Close}_{t-1} > \text{SMA20}_{t-1}$
  - Execution Timing: Next valid market session open ($t$)
- **Exit Rules:**
  - Holding Horizon: Maximum 5 daily bars (Time Exit)
  - Stop Loss: $2.0 \times \text{ATR14}$ from entry price
  - Profit Target: None

---

## 3. BROKER DESTINATION & ISOLATION BOUNDARIES

Every execution path in `PAPER_TRADING` terminates exclusively in sandbox environments:
- **Moomoo Adapter:** Target environment is strictly `trd_env = ft.TrdEnv.SIMULATE` (OpenD local port 11111).
- **Alpaca Adapter:** Target endpoint is strictly `https://paper-api.alpaca.markets`.
- **Internal Paper Broker:** Deterministic simulation account funded with \$1,000,000 USD.
- **Live Endpoints:** **COMPLETELY ABSENT**. No path to live exchanges exists.

---

## 4. INSTITUTIONAL RISK PROFILE ($1,000,000 ACCOUNT)

All order proposals must clear all deterministic risk limits:

| Risk Parameter | Setting | Dollar Cap ($1M Portfolio) |
| :--- | :---: | :---: |
| **Reference Capital** | $1,000,000.00 USD | $1,000,000.00 |
| **Planned Risk per Trade** | 0.25% equity | **$2,500.00 max risk** |
| **Maximum Allocation per Symbol** | 10.0% equity | **$100,000.00 max notional** |
| **Maximum Concurrent Positions** | 2 positions | **$200,000.00 gross exposure cap** |
| **Daily Loss Circuit Breaker** | 1.00% equity | **-$10,000.00 daily loss halt** |
| **Portfolio Drawdown Breaker** | 10.00% from HWM | **-$100,000.00 pause** |
| **Consecutive Loss Brake** | 3 consecutive losses | **Auto-halt new entries** |
| **Allowed Universe** | `SPY`, `QQQ`, `IWM`, `DIA` | Strictly enforced |

---

## 5. PRE-REGISTERED PAPER VALIDATION RULES & PASS CRITERIA

The campaign protocol remains immutable:
- **Minimum Observation Horizon:** 90 calendar days
- **Maximum Observation Window:** 180 calendar days
- **Minimum Closed Trades:** $\ge 12$
- **Net Realized PnL:** $> \$0.00$
- **Realized Profit Factor:** $PF \ge 1.05$
- **Trade Expectancy:** $> \$0.00$ / trade
- **Maximum Drawdown:** $\le 10.0\%$
- **Mean Realized Slippage:** $\le 7.5\text{ bps}$
- **Execution Defects:** Zero critical unhandled execution errors
- **Risk Compliance:** Zero risk-control violations
- **Strategy Invariance:** Fingerprint $= \text{f885ec2db2422308}$
- **No Live Exposure:** Zero interaction with live exchange endpoints

---

## 6. LIFECYCLE & LIVE SAFETY GATING

- **Current Status in SQLite:** `StrategyStatus.PAPER`
- **Robustness Score (PRS):** `71.2` (Meets threshold $\ge 60.0$)
- **Strategy Quality Score (SQS):** `69.17`
- **Approval Gate Status:** **`APPROVED = FALSE`**
- **Governance Gate:** Transition `PAPER -> APPROVED` requires $SQS \ge 70.0$. Because $69.17 < 70.0$, the strategy is physically barred from automated promotion to live trading.

---

## 7. RUNTIME, HEARTBEAT & SCHEDULER HEALTH

- **Runtime Process:** `RUNNING` (PID: `28908`, Uvicorn daemon)
- **Active Heartbeat:** `HEALTHY` (Monotonically advancing timestamps verified over HTTP)
- **Market State:** `CLOSED` (Night session)
- **Current Time ET:** `2026-10-05 23:45:00 ET`
- **First Eligible Execution Window:** `2026-10-06 09:30:00 ET` (Market Open following next daily bar evaluation)
- **Artificial Test Orders:** **ZERO (0)** submitted. The agent is waiting for natural closed bar triggers.

---

## 8. FINAL SYSTEM STATE

$$\mathbf{PAPER\_VALIDATION\_ACTIVE} = \mathbf{TRUE}$$
$$\mathbf{TRADING\_MODE} = \mathbf{PAPER\_TRADING}$$
$$\mathbf{STRATEGY\_STATUS} = \mathbf{PAPER}$$
$$\mathbf{LIVE\_CAPABILITY} = \mathbf{DISABLED}$$

---

## 9. FINAL VERDICT

$$\mathbf{FINAL\ VERDICT:}\quad \mathbf{PAPER\_RUNTIME\_ACTIVE}$$

The AI Trading Agent workstation is armed, verified, and running in controlled Paper Trading mode.
