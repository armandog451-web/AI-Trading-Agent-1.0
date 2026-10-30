# COMPARACIÓN CUANTITATIVA MULTI-CRITERIO — ORACLEBOT V2

**Candidatas Evaluadas:**
1. `ORB_INTRADAY_BREAKOUT_V1` (Breakout 15m/1h)
2. `ORB_SWING_PULLBACK_V1` (Pullback 4h/1D)
3. Referencia Inmóvil: `D21_RangeCompress_5d` (Range Compression 1D)

---

## 1. TABLA COMPARATIVA CONSOLIDADA

| Métrica Cuantitativa | ORB_INTRADAY_BREAKOUT_V1 | ORB_SWING_PULLBACK_V1 | D21_RangeCompress_5d (Base) |
| :--- | :--- | :--- | :--- |
| **Timeframe Señal / Contexto** | 15 minutos / 1 hora | 4 horas / Diario (1D) | Diario (1D) |
| **Operaciones Totales (5 años)** | 5 trades | 4 trades | 8 trades (Fase 10.7) |
| **Win Rate** | 20.0% | 100.0% | 87.5% |
| **Expectancy en R** | +0.06 R | +1.92 R | +1.50 R |
| **Profit Factor** | 0.65 | 99.00 | 13.09 |
| **PnL Neto Realizado** | -$718.50 USD | +$14,418.74 USD | +$1,847.10 USD |
| **Costes Totales (Fricción)** | $382.26 USD | $275.98 USD | $163.50 USD |
| **Maximum Drawdown** | $1,498.24 (0.15%) | $0.00 (0.00%) | $305.46 (0.19%) |
| **Duración Media en Mercado** | 1.0 barras (15m) | 1.0 barras (4h) | 5.0 días |
| **Sensibilidad a Gaps** | Inexistente (Cierre 15:50) | Moderada (Modelada en 4h) | Alta (Overnight diario) |
| **Robustness Score / SQS** | 16.2 / 20.0 | 48.0 / 50.0 | 71.2 / 69.17 |
| **Estado en Strategy Registry** | `INSUFFICIENT_EVIDENCE` | `INSUFFICIENT_EVIDENCE` | `PAPER` (Sandbox Aislado) |

---

## 2. ANÁLISIS DE CAUSA RAÍZ: ¿POR QUÉ LA MUESTRA ES BAJA?

Ambas estrategias sufren de **sobre-constricción de filtros (Over-filtering)**:
- **Intradía (A):** Exige que simultáneamente la 1H tenga EMA20 > EMA50 y cierre > EMA20; y en 15m se rompa el máximo de 20 barras con volumen $\ge 1.5\times$ la media y cuerpo $\ge 50\%$ cerrando en el cuartil superior, todo dentro del estrecho horario 10:00-15:00 ET. Esto ocurre menos de 1 vez por año por símbolo.
- **Swing (B):** Exige que la media de 50 esté subiendo vs 10 sesiones anteriores, y en 4h se toque EMA20 pero no se cierre bajo EMA50, cerrando luego sobre el máximo previo.

---

## 3. COMPARACIÓN CON D21

- **D21** mantiene un SQS superior ($69.17$), una mayor densidad de evidencias empíricas (Fases 10.1 a 10.8) y un comportamiento validado en paper sandbox.
- Las dos nuevas estrategias **no superan a D21 en robustez demostrada** y requieren campañas de relajación de parámetros antes de poder optar a estado `CANDIDATE`.
