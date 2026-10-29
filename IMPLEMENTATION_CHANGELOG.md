# REGISTRO DE CAMBIOS Y TRAZABILIDAD — ORACLEBOT V2

**Versión:** `ai_trading_agent v2.3.0-oraclebot-dual`  
**Fecha:** 2026-10-29T19:00:00Z  
**Autoridad:** OracleBot Quantitative Governance  

---

## 1. COMPONENTES NUEVOS CREADOS

| Archivo / Módulo | Propósito y Responsabilidad |
| :--- | :--- |
| `ai_trading_agent/dual_strategy/__init__.py` | Inicializador de paquete del framework dual. |
| `ai_trading_agent/dual_strategy/models.py` | Modelos inmutables Pydantic (`ReproducibleSignal`, `RiskReservation`, `TradeFillRecord`). |
| `ai_trading_agent/dual_strategy/data_provider.py` | `MarketDataProvider`: Validación de filtros de universo, normalización horaria, agregación 4h y hash de datos. |
| `ai_trading_agent/dual_strategy/features.py` | `FeatureEngine`: Cálculo de EMA, ATR, Donchian High anterior y proporciones de vela en barras cerradas. |
| `ai_trading_agent/dual_strategy/strategies/intraday_breakout.py` | `OrbIntradayBreakoutV1`: Lógica 15m/1h, filtros RVOL $\ge 1.5$, Donchian 20 y salida a las 15:50 ET. |
| `ai_trading_agent/dual_strategy/strategies/swing_pullback.py` | `OrbSwingPullbackV1`: Lógica 4h/1D, rebote en EMA20, confirmación macro y salida a 10 sesiones. |
| `ai_trading_agent/dual_strategy/risk.py` | `PortfolioRiskEngine`: Gobernanza consolidada, dimensionamiento determinista, límites nocionales y circuit breakers. |
| `ai_trading_agent/dual_strategy/simulation.py` | `SimulationExecutionEngine` & `PaperBrokerSecurityGuard`: Fricciones realistas y bloqueo de endpoints LIVE. |
| `ai_trading_agent/dual_strategy/fidelity.py` | `FidelityEngine`: Medición de discrepancias y latencia de ejecución frente al paper broker. |
| `ai_trading_agent/dual_strategy/tracker.py` | `EvidenceJournal` & `ExperimentTracker`: Diario criptográfico inmutable con encadenamiento SHA-256. |
| `ai_trading_agent/dual_strategy/metrics.py` | `MetricsEngine`: Cálculo de Sharpe, Sortino, Expectancy en R, Profit Factor y Drawdown. |
| `ai_trading_agent/dual_strategy/notifier.py` | `DualStrategyTelegramNotifier`: Mensajería Outbound-Only con tags `[BACKTEST]`, `[SHADOW]`, `[PAPER]`. |
| `ai_trading_agent/dual_strategy/orchestrator.py` | `DualStrategyOrchestrator`: Coordinador de backtesting, walk-forward, splits 60/20/20 y registro en SQLite. |
| `ai_trading_agent/tests/test_oraclebot_v2_dual_strategy.py` | Batería de 25 pruebas unitarias e integradas para validación de gobernanza y simulación. |
| `ai_trading_agent/scratch/run_dual_research_campaign.py` | Script reproducible de ejecución empírica multi-activo a 5 años. |

---

## 2. COMPONENTES AUDITADOS Y PRESERVADOS (CERO ALTERACIONES)

- **D21 Strategy Definition:** Intacta (`f885ec2db2422308`, `PAPER`).
- **Core Settings:** `TRADING_MODE = ANALYSIS_ONLY` conservado.
- **Suite de Tests Existente:** Los 230 tests originales se mantienen al 100% de éxito.

---

## 3. DOCUMENTOS ENTREGABLES GENERADOS

1. `ORACLEBOT_DUAL_STRATEGY_AUDIT.md`
2. `INTRADAY_BREAKOUT_V1_SPEC.md`
3. `SWING_PULLBACK_V1_SPEC.md`
4. `DUAL_STRATEGY_RISK_POLICY.md`
5. `DUAL_STRATEGY_BACKTEST_REPORT.md`
6. `DUAL_STRATEGY_COMPARISON.md`
7. `DUAL_STRATEGY_TEST_RESULTS.md`
8. `PAPER_VALIDATION_PLAN.md`
9. `D21_NON_REGRESSION_REPORT.md`
10. `IMPLEMENTATION_CHANGELOG.md`
