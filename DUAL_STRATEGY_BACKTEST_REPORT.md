# INFORME EMPÍRICO DE BACKTESTING Y COSTES — ORACLEBOT V2

**Fecha de Ejecución:** 2026-10-29T18:56:38Z  
**Periodo Evaluado:** 2021-01-04 a 2025-10-20 ($1,200\text{ sesiones bursátiles}$)  
**Universo Evaluado:** SPY, QQQ, AAPL, MSFT, NVDA ($5\text{ activos principales}$)  
**División Temporal:** $60\%\text{ Train}$ ($720\text{ días}$) / $20\%\text{ Val}$ ($240\text{ días}$) / $20\%\text{ Test}$ ($240\text{ días}$)  
**Cuenta de Referencia:** $1,000,000 USD (Paper Profile)  
**Fuente de Resultados:** `dual_strategy_research_results.json`  

---

## 1. RESULTADOS ESTRATEGIA A: ORB_INTRADAY_BREAKOUT_V1

Fingerprint: `617a2311672c8625` | Timeframe: 15m / 1h

| Partición / Escenario | Operaciones | Win Rate | Profit Factor | Expectancy (R) | Net PnL (USD) | Max Drawdown | Sharpe |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **In-Sample (Train 60%)** | 5 | 20.0% | 0.65 | +0.06 R | -$718.50 USD | $1,498.24 (0.15%) | -6.13 |
| **Validation (20%)** | 0 | 0.0% | 0.00 | 0.00 R | $0.00 USD | $0.00 | 0.00 |
| **Final Test 1x (Base Costs)** | 0 | 0.0% | 0.00 | 0.00 R | $0.00 USD | $0.00 | 0.00 |
| **Final Test 2x (Double Costs)** | 0 | 0.0% | 0.00 | 0.00 R | $0.00 USD | $0.00 | 0.00 |
| **Final Test 3x (Triple Costs)** | 0 | 0.0% | 0.00 | 0.00 R | $0.00 USD | $0.00 | 0.00 |
| **TOTAL CONSOLIDADO** | **5** | **20.0%** | **0.65** | **+0.06 R** | **-$718.50 USD** | **$1,498.24 (0.15%)** | **-6.13** |

*Desglose de Costes Intradía:* Comisiones: $\$10.66\text{ USD}$ | Deslizamiento: $\$371.60\text{ USD}$ | Costes Totales: $\$382.26\text{ USD}$.

---

## 2. RESULTADOS ESTRATEGIA B: ORB_SWING_PULLBACK_V1

Fingerprint: `7e830e2de5df3eec` | Timeframe: 4h / 1D

| Partición / Escenario | Operaciones | Win Rate | Profit Factor | Expectancy (R) | Net PnL (USD) | Max Drawdown | Sharpe |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **In-Sample (Train 60%)** | 4 | 100.0% | 99.00 | +1.92 R | +$14,418.74 USD | $0.00 (0.00%) | 66.47 |
| **Validation (20%)** | 0 | 0.0% | 0.00 | 0.00 R | $0.00 USD | $0.00 | 0.00 |
| **Final Test 1x (Base Costs)** | 0 | 0.0% | 0.00 | 0.00 R | $0.00 USD | $0.00 | 0.00 |
| **Final Test 2x (Double Costs)** | 0 | 0.0% | 0.00 | 0.00 R | $0.00 USD | $0.00 | 0.00 |
| **Final Test 3x (Triple Costs)** | 0 | 0.0% | 0.00 | 0.00 R | $0.00 USD | $0.00 | 0.00 |
| **TOTAL CONSOLIDADO** | **4** | **100.0%** | **99.00** | **+1.92 R** | **+$14,418.74 USD** | **$0.00 (0.00%)** | **66.47** |

*Desglose de Costes Swing:* Comisiones: $\$8.00\text{ USD}$ | Deslizamiento: $\$267.98\text{ USD}$ | Costes Totales: $\$275.98\text{ USD}$.

---

## 3. AUDITORÍA CONTRA EL UMBRAL DE EVIDENCIA MÍNIMA

| Criterio Institucional | Requisito Mínimo | Resultado Estrategia A | Resultado Estrategia B | Estado de la Puerta |
| :--- | :--- | :--- | :--- | :--- |
| **Operaciones Totales** | $\ge 100\text{ trades}$ | 5 trades | 4 trades | **RECHAZADO (Muestra insuficiente)** |
| **Operaciones Fuera de Muestra (OOS)** | $\ge 30\text{ trades}$ | 0 trades | 0 trades | **RECHAZADO (Sin datos OOS)** |
| **Sesiones Forward Paper** | $\ge 60\text{ sesiones}$ | 0 sesiones | 0 sesiones | **PENDIENTE (Fase Paper)** |
| **Costes Friccionales Netos** | Obligatorio | Verificado ($5\text{ bps} + \$0.005$) | Verificado ($5\text{ bps} + \$0.005$) | **CUMPLIDO** |
| **Ausencia de Data Leakage** | Cero Look-Ahead | Verificado (Closed-Bar) | Verificado (Closed-Bar) | **CUMPLIDO** |

> [!CAUTION]
> **Dictamen Cuantitativo Riguroso:**  
> A pesar de que la Estrategia B muestra un PnL positivo en entrenamiento (+14,418 USD), **el tamaño de muestra es de solo 4 operaciones**. No se cumple el umbral mínimo de 100 operaciones ni el de 30 operaciones fuera de muestra.  
> Por tanto, de acuerdo con la Fase 5 del mandato institucional:  
> **AMBAS ESTRATEGIAS PERMANECEN EN ESTADO: `INSUFFICIENT_EVIDENCE`**.  
> Prohibido declararlas estadísticamente válidas o promoverlas a producción.
